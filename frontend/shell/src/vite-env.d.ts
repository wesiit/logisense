/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_KEYCLOAK_URL: string;
  readonly VITE_KEYCLOAK_REALM: string;
  readonly VITE_KEYCLOAK_CLIENT_ID: string;
  readonly VITE_API_BASE_URL: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Module Federation remote modules
declare module "iwms/App" {
  const Component: React.ComponentType;
  export default Component;
}

declare module "uoih/App" {
  const Component: React.ComponentType;
  export default Component;
}

declare module "ccvp/App" {
  const Component: React.ComponentType;
  export default Component;
}

declare module "lip/App" {
  const Component: React.ComponentType;
  export default Component;
}

declare module "pise/App" {
  const Component: React.ComponentType;
  export default Component;
}

declare module "wcvp/App" {
  const Component: React.ComponentType;
  export default Component;
}
