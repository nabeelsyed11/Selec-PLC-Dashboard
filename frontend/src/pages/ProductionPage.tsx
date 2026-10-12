import React, { useState } from "react";
import { TelemetryMessage } from "../types";
import { Layers, RotateCcw, Scale, TrendingUp, CheckCircle } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const ProductionPage: React.FC<Props> = ({ telemetry }) => {
  const [tareFeedback, setTareFeedback] = useState<string | null>(null);

  if (!telemetry) return null;
  const signals = telemetry.signals;

  const prodTotal = signals.production_count_total?.value ?? 0;
  const prodRate = signals.production_rate_ppm?.value ?? 0;
  const loadCellKg = signals.load_cell_weight?.value ?? 0;
  const loadCellRaw = signals.load_cell_weight?.raw_value ?? 0;

  const handleTareScale = async () => {
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
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Production & Throughput Analytics</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          Optical part sensor counts, shift totals, and inline platform weighing
        </p>
      </div>

      {/* Production KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cumulative Total Production</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, color: "var(--primary-cyan)", marginTop: "6px" }}>
            {prodTotal.toLocaleString()}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>Units produced since last reset</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Current Throughput Rate</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, color: "#34d399", marginTop: "6px" }}>
            {prodRate.toFixed(1)}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>Parts per minute (PPM)</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Platform Scale Reading</div>
          <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px" }}>
            {loadCellKg.toFixed(1)} <span style={{ fontSize: "18px", fontWeight: 400 }}>kg</span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-dim)", marginTop: "4px" }}>Raw counts: {loadCellRaw}</div>
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

          <button className="btn-primary" onClick={handleTareScale}>
            <RotateCcw style={{ width: "14px", height: "14px" }} /> Tare Zero Reference
          </button>
        </div>

        {tareFeedback && (
          <div style={{ marginTop: "16px", padding: "12px 16px", background: "rgba(16, 185, 129, 0.15)", borderRadius: "8px", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle style={{ width: "16px", height: "16px" }} /> {tareFeedback}
          </div>
        )}
      </div>
    </div>
  );
};
