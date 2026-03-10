import { useState, useEffect, useCallback } from "react";
import { licenseApi } from "../api/client";
import type { LicenseInfo, LicensedModule } from "../types";

interface UseLicenseReturn {
  license: LicenseInfo | null;
  loading: boolean;
  error: string | null;
  isModuleLicensed: (moduleId: string) => boolean;
  getLicensedModules: () => LicensedModule[];
  refetch: () => Promise<void>;
}

// Cache license info
let cachedLicense: LicenseInfo | null = null;
let cacheTimestamp = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export const useLicense = (): UseLicenseReturn => {
  const [license, setLicense] = useState<LicenseInfo | null>(cachedLicense);
  const [loading, setLoading] = useState(!cachedLicense);
  const [error, setError] = useState<string | null>(null);

  const fetchLicense = useCallback(async () => {
    // Check cache
    if (cachedLicense && Date.now() - cacheTimestamp < CACHE_TTL) {
      setLicense(cachedLicense);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await licenseApi.get<LicenseInfo>("/v1/license/validate");
      cachedLicense = response.data;
      cacheTimestamp = Date.now();
      setLicense(response.data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to validate license";
      setError(message);
      console.error("License validation failed:", err);

      // Use mock data in development
      if (import.meta.env.DEV) {
        const mockLicense: LicenseInfo = {
          valid: true,
          tenant_id: "dev-tenant",
          tenant_name: "Development Tenant",
          licensed_modules: [
            {
              module_id: "iwms",
              module_name: "Intelligent WMS",
              enabled: true,
              features: ["inventory", "orders", "waves", "tasks"],
            },
            {
              module_id: "uoih",
              module_name: "Operations Intelligence Hub",
              enabled: true,
              features: ["kpis", "alerts", "dashboards"],
            },
            {
              module_id: "ccvp",
              module_name: "Cold Chain Visibility",
              enabled: false,
              features: [],
            },
          ],
          expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
          max_facilities: 10,
          max_users: 100,
        };
        cachedLicense = mockLicense;
        cacheTimestamp = Date.now();
        setLicense(mockLicense);
        setError(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLicense();
  }, [fetchLicense]);

  const isModuleLicensed = useCallback(
    (moduleId: string): boolean => {
      if (!license) return false;
      const module = license.licensed_modules.find(
        (m) => m.module_id === moduleId
      );
      return module?.enabled ?? false;
    },
    [license]
  );

  const getLicensedModules = useCallback((): LicensedModule[] => {
    if (!license) return [];
    return license.licensed_modules.filter((m) => m.enabled);
  }, [license]);

  return {
    license,
    loading,
    error,
    isModuleLicensed,
    getLicensedModules,
    refetch: fetchLicense,
  };
};

// Helper to dynamically import module remotes
export const loadModuleRemote = async (
  moduleId: string
): Promise<React.ComponentType | null> => {
  const remotes: Record<string, () => Promise<{ default: React.ComponentType }>> = {
    iwms: () => import("iwms/App"),
    uoih: () => import("uoih/App"),
  };

  const loader = remotes[moduleId];
  if (!loader) {
    console.warn(`No remote configured for module: ${moduleId}`);
    return null;
  }

  try {
    const module = await loader();
    return module.default;
  } catch (error) {
    console.error(`Failed to load remote module ${moduleId}:`, error);
    return null;
  }
};
