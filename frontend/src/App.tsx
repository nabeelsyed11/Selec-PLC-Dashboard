import React, { useState } from "react";
import { useTelemetry } from "./services/websocket";
import { OverviewPage } from "./pages/OverviewPage";
import { LiveMonitoringPage } from "./pages/LiveMonitoringPage";
import { LatencyAnalyticsPage } from "./pages/LatencyAnalyticsPage";
import { VibrationPage } from "./pages/VibrationPage";
import { ProductionPage } from "./pages/ProductionPage";
import { EnergyPage } from "./pages/EnergyPage";
import { AlarmsPage } from "./pages/AlarmsPage";
import { ControlPanelPage } from "./pages/ControlPanelPage";
import { SettingsPage } from "./pages/SettingsPage";

import {
  LayoutDashboard,
  Activity,
  Clock,
  Waves,
  Layers,
  Zap,
  Bell,
  ShieldCheck,
  Radio,
  Cpu,
  Settings,
} from "lucide-react";

export function App() {
  const { data: telemetry, isConnected, renderLatencyMs } = useTelemetry();
  const [activeTab, setActiveTab] = useState<string>("overview");

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "live", label: "Live Monitoring", icon: Activity },
    { id: "latency", label: "Latency Analytics", icon: Clock },
    { id: "vibration", label: "Vibration FFT", icon: Waves },
    { id: "production", label: "Production", icon: Layers },
    { id: "energy", label: "Energy Monitor", icon: Zap },
    { id: "alarms", label: "Alarms & Events", icon: Bell, badge: telemetry?.alarms.length },
    { id: "control", label: "Safe Control", icon: ShieldCheck },
    { id: "settings", label: "PLC Settings", icon: Settings },
  ];

  const machineState = telemetry?.machine_state || "COMM_LOST";

  const renderContent = () => {
    switch (activeTab) {
      case "overview":
        return <OverviewPage telemetry={telemetry} isConnected={isConnected} renderLatencyMs={renderLatencyMs} />;
      case "live":
        return <LiveMonitoringPage telemetry={telemetry} />;
      case "latency":
        return <LatencyAnalyticsPage telemetry={telemetry} renderLatencyMs={renderLatencyMs} />;
      case "vibration":
        return <VibrationPage telemetry={telemetry} />;
      case "production":
        return <ProductionPage telemetry={telemetry} />;
      case "energy":
        return <EnergyPage telemetry={telemetry} />;
      case "alarms":
        return <AlarmsPage telemetry={telemetry} />;
      case "control":
        return <ControlPanelPage telemetry={telemetry} />;
      case "settings":
        return <SettingsPage telemetry={telemetry} />;
      default:
        return null;
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Industrial App Bar */}
      <header
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(11, 15, 25, 0.85)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 100,
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #0891b2, #06b6d4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 15px rgba(6, 182, 212, 0.4)",
            }}
          >
            <Radio style={{ width: "20px", height: "20px", color: "#fff" }} />
          </div>
          <div>
            <div style={{ fontSize: "16px", fontWeight: 700, letterSpacing: "0.5px" }}>
              SELEC MiBRX-6M <span style={{ color: "var(--primary-cyan)", fontWeight: 400 }}>IIoT EDGE</span>
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Raspberry Pi 5 Gateway &middot; High-Precision Modbus TCP Telemetry
            </div>
          </div>
        </div>

        {/* Global Live Indicators */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          {/* Hardware Connection / Simulation Status Badge */}
          {telemetry?.simulation_mode ? (
            <div
              style={{
                padding: "4px 12px",
                borderRadius: "20px",
                fontSize: "12px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(168, 85, 247, 0.15)",
                border: "1px solid rgba(168, 85, 247, 0.4)",
                color: "#c084fc",
              }}
            >
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#c084fc" }} />
              <span>SIMULATION: ON (MOCK DATA)</span>
            </div>
          ) : telemetry?.plc_connected ? (
            <div
              style={{
                padding: "4px 12px",
                borderRadius: "20px",
                fontSize: "12px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(34, 197, 94, 0.15)",
                border: "1px solid rgba(34, 197, 94, 0.4)",
                color: "#4ade80",
              }}
            >
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#34d399", boxShadow: "0 0 8px #34d399" }} />
              <span>PLC DETECTED ({telemetry.plc_host || "192.168.1.50"}:{telemetry.plc_port || 502})</span>
            </div>
          ) : (
            <div
              style={{
                padding: "4px 12px",
                borderRadius: "20px",
                fontSize: "12px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                color: "#f87171",
              }}
            >
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ef4444" }} />
              <span>PLC NOT DETECTED (DISCONNECTED)</span>
            </div>
          )}

          {/* Machine State Pill */}
          <div
            style={{
              padding: "4px 12px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(0,0,0,0.4)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor:
                  machineState === "RUNNING"
                    ? "#34d399"
                    : machineState === "COMM_LOST"
                      ? "#ef4444"
                      : "var(--primary-cyan)",
                boxShadow:
                  machineState === "RUNNING"
                    ? "0 0 8px #34d399"
                    : machineState === "COMM_LOST"
                      ? "0 0 8px #ef4444"
                      : "0 0 8px var(--primary-cyan)",
              }}
            />
            <span style={{ color: "var(--text-main)" }}>
              {machineState === "COMM_LOST"
                ? "COMM LOST (PLC OFFLINE)"
                : machineState === "RUNNING"
                  ? "RUNNING"
                  : "READY / ONLINE"}
            </span>
          </div>

          {/* WebSocket Link Status */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: isConnected ? "#34d399" : "#ef4444",
                boxShadow: isConnected ? "0 0 8px #34d399" : "none",
              }}
            />
            <span style={{ color: "var(--text-muted)" }}>
              {isConnected ? "WS 10Hz Live" : "Disconnected"}
            </span>
          </div>

          {/* Render Latency Monitor */}
          <div className="mono" style={{ fontSize: "12px", color: "#a78bfa" }}>
            DOM Lag: <strong>{renderLatencyMs.toFixed(1)} ms</strong>
          </div>

          {/* Quick PLC Settings Button */}
          <button
            onClick={() => setActiveTab("settings")}
            title="Configure PLC IP and Connection"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "6px",
              border: activeTab === "settings" ? "1px solid var(--primary-cyan)" : "1px solid var(--border-subtle)",
              background: activeTab === "settings" ? "rgba(6, 182, 212, 0.2)" : "rgba(255, 255, 255, 0.06)",
              color: activeTab === "settings" ? "var(--primary-cyan)" : "#fff",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <Settings style={{ width: "14px", height: "14px" }} />
            <span>PLC Settings</span>
          </button>
        </div>
      </header>

      {/* Main Layout Container */}
      <div style={{ display: "flex", flex: 1 }}>
        {/* Navigation Sidebar */}
        <nav
          style={{
            width: "240px",
            borderRight: "1px solid var(--border-subtle)",
            background: "rgba(11, 15, 25, 0.5)",
            padding: "20px 12px",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            flexShrink: 0,
          }}
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: active ? "1px solid var(--border-highlight)" : "1px solid transparent",
                  background: active ? "rgba(6, 182, 212, 0.15)" : "transparent",
                  color: active ? "var(--primary-cyan)" : "var(--text-muted)",
                  fontSize: "13px",
                  fontWeight: active ? 600 : 500,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Icon style={{ width: "16px", height: "16px" }} />
                  <span>{item.label}</span>
                </div>
                {item.badge ? (
                  <span
                    style={{
                      background: "#ef4444",
                      color: "#fff",
                      fontSize: "10px",
                      fontWeight: 700,
                      borderRadius: "10px",
                      padding: "2px 6px",
                    }}
                  >
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        {/* Content Viewport */}
        <main style={{ flex: 1, padding: "28px", maxWidth: "1600px", margin: "0 auto", width: "100%" }}>
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
