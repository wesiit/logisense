import { uoihApi } from "./client";
import type {
  ActiveAlertsResponse,
  Alert,
  DailyKPIResponse,
  InventoryAccuracyResponse,
} from "../types";

/**
 * Fetch daily KPIs for a facility
 */
export const getDailyKPIs = async (
  facilityId: string,
  dateFrom: string,
  dateTo: string
): Promise<DailyKPIResponse> => {
  const response = await uoihApi.get<DailyKPIResponse>("/v1/uoih/kpis/daily", {
    params: {
      facility_id: facilityId,
      date_from: dateFrom,
      date_to: dateTo,
    },
  });
  return response.data;
};

/**
 * Fetch 30-day inventory accuracy trend
 */
export const getInventoryAccuracy = async (
  facilityId: string
): Promise<InventoryAccuracyResponse> => {
  const response = await uoihApi.get<InventoryAccuracyResponse>(
    "/v1/uoih/kpis/inventory-accuracy",
    {
      params: { facility_id: facilityId },
    }
  );
  return response.data;
};

/**
 * Fetch active alerts for a facility
 */
export const getActiveAlerts = async (
  facilityId: string
): Promise<ActiveAlertsResponse> => {
  const response = await uoihApi.get<ActiveAlertsResponse>(
    "/v1/uoih/alerts/active",
    {
      params: { facility_id: facilityId },
    }
  );
  return response.data;
};

/**
 * Fetch all active alerts across all facilities
 */
export const getAllActiveAlerts = async (): Promise<ActiveAlertsResponse> => {
  const response = await uoihApi.get<ActiveAlertsResponse>(
    "/v1/uoih/alerts/active",
    {
      params: { facility_id: "ALL" },
    }
  );
  return response.data;
};

/**
 * Acknowledge an alert
 */
export const acknowledgeAlert = async (
  alertId: string,
  actor: string
): Promise<Alert> => {
  const response = await uoihApi.post<Alert>(
    `/v1/uoih/alerts/${alertId}/acknowledge`,
    { actor }
  );
  return response.data;
};

/**
 * Get aggregated dashboard stats
 */
export interface DashboardStats {
  totalOrdersToday: number;
  inventoryAccuracyPct: number;
  activeAlerts: number;
  criticalAlerts: number;
  highAlerts: number;
  facilitiesOnline: number;
  totalFacilities: number;
}

export const getDashboardStats = async (
  facilityIds: string[]
): Promise<DashboardStats> => {
  // For now, aggregate from multiple calls
  // In production, this would be a dedicated endpoint
  const today = new Date().toISOString().split("T")[0];

  let totalOrders = 0;
  let totalAccuracy = 0;
  let accuracyCount = 0;
  let activeAlerts = 0;
  let criticalAlerts = 0;
  let highAlerts = 0;
  let facilitiesOnline = 0;

  for (const facilityId of facilityIds) {
    try {
      // Get KPIs
      const kpis = await getDailyKPIs(facilityId, today, today);
      if (kpis.kpis.length > 0) {
        totalOrders += kpis.kpis[0].orders_fulfilled;
        totalAccuracy += kpis.kpis[0].inventory_accuracy_pct;
        accuracyCount++;
        facilitiesOnline++;
      }

      // Get alerts
      const alerts = await getActiveAlerts(facilityId);
      activeAlerts += alerts.total;
      criticalAlerts += alerts.alerts.filter(
        (a) => a.severity === "CRITICAL"
      ).length;
      highAlerts += alerts.alerts.filter((a) => a.severity === "HIGH").length;
    } catch (error) {
      console.error(`Failed to fetch data for facility ${facilityId}:`, error);
    }
  }

  return {
    totalOrdersToday: totalOrders,
    inventoryAccuracyPct:
      accuracyCount > 0 ? totalAccuracy / accuracyCount : 0,
    activeAlerts,
    criticalAlerts,
    highAlerts,
    facilitiesOnline,
    totalFacilities: facilityIds.length,
  };
};
