import React, { useEffect, useState } from "react";
import { useLicense } from "../hooks/useLicense";
import { useAlerts } from "../hooks/useAlerts";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { AlertBadge } from "../components/AlertBadge";
import type { Alert, LicensedModule } from "../types";

// KPI Card component
interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    positive: boolean;
  };
  loading?: boolean;
}

const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  loading,
}) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {loading ? (
          <LoadingSpinner size="sm" className="mt-2" />
        ) : (
          <>
            <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
            {subtitle && (
              <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
            )}
            {trend && (
              <p
                className={`mt-2 text-sm font-medium ${
                  trend.positive ? "text-green-600" : "text-red-600"
                }`}
              >
                {trend.positive ? "↑" : "↓"} {Math.abs(trend.value)}% from yesterday
              </p>
            )}
          </>
        )}
      </div>
      <div className="p-3 bg-navy-50 rounded-lg text-navy-600">{icon}</div>
    </div>
  </div>
);

// Module Card component
interface ModuleCardProps {
  module: LicensedModule;
}

const ModuleCard: React.FC<ModuleCardProps> = ({ module }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
    <div className="flex items-center justify-between">
      <div>
        <h3 className="font-semibold text-gray-900">{module.module_name}</h3>
        <p className="text-sm text-gray-500 mt-1">
          {module.features.length} features enabled
        </p>
      </div>
      <span
        className={`px-3 py-1 rounded-full text-xs font-medium ${
          module.enabled
            ? "bg-green-100 text-green-800"
            : "bg-gray-100 text-gray-600"
        }`}
      >
        {module.enabled ? "Active" : "Inactive"}
      </span>
    </div>
    <div className="mt-4 flex flex-wrap gap-2">
      {module.features.slice(0, 4).map((feature) => (
        <span
          key={feature}
          className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600"
        >
          {feature}
        </span>
      ))}
      {module.features.length > 4 && (
        <span className="px-2 py-1 text-xs text-gray-400">
          +{module.features.length - 4} more
        </span>
      )}
    </div>
  </div>
);

// Alert Item component
interface AlertItemProps {
  alert: Alert;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert }) => {
  const severityColors = {
    CRITICAL: "border-l-red-500 bg-red-50",
    HIGH: "border-l-orange-500 bg-orange-50",
    MEDIUM: "border-l-yellow-500 bg-yellow-50",
    LOW: "border-l-blue-500 bg-blue-50",
  };

  const timeAgo = (date: string) => {
    const seconds = Math.floor(
      (new Date().getTime() - new Date(date).getTime()) / 1000
    );
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div
      className={`border-l-4 ${severityColors[alert.severity]} p-4 rounded-r-lg`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <AlertBadge
              count={1}
              severity={alert.severity.toLowerCase() as "critical" | "high" | "medium" | "low"}
            />
            <span className="text-xs text-gray-500">{alert.facility_id}</span>
          </div>
          <p className="mt-1 text-sm font-medium text-gray-900">{alert.title}</p>
          {alert.body && (
            <p className="mt-1 text-sm text-gray-600 line-clamp-2">{alert.body}</p>
          )}
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap ml-4">
          {timeAgo(alert.created_at)}
        </span>
      </div>
    </div>
  );
};

// Icons
const OrdersIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
  </svg>
);

const AccuracyIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const FacilityIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

export const Dashboard: React.FC = () => {
  const { getLicensedModules, loading: licenseLoading } = useLicense();
  const { alerts, criticalCount, highCount, loading: alertsLoading } = useAlerts();
  const licensedModules = getLicensedModules();

  // Mock KPI data - in production, fetch from UOIH API
  const [kpiLoading, setKpiLoading] = useState(true);
  const [kpis, setKpis] = useState({
    totalOrdersToday: 0,
    inventoryAccuracyPct: 0,
    facilitiesOnline: 0,
    totalFacilities: 0,
  });

  useEffect(() => {
    // Simulate API call
    const fetchKPIs = async () => {
      setKpiLoading(true);
      // In production: const data = await getDashboardStats(facilityIds);
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setKpis({
        totalOrdersToday: 1247,
        inventoryAccuracyPct: 98.5,
        facilitiesOnline: 3,
        totalFacilities: 4,
      });
      setKpiLoading(false);
    };

    fetchKPIs();
  }, []);

  const totalAlerts = criticalCount + highCount;

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Overview of your warehouse operations
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Orders Today"
          value={kpis.totalOrdersToday.toLocaleString()}
          subtitle="Orders fulfilled"
          icon={<OrdersIcon />}
          trend={{ value: 12, positive: true }}
          loading={kpiLoading}
        />
        <KPICard
          title="Inventory Accuracy"
          value={`${kpis.inventoryAccuracyPct}%`}
          subtitle="Based on cycle counts"
          icon={<AccuracyIcon />}
          trend={{ value: 0.5, positive: true }}
          loading={kpiLoading}
        />
        <KPICard
          title="Active Alerts"
          value={totalAlerts}
          subtitle={`${criticalCount} critical, ${highCount} high`}
          icon={<AlertIcon />}
          loading={alertsLoading}
        />
        <KPICard
          title="Facilities Online"
          value={`${kpis.facilitiesOnline}/${kpis.totalFacilities}`}
          subtitle="Connected facilities"
          icon={<FacilityIcon />}
          loading={kpiLoading}
        />
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Licensed Modules */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Licensed Modules
            </h2>
            {licenseLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {licensedModules.map((module) => (
                  <ModuleCard key={module.module_id} module={module} />
                ))}
                {licensedModules.length === 0 && (
                  <p className="text-gray-500 col-span-2 text-center py-8">
                    No modules licensed
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Recent Alerts
              </h2>
              {totalAlerts > 0 && (
                <AlertBadge
                  count={totalAlerts}
                  severity={criticalCount > 0 ? "critical" : "high"}
                />
              )}
            </div>
            {alertsLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.slice(0, 5).map((alert) => (
                  <AlertItem key={alert.id} alert={alert} />
                ))}
                {alerts.length > 5 && (
                  <a
                    href="/uoih/alerts"
                    className="block text-center text-sm text-accent-blue hover:underline py-2"
                  >
                    View all {alerts.length} alerts
                  </a>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <p className="text-gray-500">All systems operational</p>
                <p className="text-sm text-gray-400 mt-1">No active alerts</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
