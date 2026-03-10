import { useState, useEffect, useCallback, useRef } from "react";
import { getAllActiveAlerts } from "../api/uoih";
import type { Alert, ActiveAlertsResponse } from "../types";

interface UseAlertsReturn {
  alerts: Alert[];
  total: number;
  criticalCount: number;
  highCount: number;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const POLL_INTERVAL = 30000; // 30 seconds

export const useAlerts = (facilityId?: string): UseAlertsReturn => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      const response: ActiveAlertsResponse = await getAllActiveAlerts();

      // Filter by facility if specified
      let filteredAlerts = response.alerts;
      if (facilityId && facilityId !== "ALL") {
        filteredAlerts = response.alerts.filter(
          (a) => a.facility_id === facilityId
        );
      }

      // Sort by severity then by created_at
      const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      filteredAlerts.sort((a, b) => {
        const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
        if (severityDiff !== 0) return severityDiff;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });

      setAlerts(filteredAlerts);
      setTotal(filteredAlerts.length);
      setError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch alerts";
      setError(message);
      console.error("Alert fetch failed:", err);

      // Use mock data in development
      if (import.meta.env.DEV) {
        const mockAlerts: Alert[] = [
          {
            id: "1",
            facility_id: "FAC001",
            module_id: "iwms",
            alert_type: "LOW_INVENTORY",
            severity: "CRITICAL",
            title: "Critical: SKU-12345 below safety stock",
            body: "Current inventory: 5 units. Safety stock: 50 units.",
            alert_metadata: { sku_id: "SKU-12345" },
            status: "ACTIVE",
            created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
            acknowledged_by: null,
            acknowledged_at: null,
          },
          {
            id: "2",
            facility_id: "FAC001",
            module_id: "iwms",
            alert_type: "PICK_DELAY",
            severity: "HIGH",
            title: "Wave W-2024-0315 pick tasks delayed",
            body: "15 tasks pending for more than 2 hours",
            alert_metadata: { wave_id: "W-2024-0315" },
            status: "ACTIVE",
            created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            acknowledged_by: null,
            acknowledged_at: null,
          },
          {
            id: "3",
            facility_id: "FAC002",
            module_id: "ccvp",
            alert_type: "TEMP_EXCURSION",
            severity: "CRITICAL",
            title: "Temperature excursion in Zone C-4",
            body: "Temperature: 8.5°C. Threshold: 5°C",
            alert_metadata: { zone_id: "C-4", current_temp: 8.5 },
            status: "ACTIVE",
            created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            acknowledged_by: null,
            acknowledged_at: null,
          },
        ];
        setAlerts(mockAlerts);
        setTotal(mockAlerts.length);
        setError(null);
      }
    } finally {
      setLoading(false);
    }
  }, [facilityId]);

  useEffect(() => {
    // Initial fetch
    fetchAlerts();

    // Setup polling
    intervalRef.current = window.setInterval(fetchAlerts, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchAlerts]);

  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL").length;
  const highCount = alerts.filter((a) => a.severity === "HIGH").length;

  return {
    alerts,
    total,
    criticalCount,
    highCount,
    loading,
    error,
    refetch: fetchAlerts,
  };
};
