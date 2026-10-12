import React, { useState } from "react";
import { TelemetryMessage, SignalData } from "../types";
import { Filter, Layers, CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const LiveMonitoringPage: React.FC<Props> = ({ telemetry }) => {
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");

  if (!telemetry) return null;
  const signals = Object.values(telemetry.signals);

  const filteredSignals = selectedGroup === "ALL"
    ? signals
    : signals.filter((s) => s.group === selectedGroup);

  const getQualityBadgeClass = (quality: string) => {
    switch (quality) {
      case "VALID": return "badge-quality-valid";
      case "STALE": return "badge-quality-stale";
      case "DISCONNECTED": return "badge-quality-disconnected";
      case "SIMULATED": return "badge-quality-simulated";
      default: return "";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header and Filter Tabs */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Live Signal Registry</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
            Real-time telemetry from Selec MiBRX-6M Modbus registers and direct sensors
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", background: "rgba(0,0,0,0.3)", padding: "4px", borderRadius: "8px" }}>
          {["ALL", "fast_group", "medium_group", "slow_group"].map((grp) => (
            <button
              key={grp}
              onClick={() => setSelectedGroup(grp)}
              style={{
                background: selectedGroup === grp ? "rgba(6, 182, 212, 0.2)" : "transparent",
                color: selectedGroup === grp ? "var(--primary-cyan)" : "var(--text-muted)",
                border: selectedGroup === grp ? "1px solid var(--border-highlight)" : "none",
                borderRadius: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {grp.toUpperCase().replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Signal Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
        {filteredSignals.map((sig) => (
          <div key={sig.name} className="glass-panel" style={{ padding: "18px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-main)" }}>
                  {sig.name.replace(/_/g, " ").toUpperCase()}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-dim)" }}>
                  Group: {sig.group}
                </div>
              </div>
              <span
                className={`mono ${getQualityBadgeClass(sig.quality)}`}
                style={{ fontSize: "10px", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}
              >
                {sig.quality}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", margin: "14px 0" }}>
              <div className="mono" style={{ fontSize: "28px", fontWeight: 700, color: "var(--primary-cyan)" }}>
                {typeof sig.value === "number" ? sig.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : sig.value}
              </div>
              <div style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 500 }}>
                {sig.unit}
              </div>
            </div>

            <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "10px", display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-dim)" }}>
              <span>Raw: <strong className="mono">{sig.raw_value}</strong></span>
              {sig.rtt_ms !== undefined && (
                <span>RTT: <strong className="mono" style={{ color: "#34d399" }}>{sig.rtt_ms.toFixed(1)} ms</strong></span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
