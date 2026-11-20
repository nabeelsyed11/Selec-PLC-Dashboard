import React from "react";
import { TelemetryMessage } from "../types";
import {
  Activity,
  Cpu,
  Gauge,
  HardDrive,
  Radio,
  Server,
  Thermometer,
  Zap,
  Clock,
  Layers,
  AlertTriangle,
  RotateCw,
} from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
  isConnected: boolean;
  renderLatencyMs: number;
}

export const OverviewPage: React.FC<Props> = ({ telemetry, isConnected, renderLatencyMs }) => {
  if (!telemetry) {
    return (
      <div className="glass-panel" style={{ padding: "40px", textAlign: "center" }}>
        <Radio style={{ width: "48px", height: "48px", color: "var(--primary-cyan)", animation: "spin 2s linear infinite" }} />
        <h2 style={{ marginTop: "16px", fontWeight: 600 }}>Connecting to Industrial IoT Gateway...</h2>
        <p style={{ color: "var(--text-muted)", marginTop: "8px" }}>Establishing WebSocket connection to Raspberry Pi 5</p>
      </div>
    );
  }

  const { machine_state, signals, latency, alarms, vibration, telemetry: pi_sys, diagnostics } = telemetry;

  const displayState =
    machine_state === "COMM_LOST"
      ? "COMM LOST (PLC OFFLINE)"
      : machine_state === "RUNNING"
        ? "RUNNING"
        : "READY / ONLINE";

  const currentColor =
    machine_state === "COMM_LOST"
      ? "#ef4444"
      : machine_state === "RUNNING"
        ? "#34d399"
        : "var(--primary-cyan)";

  const fastLatency = latency.groups?.fast_group;
  const loadCellKg = signals.load_cell_weight?.value ?? 0;
  const motorTempC = signals.motor_temperature?.value ?? 0;
  const beltSpeedMps = signals.conveyor_belt_speed?.value ?? 0;
  const prodTotal = signals.production_count_total?.value ?? 0;
  const prodRate = signals.production_rate_ppm?.value ?? 0;
  const activePowerKw = signals.active_power_kw?.value ?? 0;
  const vfdRunning = signals.vfd_running_status?.value === 1;
  const beltSlip = signals.belt_slip_sensor?.value === 1;

  // New SCADA Registers
  const cycle1 = signals.cycle_1_mx2?.value === 1;
  const cycle2 = signals.cycle_2_mx3?.value === 1;
  const cycle3 = signals.cycle_3_mx4?.value === 1;
  const cycle4 = signals.cycle_4_mx5?.value === 1;
  const vfdOutHz = signals.scaled_out_vfd_qw0?.value ?? signals.vfd_output_frequency?.value ?? 0;
  const iw0Raw = signals.plc_input_iw0?.value ?? 0;
  const voltageTd3 = signals.mains_voltage_td3?.value ?? signals.mains_voltage_v?.value ?? 0;
  const currentTd4 = signals.mains_current_td4?.value ?? signals.mains_current_a?.value ?? 0;
  const pfTd5 = signals.power_factor_td5?.value ?? signals.power_factor?.value ?? 0;

  // One-shot Input Delays (captured at the moment input is pressed or register updated)
  const vfdOutTriggerDelay = signals.scaled_out_vfd_qw0?.trigger_delay_ms ?? signals.vfd_output_frequency?.trigger_delay_ms ?? null;
  const iw0TriggerDelay = signals.plc_input_iw0?.trigger_delay_ms ?? null;
  const voltageTriggerDelay = signals.mains_voltage_td3?.trigger_delay_ms ?? signals.mains_voltage_v?.trigger_delay_ms ?? null;
  const currentTriggerDelay = signals.mains_current_td4?.trigger_delay_ms ?? signals.mains_current_a?.trigger_delay_ms ?? null;
  const pfTriggerDelay = signals.power_factor_td5?.trigger_delay_ms ?? signals.power_factor?.trigger_delay_ms ?? null;

  // SCADA Cycle Telemetry with exact one-shot trigger delay when pressed
  const cyclesList = [
    telemetry.cycles?.cycle_1 || { cycle_num: 1, name: "First Cycle", plc_tag: "MX2", modbus_coil: 514, active: cycle1, trigger_delay_ms: null, last_pressed_at: null },
    telemetry.cycles?.cycle_2 || { cycle_num: 2, name: "Second Cycle", plc_tag: "MX3", modbus_coil: 515, active: cycle2, trigger_delay_ms: null, last_pressed_at: null },
    telemetry.cycles?.cycle_3 || { cycle_num: 3, name: "Third Cycle", plc_tag: "MX4", modbus_coil: 516, active: cycle3, trigger_delay_ms: null, last_pressed_at: null },
    telemetry.cycles?.cycle_4 || { cycle_num: 4, name: "Fourth Cycle", plc_tag: "MX5", modbus_coil: 517, active: cycle4, trigger_delay_ms: null, last_pressed_at: null },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Machine Status Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          borderLeft: `6px solid ${currentColor}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            className="state-pulse"
            style={{
              width: "18px",
              height: "18px",
              borderRadius: "50%",
              backgroundColor: currentColor,
              boxShadow: `0 0 12px ${currentColor}`,
            }}
          />
          <div>
            <div style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-muted)" }}>
              Operating State
            </div>
            <div style={{ fontSize: "24px", fontWeight: 700, letterSpacing: "0.5px", color: currentColor }}>
              {displayState}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Modbus Link</div>
            <div style={{ fontWeight: 600, color: telemetry.simulation_mode ? "#c084fc" : diagnostics.connected ? "#34d399" : "#f87171" }}>
              {telemetry.simulation_mode
                ? "SIMULATION (MOCK)"
                : diagnostics.connected
                  ? `PLC ONLINE (${telemetry.plc_host || "192.168.1.50"}:${telemetry.plc_port || 502})`
                  : "PLC NOT DETECTED"}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Modbus RTT (P50)</div>
            <div className="mono" style={{ fontWeight: 600, color: "var(--primary-cyan)" }}>
              {diagnostics.connected || telemetry.simulation_mode ? (fastLatency ? `${fastLatency.rtt_p50_ms.toFixed(1)} ms` : "--") : "--"}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>UI Render Lag</div>
            <div className="mono" style={{ fontWeight: 600, color: "#a78bfa" }}>
              {renderLatencyMs.toFixed(1)} ms
            </div>
          </div>
        </div>
      </div>

      {/* Disconnection Notice Banner */}
      {!telemetry.simulation_mode && !diagnostics.connected && (
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
            Simulation is <span style={{ fontWeight: 700 }}>OFF</span> and no physical PLC response was received at{" "}
            <code className="mono">{telemetry.plc_host || "192.168.1.50"}:{telemetry.plc_port || 502}</code>. All live signals are held at zero to guarantee no false telemetry is displayed. Verify your Ethernet cable connection, or configure the IP in <strong>PLC Settings</strong>.
          </div>
        </div>
      )}

      {/* SCADA Process Cycle Sequencer (MX2 - MX5) */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <div style={{ fontSize: "13px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--primary-cyan)", display: "flex", alignItems: "center", gap: "8px" }}>
            <RotateCw style={{ width: "16px", height: "16px" }} />
            SCADA Process Cycle Sequencer (MX2 - MX5)
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Modbus Coils: <strong>514 - 517</strong>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px" }}>
          {cyclesList.map((c) => (
            <div
              key={c.cycle_num}
              style={{
                background: c.active ? "rgba(16, 185, 129, 0.15)" : "rgba(0, 0, 0, 0.3)",
                border: c.active ? "1px solid rgba(16, 185, 129, 0.6)" : "1px solid var(--border-subtle)",
                boxShadow: c.active ? "0 0 15px rgba(16, 185, 129, 0.25)" : "none",
                borderRadius: "10px",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "12px",
                transition: "all 0.2s ease",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    {c.name}
                  </span>
                  <span
                    className="mono"
                    style={{
                      fontSize: "11px",
                      padding: "2px 8px",
                      borderRadius: "12px",
                      background: "rgba(255, 255, 255, 0.06)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-muted)",
                      fontWeight: 600,
                    }}
                  >
                    {c.plc_tag}
                  </span>
                </div>
                <div style={{ fontSize: "18px", fontWeight: 800, color: "#fff", margin: "6px 0 2px" }}>
                  Cycle {c.cycle_num}
                </div>
                <div className="mono" style={{ fontSize: "11px", color: "#9ca3af" }}>
                  PLC: <strong style={{ color: "var(--primary-cyan)" }}>{c.plc_tag}</strong> | Coil: {c.modbus_coil}
                </div>
              </div>

              {/* Input Display Delay & Status */}
              <div
                style={{
                  background: "rgba(0,0,0,0.4)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                  border: c.active ? "1px solid rgba(16, 185, 129, 0.4)" : "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 10px",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontWeight: 800,
                      backgroundColor: c.active ? "#10b981" : "#1f2937",
                      color: c.active ? "#000" : "#9ca3af",
                      boxShadow: c.active ? "0 0 10px rgba(16, 185, 129, 0.5)" : "none",
                    }}
                  >
                    {c.active ? "● ACTIVE" : "STANDBY"}
                  </span>
                  {c.last_pressed_at ? (
                    <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Pressed: {c.last_pressed_at}
                    </span>
                  ) : (
                    <span className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Not Triggered
                    </span>
                  )}
                </div>

                <div
                  style={{
                    background: "rgba(6, 182, 212, 0.08)",
                    border: "1px solid rgba(6, 182, 212, 0.25)",
                    borderRadius: "6px",
                    padding: "8px 10px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Input Delay:</span>
                  <span className="mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--primary-cyan)" }}>
                    {c.trigger_delay_ms != null && c.trigger_delay_ms > 0
                      ? `⚡ ${c.trigger_delay_ms.toFixed(1)} ms`
                      : "-- ms"}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SCADA Drive & Electrical Telemetry Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        {/* VFD Scaled Out Frequency (QW0) */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "var(--primary-cyan)" }}>
                Scaled Out / VFD Out
              </span>
              <span className="mono" style={{ fontSize: "11px" }}>QW0 (30768)</span>
            </div>
            <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px", color: "#fff" }}>
              {vfdOutHz.toFixed(1)} <span style={{ fontSize: "18px", color: "var(--primary-cyan)" }}>Hz</span>
            </div>
          </div>
          <div
            style={{
              marginTop: "12px",
              paddingTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>Drive Output (Real)</span>
            <span className="mono" style={{ color: "var(--primary-cyan)", fontWeight: 600 }}>
              Input Delay: {vfdOutTriggerDelay != null && vfdOutTriggerDelay > 0 ? `⚡ ${vfdOutTriggerDelay.toFixed(1)} ms` : "-- ms"}
            </span>
          </div>
        </div>

        {/* Process Input Word (IW0) */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#34d399" }}>
                Process Input (IW0)
              </span>
              <span className="mono" style={{ fontSize: "11px" }}>IW0 (40768)</span>
            </div>
            <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px", color: "#fff" }}>
              {iw0Raw} <span style={{ fontSize: "18px", color: "#34d399" }}>raw</span>
            </div>
          </div>
          <div
            style={{
              marginTop: "12px",
              paddingTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>Input Register (Int16)</span>
            <span className="mono" style={{ color: "#34d399", fontWeight: 600 }}>
              Input Delay: {iw0TriggerDelay != null && iw0TriggerDelay > 0 ? `⚡ ${iw0TriggerDelay.toFixed(1)} ms` : "-- ms"}
            </span>
          </div>
        </div>

        {/* Mains Voltage (TD3) */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#f59e0b" }}>
                Mains Voltage
              </span>
              <span className="mono" style={{ fontSize: "11px" }}>TD3 (41542)</span>
            </div>
            <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px", color: "#fff" }}>
              {voltageTd3.toFixed(1)} <span style={{ fontSize: "18px", color: "#f59e0b" }}>V</span>
            </div>
          </div>
          <div
            style={{
              marginTop: "12px",
              paddingTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>AC Line Potential</span>
            <span className="mono" style={{ color: "#f59e0b", fontWeight: 600 }}>
              Input Delay: {voltageTriggerDelay != null && voltageTriggerDelay > 0 ? `⚡ ${voltageTriggerDelay.toFixed(1)} ms` : "-- ms"}
            </span>
          </div>
        </div>

        {/* Load Current (TD4) */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#60a5fa" }}>
                Load Current
              </span>
              <span className="mono" style={{ fontSize: "11px" }}>TD4 (41544)</span>
            </div>
            <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px", color: "#fff" }}>
              {currentTd4.toFixed(2)} <span style={{ fontSize: "18px", color: "#60a5fa" }}>A</span>
            </div>
          </div>
          <div
            style={{
              marginTop: "12px",
              paddingTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>Current Draw (Real)</span>
            <span className="mono" style={{ color: "#60a5fa", fontWeight: 600 }}>
              Input Delay: {currentTriggerDelay != null && currentTriggerDelay > 0 ? `⚡ ${currentTriggerDelay.toFixed(1)} ms` : "-- ms"}
            </span>
          </div>
        </div>

        {/* Power Factor (TD4/TD5) */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#c084fc" }}>
                Power Factor
              </span>
              <span className="mono" style={{ fontSize: "11px" }}>TD4/5 (41546)</span>
            </div>
            <div className="mono" style={{ fontSize: "36px", fontWeight: 700, marginTop: "6px", color: "#fff" }}>
              {pfTd5.toFixed(2)} <span style={{ fontSize: "18px", color: "#c084fc" }}>PF</span>
            </div>
          </div>
          <div
            style={{
              marginTop: "12px",
              paddingTop: "8px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "11px",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>Efficiency Factor</span>
            <span className="mono" style={{ color: "#c084fc", fontWeight: 600 }}>
              Input Delay: {pfTriggerDelay != null && pfTriggerDelay > 0 ? `⚡ ${pfTriggerDelay.toFixed(1)} ms` : "-- ms"}
            </span>
          </div>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
        {/* KPI 1: Production Count */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Production Total</span>
            <Layers style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px" }}>
            {prodTotal.toLocaleString()}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Rate: <span className="mono" style={{ color: "#34d399", fontWeight: 600 }}>{prodRate.toFixed(1)}</span> parts/min
          </div>
        </div>

        {/* KPI 2: Load Cell */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Platform Load Cell</span>
            <Gauge style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px" }}>
            {loadCellKg.toFixed(1)} <span style={{ fontSize: "18px", fontWeight: 400 }}>kg</span>
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Calibrated Scale (0 - 500 kg)
          </div>
        </div>

        {/* KPI 3: Motor Temperature */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Motor Stator Temp</span>
            <Thermometer style={{ width: "18px", height: "18px", color: motorTempC > 75 ? "#ef4444" : "var(--primary-cyan)" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px", color: motorTempC > 75 ? "#ef4444" : "inherit" }}>
            {motorTempC.toFixed(1)} <span style={{ fontSize: "18px", fontWeight: 400 }}>°C</span>
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Limit: 75°C Warn / 90°C Trip
          </div>
        </div>

        {/* KPI 4: Conveyor Motion & Slip */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Belt Linear Speed</span>
            <RotateCw style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px" }}>
            {beltSpeedMps.toFixed(2)} <span style={{ fontSize: "18px", fontWeight: 400 }}>m/s</span>
          </div>
          <div style={{ fontSize: "13px", marginTop: "4px" }}>
            Status: {beltSlip ? (
              <span style={{ color: "#ef4444", fontWeight: 600 }}>SLIP ALARM</span>
            ) : (
              <span style={{ color: "#34d399", fontWeight: 600 }}>Normal Traction</span>
            )}
          </div>
        </div>

        {/* KPI 5: Active Power */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Active Power Load</span>
            <Zap style={{ width: "18px", height: "18px", color: "#f59e0b" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px" }}>
            {activePowerKw.toFixed(2)} <span style={{ fontSize: "18px", fontWeight: 400 }}>kW</span>
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Cumulative: {signals.cumulative_energy_kwh?.value.toFixed(1) ?? "--"} kWh
          </div>
        </div>

        {/* KPI 6: Vibration RMS */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)" }}>
            <span style={{ fontSize: "13px", fontWeight: 500 }}>Vibration RMS</span>
            <Activity style={{ width: "18px", height: "18px", color: vibration.warning_alarm ? "#ef4444" : "var(--primary-cyan)" }} />
          </div>
          <div className="mono" style={{ fontSize: "32px", fontWeight: 700, marginTop: "8px", color: vibration.warning_alarm ? "#ef4444" : "inherit" }}>
            {vibration.rms_g.toFixed(2)} <span style={{ fontSize: "18px", fontWeight: 400 }}>g</span>
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Dominant: <span className="mono" style={{ color: "var(--primary-cyan)" }}>{vibration.dominant_frequency_hz} Hz</span>
          </div>
        </div>
      </div>

      {/* Gateway System Telemetry Footer */}
      <div className="glass-panel" style={{ padding: "20px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Server style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
          Raspberry Pi 5 Edge Gateway Health
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
          <div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>CPU Utilization</div>
            <div className="mono" style={{ fontSize: "18px", fontWeight: 600, marginTop: "2px" }}>
              {pi_sys.cpu_percent.toFixed(1)} %
            </div>
            <div style={{ height: "4px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "6px" }}>
              <div style={{ height: "100%", width: `${Math.min(100, pi_sys.cpu_percent)}%`, backgroundColor: "var(--primary-cyan)", borderRadius: "2px" }} />
            </div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>RAM Memory</div>
            <div className="mono" style={{ fontSize: "18px", fontWeight: 600, marginTop: "2px" }}>
              {pi_sys.memory_percent.toFixed(1)} % ({pi_sys.memory_used_mb} MB)
            </div>
            <div style={{ height: "4px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "6px" }}>
              <div style={{ height: "100%", width: `${pi_sys.memory_percent}%`, backgroundColor: "#a78bfa", borderRadius: "2px" }} />
            </div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>System Uptime</div>
            <div className="mono" style={{ fontSize: "18px", fontWeight: 600, marginTop: "2px" }}>
              {Math.floor(pi_sys.uptime_seconds / 3600)}h {Math.floor((pi_sys.uptime_seconds % 3600) / 60)}m {pi_sys.uptime_seconds % 60}s
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>Continuous execution</div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Active Alarms</div>
            <div className="mono" style={{ fontSize: "18px", fontWeight: 600, marginTop: "2px", color: alarms.length > 0 ? "#ef4444" : "#34d399" }}>
              {alarms.length} Active
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              {alarms.length > 0 ? "Requires Operator Attention" : "All Systems Nominal"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
