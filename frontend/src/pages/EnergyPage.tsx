import React from "react";
import { TelemetryMessage } from "../types";
import { Zap, Activity, BatteryCharging, Gauge } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const EnergyPage: React.FC<Props> = ({ telemetry }) => {
  if (!telemetry) return null;
  const signals = telemetry.signals;

  const voltage = signals.mains_voltage_v?.value ?? 0;
  const current = signals.mains_current_a?.value ?? 0;
  const activePower = signals.active_power_kw?.value ?? 0;
  const powerFactor = signals.power_factor?.value ?? 0;
  const frequency = signals.grid_frequency_hz?.value ?? 0;
  const cumulativeKwh = signals.cumulative_energy_kwh?.value ?? 0;
  const prodTotal = signals.production_count_total?.value ?? 1;

  const energyPerPartKwh = prodTotal > 0 ? (cumulativeKwh / prodTotal) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Energy & Electrical Metering</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          AC electrical telemetry acquired from industrial energy meter via PLC RS-485 Modbus RTU gateway
        </p>
      </div>

      {/* Primary Energy KPI Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Active Power Load</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: "#f59e0b", marginTop: "4px" }}>
            {activePower.toFixed(2)} <span style={{ fontSize: "16px", fontWeight: 400 }}>kW</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Instantaneous consumption</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cumulative Energy</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: "var(--primary-cyan)", marginTop: "4px" }}>
            {cumulativeKwh.toFixed(1)} <span style={{ fontSize: "16px", fontWeight: 400 }}>kWh</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Total accumulated</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Specific Energy / Unit</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: "#34d399", marginTop: "4px" }}>
            {energyPerPartKwh.toFixed(3)} <span style={{ fontSize: "16px", fontWeight: 400 }}>kWh/part</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Carbon / energy efficiency</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Power Factor</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "4px" }}>
            {powerFactor.toFixed(2)}
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Efficiency rating</div>
        </div>
      </div>

      {/* Grid Parameters Table */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>3-Phase Mains Electrical Parameters</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Line Voltage</div>
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>
              {voltage.toFixed(1)} <span style={{ fontSize: "14px", fontWeight: 400 }}>V</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>AC RMS Voltage</div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Line Current</div>
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>
              {current.toFixed(1)} <span style={{ fontSize: "14px", fontWeight: 400 }}>A</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Total AC Current</div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Grid Frequency</div>
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>
              {frequency.toFixed(2)} <span style={{ fontSize: "14px", fontWeight: 400 }}>Hz</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Nominal 50.00 Hz</div>
          </div>
        </div>
      </div>
    </div>
  );
};
