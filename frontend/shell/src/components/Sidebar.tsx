import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useLicense } from "../hooks/useLicense";
import { LoadingSpinner } from "./LoadingSpinner";

// Icons as simple SVG components
const DashboardIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
  </svg>
);

const WarehouseIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

const ChartIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const ThermometerIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const moduleIcons: Record<string, React.FC> = {
  iwms: WarehouseIcon,
  uoih: ChartIcon,
  ccvp: ThermometerIcon,
};

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: React.FC;
  moduleId?: string;
}

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { getLicensedModules, loading } = useLicense();
  const licensedModules = getLicensedModules();

  // Base navigation items
  const baseNavItems: NavItem[] = [
    {
      id: "dashboard",
      label: "Dashboard",
      path: "/",
      icon: DashboardIcon,
    },
  ];

  // Module navigation items based on license
  const moduleNavItems: NavItem[] = licensedModules.map((module) => ({
    id: module.module_id,
    label: module.module_name,
    path: `/${module.module_id}`,
    icon: moduleIcons[module.module_id] || DashboardIcon,
    moduleId: module.module_id,
  }));

  const navItems = [...baseNavItems, ...moduleNavItems];

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-navy-900 text-white">
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-navy-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-accent-blue rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">L</span>
          </div>
          <span className="text-xl font-semibold tracking-tight">LogiSense</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : (
          navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);

            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-colors duration-150
                  ${
                    isActive
                      ? "bg-accent-blue text-white"
                      : "text-gray-300 hover:bg-navy-800 hover:text-white"
                  }
                `}
              >
                <Icon />
                <span className="font-medium">{item.label}</span>
              </NavLink>
            );
          })
        )}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-navy-700">
        <div className="text-xs text-gray-400">
          <p>LogiSense v0.1.0</p>
          <p className="mt-1">{licensedModules.length} modules licensed</p>
        </div>
      </div>
    </aside>
  );
};
