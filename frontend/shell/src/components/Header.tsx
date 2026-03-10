import React, { useState } from "react";
import { useAlerts } from "../hooks/useAlerts";
import { AlertBadge } from "./AlertBadge";
import { logout, getKeycloak } from "../api/client";

// Bell icon
const BellIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    />
  </svg>
);

// User icon
const UserIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
    />
  </svg>
);

// Logout icon
const LogoutIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
    />
  </svg>
);

export const Header: React.FC = () => {
  const { alerts, criticalCount, highCount } = useAlerts();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const keycloak = getKeycloak();
  const userName = keycloak?.tokenParsed?.preferred_username || "User";
  const userEmail = keycloak?.tokenParsed?.email || "";

  const totalUrgentAlerts = criticalCount + highCount;

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200">
      {/* Left side - Page title / Breadcrumb */}
      <div>
        <h1 className="text-lg font-semibold text-gray-900">
          Warehouse Intelligence Platform
        </h1>
      </div>

      {/* Right side - Notifications and User */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
          >
            <BellIcon />
            {totalUrgentAlerts > 0 && (
              <span className="absolute -top-1 -right-1">
                <AlertBadge
                  count={totalUrgentAlerts}
                  severity={criticalCount > 0 ? "critical" : "high"}
                />
              </span>
            )}
          </button>

          {/* Notifications dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              <div className="p-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900">Notifications</h3>
                <p className="text-sm text-gray-500">
                  {totalUrgentAlerts} urgent alert{totalUrgentAlerts !== 1 ? "s" : ""}
                </p>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {alerts.slice(0, 5).map((alert) => (
                  <div
                    key={alert.id}
                    className="p-4 border-b border-gray-50 hover:bg-gray-50"
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={`
                          w-2 h-2 mt-2 rounded-full flex-shrink-0
                          ${alert.severity === "CRITICAL" ? "bg-red-500" : ""}
                          ${alert.severity === "HIGH" ? "bg-orange-500" : ""}
                          ${alert.severity === "MEDIUM" ? "bg-yellow-500" : ""}
                          ${alert.severity === "LOW" ? "bg-blue-500" : ""}
                        `}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {alert.title}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {alert.facility_id} •{" "}
                          {new Date(alert.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                {alerts.length === 0 && (
                  <div className="p-8 text-center text-gray-500">
                    <p>No active alerts</p>
                  </div>
                )}
              </div>
              {alerts.length > 5 && (
                <div className="p-3 border-t border-gray-100">
                  <a
                    href="/uoih/alerts"
                    className="text-sm text-accent-blue hover:underline"
                  >
                    View all {alerts.length} alerts
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-3 p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <div className="w-8 h-8 bg-navy-900 rounded-full flex items-center justify-center text-white">
              <UserIcon />
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-gray-900">{userName}</p>
              <p className="text-xs text-gray-500">{userEmail}</p>
            </div>
          </button>

          {/* User dropdown */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              <div className="py-1">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <LogoutIcon />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Click outside to close dropdowns */}
      {(showNotifications || showUserMenu) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setShowNotifications(false);
            setShowUserMenu(false);
          }}
        />
      )}
    </header>
  );
};
