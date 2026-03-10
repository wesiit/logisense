import React, { Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { Dashboard } from "./pages/Dashboard";
import { NotFound } from "./pages/NotFound";
import { FullPageLoader, LoadingSpinner } from "./components/LoadingSpinner";
import { useLicense, loadModuleRemote } from "./hooks/useLicense";
import { initKeycloak } from "./api/client";

// Lazy load module components
const LazyModuleLoader: React.FC<{ moduleId: string }> = ({ moduleId }) => {
  const [Component, setComponent] = useState<React.ComponentType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const ModuleComponent = await loadModuleRemote(moduleId);
        if (ModuleComponent) {
          setComponent(() => ModuleComponent);
        } else {
          setError(`Module ${moduleId} could not be loaded`);
        }
      } catch (err) {
        console.error(`Failed to load module ${moduleId}:`, err);
        setError(`Failed to load module: ${err instanceof Error ? err.message : "Unknown error"}`);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [moduleId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Module Unavailable</h3>
        <p className="text-gray-500 mt-2 max-w-md">{error}</p>
        <p className="text-sm text-gray-400 mt-4">
          The module micro-frontend may not be running.
        </p>
      </div>
    );
  }

  if (!Component) {
    return null;
  }

  return <Component />;
};

// Module route guard
const ModuleRoute: React.FC<{ moduleId: string }> = ({ moduleId }) => {
  const { isModuleLicensed, loading } = useLicense();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isModuleLicensed(moduleId)) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-yellow-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Module Not Licensed</h3>
        <p className="text-gray-500 mt-2">
          This module is not included in your license.
        </p>
        <a
          href="mailto:sales@logisense.io"
          className="mt-4 text-accent-blue hover:underline"
        >
          Contact sales to upgrade
        </a>
      </div>
    );
  }

  return <LazyModuleLoader moduleId={moduleId} />;
};

// Main layout with sidebar and header
const MainLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
};

// App component
const App: React.FC = () => {
  const [initialized, setInitialized] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        // Skip Keycloak in development if not configured
        if (import.meta.env.DEV && !import.meta.env.VITE_KEYCLOAK_URL) {
          console.log("Development mode: Skipping Keycloak authentication");
          setInitialized(true);
          return;
        }

        await initKeycloak();
        setInitialized(true);
      } catch (error) {
        console.error("Initialization failed:", error);
        setAuthError("Authentication initialization failed");
        // In development, continue anyway
        if (import.meta.env.DEV) {
          setInitialized(true);
        }
      }
    };

    init();
  }, []);

  if (!initialized) {
    return <FullPageLoader message="Initializing application..." />;
  }

  if (authError && !import.meta.env.DEV) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Authentication Error</h1>
          <p className="mt-2 text-gray-500">{authError}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-6 py-2 bg-navy-900 text-white rounded-lg hover:bg-navy-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/*"
          element={
            <MainLayout>
              <Suspense fallback={<FullPageLoader />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/iwms/*" element={<ModuleRoute moduleId="iwms" />} />
                  <Route path="/uoih/*" element={<ModuleRoute moduleId="uoih" />} />
                  <Route path="/ccvp/*" element={<ModuleRoute moduleId="ccvp" />} />
                  <Route path="/lip/*" element={<ModuleRoute moduleId="lip" />} />
                  <Route path="/pise/*" element={<ModuleRoute moduleId="pise" />} />
                  <Route path="/wcvp/*" element={<ModuleRoute moduleId="wcvp" />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </MainLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
