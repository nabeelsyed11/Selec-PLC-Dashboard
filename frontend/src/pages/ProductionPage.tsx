import React, { useState } from "react";
import { TelemetryMessage } from "../types";
import { Layers, RotateCcw, Scale, TrendingUp, CheckCircle, AlertTriangle } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const ProductionPage: React.FC<Props> = ({ telemetry }) => {
  const [tareFeedback, setTareFeedback] = useState<string | null>(null);

  if (!telemetry) return null;
  const signals = telemetry.signals;
  const isSim = Boolean(telemetry.simulation_mode);
  const isConnected = Boolean(telemetry.plc_connected ?? telemetry.diagnostics?.connected);

  const prodTotal = signals.production_count_total?.value ?? 0;
  const prodRate = signals.production_rate_ppm?.value ?? 0;
  const loadCellKg = signals.load_cell_weight?.value ?? 0;
  const loadCellRaw = signals.load_cell_weight?.raw_value ?? 0;

  const handleTareScale = async () => {
    if (!isSim && !isConnected) return;
    try {
      const res = await fetch("/api/production/tare-loadcell", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_counts: loadCellRaw }),
      });
      if (res.ok) {
        setTareFeedback(`Successfully calibrated zero tare at ${loadCellRaw} raw counts.`);
        setTimeout(() => setTareFeedback(null), 4000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Production & Throughput Analytics</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              Optical part sensor counts, shift totals, and inline platform weighing
            </p>
          </div>
          <div>
            {isSim ? (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(168, 85, 247, 0.15)", border: "1px solid rgba(168, 85, 247, 0.4)", color: "#c084fc" }}>
                SIMULATED PRODUCTION DATA
              </span>
            ) : isConnected ? (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(34, 197, 94, 0.15)", border: "1px solid rgba(34, 197, 94, 0.4)", color: "#4ade80" }}>
                PHYSICAL SENSORS ONLINE
              </span>
            ) : (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#f87171" }}>
                PLC NOT DETECTED (OFFLINE)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Disconnection Notice */}
      {!isSim && !isConnected && (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: "8px",
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.35)",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}
        >
          <AlertTriangle style={{ width: "24px", height: "24px", color: "#f87171", flexShrink: 0 }} />
          <div style={{ fontSize: "13px", lineHeight: "1.5" }}>
            <strong style={{ color: "#f87171", display: "block" }}>Physical Selec PLC Not Detected:</strong>
            Simulation is OFF and the hardware PLC at <code className="mono">{telemetry.plc_host || "192.168.1.50"}:{telemetry.plc_port || 502}</code> is disconnected. Production counters and load cell readings are zeroed.
          </div>
        </div>
      )}

      {/* Production KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cumulative Total Production</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--primary-cyan)", marginTop: "6px" }}>
            {(!isSim && !isConnected) ? "0" : prodTotal.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "No hardware detected" : "Units produced since last reset"}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Current Throughput Rate</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "#34d399", marginTop: "6px" }}>
            {(!isSim && !isConnected) ? "0.0" : prodRate.toFixed(1)}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "No hardware detected" : "Parts per minute (PPM)"}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Platform Scale Reading</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--text-main)", marginTop: "6px" }}>
            {(!isSim && !isConnected) ? "0.0" : loadCellKg.toFixed(1)} <span style={{ fontSize: "18px", fontWeight: 400 }}>kg</span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "Disconnected" : `Raw counts: ${loadCellRaw}`}
          </div>
        </div>
      </div>

      {/* Load Cell Calibration Card */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <Scale style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
              Load Cell Zero Tare Calibration
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "2px" }}>
              Ensure platform is unloaded and empty before initiating zero reference calibration.
            </p>
          </div>

          <button
            className="btn-primary"
            onClick={handleTareScale}
            disabled={!isSim && !isConnected}
            style={{ opacity: (!isSim && !isConnected) ? 0.5 : 1, cursor: (!isSim && !isConnected) ? "not-allowed" : "pointer" }}
          >
            <RotateCcw style={{ width: "14px", height: "14px" }} /> Tare Zero Reference
          </button>
        </div>

        {tareFeedback && (
          <div style={{ marginTop: "16px", padding: "12px 16px", background: "rgba(160, 185, 129, 0.15)", borderRadius: "8px", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle style={{ width: "16px", height: "16px" }} /> {tareFeedback}
          </div>
        )}
      </div>
    </div>
  );
};
