import React from "react";
import { TelemetryMessage } from "../types";
import { Zap, Activity, BatteryCharging, Gauge, AlertTriangle } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const EnergyPage: React.FC<Props> = ({ telemetry }) => {
  if (!telemetry) return null;
  const signals = telemetry.signals;
  const isSim = Boolean(telemetry.simulation_mode);
  const isConnected = Boolean(telemetry.plc_connected ?? telemetry.diagnostics?.connected);

  const voltage = signals.mains_voltage_v?.value ?? 0;
  const current = signals.mains_current_a?.value ?? 0;
  const activePower = signals.active_power_kw?.value ?? 0;
  const powerFactor = signals.power_factor?.value ?? 0;
  const frequency = signals.grid_frequency_hz?.value ?? 0;
  const cumulativeKwh = signals.cumulative_energy_kwh?.value ?? 0;
  const prodTotal = signals.production_count_total?.value ?? 0;

  const energyPerPartKwh = prodTotal > 0 ? (cumulativeKwh / prodTotal) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Energy & Electrical Metering</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              AC electrical telemetry acquired from industrial energy meter via PLC RS-485 Modbus RTU gateway
            </p>
          </div>
          <div>
            {isSim ? (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(168, 85, 247, 0.15)", border: "1px solid rgba(168, 85, 247, 0.4)", color: "#c084fc" }}>
                SIMULATED LOAD PROFILE
              </span>
            ) : isConnected ? (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(34, 197, 94, 0.15)", border: "1px solid rgba(34, 197, 94, 0.4)", color: "#4ade80" }}>
                REAL PLC METER ONLINE
              </span>
            ) : (
              <span style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#f87171" }}>
                PLC NOT DETECTED (METER OFFLINE)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Disconnected Notice */}
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
            <strong style={{ color: "#f87171", display: "block" }}>Physical PLC Not Detected:</strong>
            Simulation is OFF and the hardware PLC at <code className="mono">{telemetry.plc_host || "192.168.1.50"}:{telemetry.plc_port || 502}</code> is not responding. All energy meters and electrical parameters are held at 0.00 to prevent false readings.
          </div>
        </div>
      )}

      {/* Primary Energy KPI Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Active Power Load</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "#f59e0b", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "0.00" : activePower.toFixed(2)} <span style={{ fontSize: "16px", fontWeight: 400 }}>kW</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "No hardware detected" : "Instantaneous consumption"}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cumulative Energy</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--primary-cyan)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "0.0" : cumulativeKwh.toFixed(1)} <span style={{ fontSize: "16px", fontWeight: 400 }}>kWh</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "No hardware detected" : "Total accumulated"}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Specific Energy / Unit</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "#34d399", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "--" : energyPerPartKwh.toFixed(3)} <span style={{ fontSize: "16px", fontWeight: 400 }}>{(!isSim && !isConnected) ? "" : "kWh/part"}</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Carbon / energy efficiency</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Power Factor</div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--text-main)", marginTop: "4px" }}>
            {(!isSim && !isConnected) ? "--" : powerFactor.toFixed(2)}
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
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px", color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--text-main)" }}>
              {(!isSim && !isConnected) ? "0.0" : voltage.toFixed(1)} <span style={{ fontSize: "14px", fontWeight: 400 }}>V</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>AC RMS Voltage</div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Line Current</div>
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px", color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--text-main)" }}>
              {(!isSim && !isConnected) ? "0.0" : current.toFixed(1)} <span style={{ fontSize: "14px", fontWeight: 400 }}>A</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Total AC Current</div>
          </div>

          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Grid Frequency</div>
            <div className="mono" style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px", color: (!isSim && !isConnected) ? "var(--text-muted)" : "var(--text-main)" }}>
              {(!isSim && !isConnected) ? "0.00" : frequency.toFixed(2)} <span style={{ fontSize: "14px", fontWeight: 400 }}>Hz</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Nominal 50.00 Hz</div>
          </div>
        </div>
      </div>
    </div>
  );
};
