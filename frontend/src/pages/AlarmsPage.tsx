import React, { useState } from "react";
import { TelemetryMessage, AlarmItem } from "../types";
import { AlertTriangle, CheckCircle, ShieldAlert, Bell, Info } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const AlarmsPage: React.FC<Props> = ({ telemetry }) => {
  const [operatorName, setOperatorName] = useState<string>("operator_1");
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!telemetry) return null;
  const alarms = telemetry.alarms || [];

  const handleAcknowledge = async (alarmName: string) => {
    try {
      const res = await fetch(`/api/alarms/${alarmName}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_name: operatorName }),
      });
      if (res.ok) {
        setFeedback(`Alarm '${alarmName}' acknowledged.`);
        setTimeout(() => setFeedback(null), 3000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return { border: "1px solid rgba(239, 68, 68, 0.4)", background: "rgba(239, 68, 68, 0.12)", color: "#f87171" };
      case "WARNING":
        return { border: "1px solid rgba(245, 158, 11, 0.4)", background: "rgba(245, 158, 11, 0.12)", color: "#fbbf24" };
      default:
        return { border: "1px solid rgba(6, 182, 212, 0.4)", background: "rgba(6, 182, 212, 0.12)", color: "var(--primary-cyan)" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Alarms & Safety Events Console</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          Active machine safety interlocks, process thresholds, and operator acknowledgement audit
        </p>
      </div>

      {feedback && (
        <div style={{ padding: "12px 16px", background: "rgba(16, 185, 129, 0.15)", borderRadius: "8px", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", fontSize: "13px" }}>
          {feedback}
        </div>
      )}

      {/* Active Alarms Section */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
            <Bell style={{ width: "18px", height: "18px", color: alarms.length > 0 ? "#ef4444" : "var(--primary-cyan)" }} />
            Active Alarm Registry ({alarms.length})
          </h3>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
            <span style={{ color: "var(--text-muted)" }}>Acknowledge As:</span>
            <input
              type="text"
              value={operatorName}
              onChange={(e) => setOperatorName(e.target.value)}
              style={{
                background: "rgba(0,0,0,0.4)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-main)",
                borderRadius: "6px",
                padding: "4px 8px",
                fontSize: "12px",
              }}
            />
          </div>
        </div>

        {alarms.length === 0 ? (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
            <CheckCircle style={{ width: "40px", height: "40px", color: "#34d399", margin: "0 auto 12px" }} />
            <div style={{ fontSize: "15px", fontWeight: 500 }}>No Active Alarms</div>
            <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>All process parameters and safety interlocks are nominal.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {alarms.map((alarm) => {
              const sevStyle = getSeverityStyle(alarm.severity);
              return (
                <div
                  key={alarm.name}
                  style={{
                    padding: "16px",
                    borderRadius: "8px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "12px",
                    ...sevStyle,
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <AlertTriangle style={{ width: "16px", height: "16px" }} />
                      <strong style={{ fontSize: "14px" }}>{alarm.name}</strong>
                      <span className="mono" style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "4px", background: "rgba(0,0,0,0.3)" }}>
                        {alarm.severity}
                      </span>
                    </div>
                    <div style={{ fontSize: "13px", marginTop: "4px", color: "var(--text-main)" }}>
                      {alarm.message}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                      Triggered: {alarm.triggered_at}
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    {alarm.state === "ACKNOWLEDGED" ? (
                      <span className="mono" style={{ fontSize: "12px", color: "#34d399" }}>
                        ACKNOWLEDGED by {alarm.acknowledged_by}
                      </span>
                    ) : (
                      <button className="btn-primary" onClick={() => handleAcknowledge(alarm.name)}>
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
