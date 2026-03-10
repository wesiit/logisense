import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import Keycloak from "keycloak-js";

// Keycloak instance
let keycloak: Keycloak | null = null;

// Initialize Keycloak
export const initKeycloak = async (): Promise<Keycloak> => {
  if (keycloak) {
    return keycloak;
  }

  keycloak = new Keycloak({
    url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080",
    realm: import.meta.env.VITE_KEYCLOAK_REALM || "logisense",
    clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "logisense-web",
  });

  try {
    const authenticated = await keycloak.init({
      onLoad: "login-required",
      checkLoginIframe: false,
      pkceMethod: "S256",
    });

    if (!authenticated) {
      keycloak.login();
    }

    // Setup token refresh
    setInterval(async () => {
      try {
        await keycloak?.updateToken(60);
      } catch {
        console.error("Failed to refresh token");
        keycloak?.login();
      }
    }, 30000);

    return keycloak;
  } catch (error) {
    console.error("Keycloak initialization failed:", error);
    throw error;
  }
};

export const getKeycloak = (): Keycloak | null => keycloak;

export const logout = (): void => {
  keycloak?.logout({ redirectUri: window.location.origin });
};

// Create axios instance with JWT interceptor
const createApiClient = (baseURL: string): AxiosInstance => {
  const client = axios.create({
    baseURL,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Request interceptor - add JWT token
  client.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      if (keycloak?.token) {
        // Refresh token if needed
        try {
          await keycloak.updateToken(30);
        } catch {
          console.error("Token refresh failed");
        }

        config.headers.Authorization = `Bearer ${keycloak.token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor - handle auth errors
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        keycloak?.login();
      }
      return Promise.reject(error);
    }
  );

  return client;
};

// API clients for different services
export const licenseApi = createApiClient(
  import.meta.env.VITE_LICENSE_API_URL || "http://localhost:8007"
);

export const uoihApi = createApiClient(
  import.meta.env.VITE_UOIH_API_URL || "http://localhost:8006"
);

export const iwmsApi = createApiClient(
  import.meta.env.VITE_IWMS_API_URL || "http://localhost:8011"
);

// Kong gateway client (for production routing)
export const gatewayApi = createApiClient(
  import.meta.env.VITE_GATEWAY_URL || "http://localhost:8000"
);
