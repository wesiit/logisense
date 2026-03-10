// License types
export interface LicenseInfo {
  valid: boolean;
  tenant_id: string;
  tenant_name: string;
  licensed_modules: LicensedModule[];
  expires_at: string;
  max_facilities: number;
  max_users: number;
}

export interface LicensedModule {
  module_id: string;
  module_name: string;
  enabled: boolean;
  features: string[];
}

// Alert types
export type AlertSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

export interface Alert {
  id: string;
  facility_id: string;
  module_id: string;
  alert_type: string;
  severity: AlertSeverity;
  title: string;
  body: string | null;
  alert_metadata: Record<string, unknown> | null;
  status: AlertStatus;
  created_at: string;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
}

export interface ActiveAlertsResponse {
  facility_id: string;
  total: number;
  alerts: Alert[];
}

// KPI types
export interface DailyKPI {
  facility_id: string;
  date: string;
  total_movements: number;
  picks_completed: number;
  inventory_accuracy_pct: number;
  orders_fulfilled: number;
}

export interface DailyKPIResponse {
  facility_id: string;
  date_from: string;
  date_to: string;
  kpis: DailyKPI[];
}

export interface InventoryAccuracyPoint {
  date: string;
  accuracy_pct: number;
  cycle_counts: number;
}

export interface InventoryAccuracyResponse {
  facility_id: string;
  period_days: number;
  trend: InventoryAccuracyPoint[];
  average_accuracy_pct: number;
}

// User types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  roles: string[];
}

// Navigation types
export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: string;
  module_id?: string;
}

// Module remote types
export interface ModuleRemote {
  name: string;
  entry: string;
  routes: ModuleRoute[];
}

export interface ModuleRoute {
  path: string;
  component: string;
}
