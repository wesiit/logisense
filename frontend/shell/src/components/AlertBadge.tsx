import React from "react";

interface AlertBadgeProps {
  count: number;
  severity?: "critical" | "high" | "medium" | "low" | "default";
  className?: string;
}

export const AlertBadge: React.FC<AlertBadgeProps> = ({
  count,
  severity = "default",
  className = "",
}) => {
  if (count === 0) return null;

  const severityClasses = {
    critical: "bg-red-500 text-white animate-pulse",
    high: "bg-orange-500 text-white",
    medium: "bg-yellow-500 text-gray-900",
    low: "bg-blue-500 text-white",
    default: "bg-gray-500 text-white",
  };

  const displayCount = count > 99 ? "99+" : count.toString();

  return (
    <span
      className={`
        inline-flex items-center justify-center
        min-w-[1.25rem] h-5 px-1.5
        text-xs font-semibold rounded-full
        ${severityClasses[severity]}
        ${className}
      `}
    >
      {displayCount}
    </span>
  );
};

interface AlertSummaryBadgeProps {
  criticalCount: number;
  highCount: number;
  className?: string;
}

export const AlertSummaryBadge: React.FC<AlertSummaryBadgeProps> = ({
  criticalCount,
  highCount,
  className = "",
}) => {
  if (criticalCount === 0 && highCount === 0) {
    return (
      <span className={`text-xs text-green-600 font-medium ${className}`}>
        No alerts
      </span>
    );
  }

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {criticalCount > 0 && (
        <AlertBadge count={criticalCount} severity="critical" />
      )}
      {highCount > 0 && <AlertBadge count={highCount} severity="high" />}
    </div>
  );
};
