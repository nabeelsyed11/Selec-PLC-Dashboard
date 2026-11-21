import React, { useState, useEffect } from "react";
import { TelemetryMessage } from "../types";
import {
  Settings,
  Server,
  Wifi,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Save,
  Network,
  HelpCircle,
  Cpu,
  Activity,
  Radio,
} from "lucide-react";

interface Props {
  telemetry?: TelemetryMessage | null;
}

interface PLCConfig {
  plc_host: string;
  plc_port: number;
  plc_unit_id: number;
  simulation_mode: boolean;
  plc_timeout_seconds: number;
  connected?: boolean;
}

interface TestResult {
  success: boolean;
  message: string;
  rtt_ms?: number | null;
  has_exception?: boolean;
}

export const SettingsPage: React.FC<Props> = ({ telemetry }) => {
  const [config, setConfig] = useState<PLCConfig>({
    plc_host: "192.168.1.50",
    plc_port: 502,
    plc_unit_id: 1,
    simulation_mode: false,
    plc_timeout_seconds: 1.5,
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [saveStatus, setSaveStatus] = useState<{ success: boolean; message: string } | null>(null);

  // Fetch active configuration from backend
  const fetchConfig = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/system/config");
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (err) {
      console.error("Failed to load PLC config", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // Preset Handlers
  const applyPreset = (type: "physical" | "simulation") => {
    if (type === "physical") {
      setConfig((prev) => ({
        ...prev,
        plc_host: "192.168.1.50",
        plc_port: 502,
        plc_unit_id: 1,
        simulation_mode: false,
      }));
    } else {
      setConfig((prev) => ({
        ...prev,
        plc_host: "127.0.0.1",
        plc_port: 5020,
        plc_unit_id: 1,
        simulation_mode: true,
      }));
    }
    setTestResult(null);
    setSaveStatus(null);
  };

  // Test Connection
  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    setSaveStatus(null);
    try {
      const res = await fetch("/api/system/test-connection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plc_host: config.plc_host,
          plc_port: config.plc_port,
          plc_unit_id: config.plc_unit_id,
          timeout_seconds: 2.5,
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: `Network error sending test request: ${err.message || err}`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Save & Apply Configuration
  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveStatus(null);
    try {
      const res = await fetch("/api/system/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      let data: any = {};
      try {
        data = await res.json();
      } catch {
        const text = await res.text().catch(() => "");
        data = { detail: text || `Server returned HTTP ${res.status}` };
      }
      if (res.ok && data.success !== false) {
        setSaveStatus({
          success: true,
          message: data.message || "Configuration successfully saved and applied!",
        });
        setConfig((prev) => ({
          ...prev,
          ...data.config,
        }));
      } else {
        setSaveStatus({
          success: false,
          message: data.detail || data.message || "Failed to update configuration",
        });
      }
    } catch (err: any) {
      setSaveStatus({
        success: false,
        message: `Error saving config: ${err.message || err}`,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Header Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 700, display: "flex", alignItems: "center", gap: "10px" }}>
            <Settings style={{ width: "22px", height: "22px", color: "var(--primary-cyan)" }} />
            PLC Connection & Hardware Gateway Settings
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "4px" }}>
            Configure Selec MiBRX-6M Modbus TCP parameters in real time without restarting the Raspberry Pi.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={() => fetchConfig()}
            className="btn-secondary"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <RefreshCw style={{ width: "14px", height: "14px", animation: isLoading ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Real-time Hardware Detection Indicator */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          borderLeft: telemetry?.simulation_mode
            ? "6px solid #a855f7"
            : telemetry?.plc_connected
            ? "6px solid #22c55e"
            : "6px solid #ef4444",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "14px",
              height: "14px",
              borderRadius: "50%",
              backgroundColor: telemetry?.simulation_mode
                ? "#c084fc"
                : telemetry?.plc_connected
                ? "#34d399"
                : "#ef4444",
              boxShadow: telemetry?.plc_connected ? "0 0 10px #34d399" : "none",
            }}
          />
          <div>
            <div style={{ fontSize: "14px", fontWeight: 700 }}>
              {telemetry?.simulation_mode
                ? "Current Status: SIMULATION MODE ACTIVE"
                : telemetry?.plc_connected
                ? `Current Status: PHYSICAL PLC DETECTED & ONLINE (${telemetry.plc_host || config.plc_host}:${telemetry.plc_port || config.plc_port})`
                : `Current Status: PHYSICAL PLC NOT DETECTED (${telemetry?.plc_host || config.plc_host}:${telemetry?.plc_port || config.plc_port})`}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              {telemetry?.simulation_mode
                ? "The system is generating synthetic telemetry for testing. Real Modbus queries are disabled."
                : telemetry?.plc_connected
                ? "Physical Selec MiBRX-6M PLC is actively responding to Modbus TCP queries. Displaying 100% real values."
                : "No response from physical PLC. Ensure the Ethernet cable is connected to Raspberry Pi and both devices are on the same subnet (e.g. 192.168.1.x). All dashboard values are held at 0."}
            </div>
          </div>
        </div>

        <div>
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={isTesting}
            className="btn-secondary"
            style={{ fontSize: "12px", padding: "6px 12px" }}
          >
            {isTesting ? "Testing Ping & Modbus..." : "Ping / Test Now"}
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "24px" }}>
        {/* Main Configuration Card */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <Server style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
            Modbus TCP Network Parameters
          </h2>

          {/* Quick Presets */}
          <div style={{ marginBottom: "20px" }}>
            <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              Quick Presets:
            </label>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => applyPreset("physical")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: !config.simulation_mode ? "1px solid var(--primary-cyan)" : "1px solid var(--border-subtle)",
                  background: !config.simulation_mode ? "rgba(6, 182, 212, 0.15)" : "rgba(255, 255, 255, 0.05)",
                  color: !config.simulation_mode ? "var(--primary-cyan)" : "var(--text-main)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Physical PLC (192.168.1.50 : 502)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("simulation")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: config.simulation_mode ? "1px solid #a855f7" : "1px solid var(--border-subtle)",
                  background: config.simulation_mode ? "rgba(168, 85, 247, 0.15)" : "rgba(255, 255, 255, 0.05)",
                  color: config.simulation_mode ? "#c084fc" : "var(--text-main)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Virtual Simulator (127.0.0.1 : 5020)
              </button>
            </div>
          </div>

          <form onSubmit={handleSaveConfig} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Host Input */}
            <div>
              <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                PLC IP Address / Hostname
              </label>
              <input
                type="text"
                value={config.plc_host}
                onChange={(e) => setConfig({ ...config, plc_host: e.target.value })}
                placeholder="e.g. 192.168.1.50"
                required
                className="mono"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  background: "rgba(0,0,0,0.4)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "14px",
                }}
              />
              <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
                Static IP assigned to the Selec MiBRX-6M Ethernet module.
              </span>
            </div>

            {/* Port & Unit ID row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Modbus TCP Port
                </label>
                <input
                  type="number"
                  value={config.plc_port}
                  onChange={(e) => setConfig({ ...config, plc_port: parseInt(e.target.value) || 502 })}
                  required
                  className="mono"
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-subtle)",
                    color: "#fff",
                    fontSize: "14px",
                  }}
                />
                <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
                  Default is 502 for real hardware.
                </span>
              </div>

              <div>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Slave / Unit ID
                </label>
                <input
                  type="number"
                  value={config.plc_unit_id}
                  onChange={(e) => setConfig({ ...config, plc_unit_id: parseInt(e.target.value) || 1 })}
                  required
                  className="mono"
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-subtle)",
                    color: "#fff",
                    fontSize: "14px",
                  }}
                />
                <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
                  Default is 1 on Selec PLCs.
                </span>
              </div>
            </div>

            {/* Timeout & Simulation Toggle */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Socket Timeout (seconds)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={config.plc_timeout_seconds}
                  onChange={(e) => setConfig({ ...config, plc_timeout_seconds: parseFloat(e.target.value) || 1.5 })}
                  required
                  className="mono"
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-subtle)",
                    color: "#fff",
                    fontSize: "14px",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: "13px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                  Simulation Mode
                </label>
                <div
                  onClick={() => setConfig({ ...config, simulation_mode: !config.simulation_mode })}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    background: config.simulation_mode ? "rgba(168, 85, 247, 0.15)" : "rgba(6, 182, 212, 0.1)",
                    border: config.simulation_mode ? "1px solid #c084fc" : "1px solid var(--border-subtle)",
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  <div
                    style={{
                      width: "14px",
                      height: "14px",
                      borderRadius: "50%",
                      backgroundColor: config.simulation_mode ? "#c084fc" : "#06b6d4",
                    }}
                  />
                  <span style={{ fontSize: "13px", fontWeight: 600 }}>
                    {config.simulation_mode ? "Simulation ON (Virtual)" : "Simulation OFF (Physical)"}
                  </span>
                </div>
              </div>
            </div>

            {/* Test Connection Banner */}
            {testResult && (
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  background: testResult.success ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                  border: testResult.success ? "1px solid rgba(34, 197, 94, 0.4)" : "1px solid rgba(239, 68, 68, 0.4)",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "10px",
                  marginTop: "8px",
                }}
              >
                {testResult.success ? (
                  <CheckCircle2 style={{ width: "18px", height: "18px", color: "#4ade80", flexShrink: 0, marginTop: "2px" }} />
                ) : (
                  <AlertTriangle style={{ width: "18px", height: "18px", color: "#f87171", flexShrink: 0, marginTop: "2px" }} />
                )}
                <div style={{ fontSize: "13px" }}>
                  <div style={{ fontWeight: 600, color: testResult.success ? "#4ade80" : "#f87171" }}>
                    {testResult.success ? "Test Passed!" : "Connection Failed"}
                  </div>
                  <div style={{ color: "var(--text-main)", marginTop: "2px" }}>{testResult.message}</div>
                </div>
              </div>
            )}

            {/* Save Status Banner */}
            {saveStatus && (
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  background: saveStatus.success ? "rgba(6, 182, 212, 0.15)" : "rgba(239, 68, 68, 0.15)",
                  border: saveStatus.success ? "1px solid rgba(6, 182, 212, 0.4)" : "1px solid rgba(239, 68, 68, 0.4)",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  marginTop: "8px",
                }}
              >
                <CheckCircle2 style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
                <span style={{ fontSize: "13px", color: "var(--text-main)", fontWeight: 600 }}>{saveStatus.message}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting}
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  padding: "12px",
                  borderRadius: "6px",
                  border: "1px solid var(--border-subtle)",
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "#fff",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: isTesting ? "not-allowed" : "pointer",
                }}
              >
                <Wifi style={{ width: "16px", height: "16px", color: "var(--primary-cyan)" }} />
                {isTesting ? "Testing Link..." : "Test Connection"}
              </button>

              <button
                type="submit"
                disabled={isSaving}
                style={{
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  padding: "12px",
                  borderRadius: "6px",
                  border: "none",
                  background: "linear-gradient(135deg, #0891b2, #06b6d4)",
                  color: "#fff",
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor: isSaving ? "not-allowed" : "pointer",
                  boxShadow: "0 0 12px rgba(6, 182, 212, 0.3)",
                }}
              >
                <Save style={{ width: "16px", height: "16px" }} />
                {isSaving ? "Applying..." : "Save & Connect"}
              </button>
            </div>
          </form>
        </div>

        {/* Informational Diagnostics & Setup Guide */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Active Status Overview */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Activity style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
              Live Gateway Status
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(0,0,0,0.3)", borderRadius: "6px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Target Host:</span>
                <span className="mono" style={{ fontSize: "13px", fontWeight: 600 }}>{config.plc_host}:{config.plc_port}</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(0,0,0,0.3)", borderRadius: "6px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Active Protocol:</span>
                <span style={{ fontSize: "13px", fontWeight: 600 }}>Modbus TCP (Slave ID {config.plc_unit_id})</span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 12px", background: "rgba(0,0,0,0.3)", borderRadius: "6px" }}>
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Operating Mode:</span>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: config.simulation_mode ? "rgba(168, 85, 247, 0.2)" : "rgba(34, 197, 94, 0.2)",
                    color: config.simulation_mode ? "#c084fc" : "#4ade80",
                  }}
                >
                  {config.simulation_mode ? "VIRTUAL SIMULATION" : "PHYSICAL HARDWARE"}
                </span>
              </div>
            </div>
          </div>

          {/* Industrial Networking Quick Tips */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Network style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
              Direct Cable Quick Checklist
            </h2>

            <div style={{ fontSize: "13px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "10px", lineHeight: "1.5" }}>
              <div>
                <strong>1. Subnet Match:</strong> If Selec PLC is set to <code className="mono">192.168.1.50</code>, ensure your Pi Ethernet interface has static IP <code className="mono">192.168.1.100</code> with mask <code className="mono">255.255.255.0</code>.
              </div>
              <div>
                <strong>2. PLC RUN Mode:</strong> The Selec MiBRX-6M controller must be switched to <strong>RUN</strong> mode for its Modbus TCP server task to respond to port 502 requests.
              </div>
              <div>
                <strong>3. Seamless Persistence:</strong> Clicking <em>Save & Connect</em> updates your configuration in runtime memory and writes directly to the Pi's <code className="mono">.env</code> file so settings remain permanent across power restarts.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

