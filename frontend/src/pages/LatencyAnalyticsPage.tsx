import React, { useState } from "react";
import { TelemetryMessage, GroupLatencyStats } from "../types";
import { Clock, Play, Square, Download, Activity, AlertCircle, ShieldCheck } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
  renderLatencyMs: number;
}

export const LatencyAnalyticsPage: React.FC<Props> = ({ telemetry, renderLatencyMs }) => {
  const [benchmarkDuration, setBenchmarkDuration] = useState<number>(30);
  const [targetGroup, setTargetGroup] = useState<string>("fast_group");
  const [isRunning, setIsRunning] = useState<boolean>(false);

  if (!telemetry) return null;
  const { latency } = telemetry;
  const groups = latency.groups || {};

  const handleStartBenchmark = async () => {
    try {
      setIsRunning(true);
      await fetch("/api/latency/benchmark/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration_seconds: benchmarkDuration, group_name: targetGroup }),
      });
    } catch (e) {
      console.error(e);
      setIsRunning(false);
    }
  };

  const handleStopBenchmark = async () => {
    try {
      await fetch("/api/latency/benchmark/stop", { method: "POST" });
      setIsRunning(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleExportCsv = () => {
    window.location.href = "/api/latency/benchmark/export";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header and Stage Decomposition Overview */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>
          End-to-End Latency Decomposition Subsystem
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "20px" }}>
          Deconstructs signal delays across the physical acquisition chain, Modbus TCP network, gateway ingestion, and browser DOM rendering.
        </p>

        {/* Latency Pipeline Visualizer */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
          {/* Stage 1: Modbus Round-Trip */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", borderLeft: "4px solid var(--primary-cyan)" }}>
            <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)" }}>Stage 1: Modbus RTT</div>
            <div className="mono" style={{ fontSize: "20px", fontWeight: 700, color: "var(--primary-cyan)", marginTop: "4px" }}>
              {groups.fast_group ? `${groups.fast_group.rtt_p50_ms.toFixed(1)} ms` : "--"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>t_response - t_request</div>
          </div>

          {/* Stage 2: Gateway Ingest */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", borderLeft: "4px solid #34d399" }}>
            <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)" }}>Stage 2: Ingest & Decode</div>
            <div className="mono" style={{ fontSize: "20px", fontWeight: 700, color: "#34d399", marginTop: "4px" }}>
              {groups.fast_group ? `${groups.fast_group.ingest_mean_ms.toFixed(2)} ms` : "--"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>t_ingest - t_response</div>
          </div>

          {/* Stage 3: Server Publish */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", borderLeft: "4px solid #f59e0b" }}>
            <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)" }}>Stage 3: Server Publish</div>
            <div className="mono" style={{ fontSize: "20px", fontWeight: 700, color: "#f59e0b", marginTop: "4px" }}>
              {groups.fast_group ? `${groups.fast_group.publish_mean_ms.toFixed(2)} ms` : "--"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>t_publish - t_ingest</div>
          </div>

          {/* Stage 4: Browser Render */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", borderLeft: "4px solid #a78bfa" }}>
            <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)" }}>Stage 4: Client Render</div>
            <div className="mono" style={{ fontSize: "20px", fontWeight: 700, color: "#a78bfa", marginTop: "4px" }}>
              {renderLatencyMs.toFixed(1)} ms
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>t_render - t_publish</div>
          </div>
        </div>
      </div>

      {/* Latency Percentiles Table */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
          Signal Group Statistical Percentile Distributions
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                <th style={{ padding: "10px 12px" }}>Group</th>
                <th style={{ padding: "10px 12px" }}>Samples</th>
                <th style={{ padding: "10px 12px" }}>Mean</th>
                <th style={{ padding: "10px 12px" }}>P50 (Median)</th>
                <th style={{ padding: "10px 12px" }}>P95</th>
                <th style={{ padding: "10px 12px" }}>P99</th>
                <th style={{ padding: "10px 12px" }}>Min / Max</th>
                <th style={{ padding: "10px 12px" }}>Poll Jitter</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(groups).map(([grpName, stats]) => (
                <tr key={grpName} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: "12px", fontWeight: 600, color: "var(--primary-cyan)" }}>
                    {grpName.toUpperCase()}
                  </td>
                  <td className="mono" style={{ padding: "12px" }}>{stats.count.toLocaleString()}</td>
                  <td className="mono" style={{ padding: "12px" }}>{stats.rtt_mean_ms.toFixed(2)} ms</td>
                  <td className="mono" style={{ padding: "12px", color: "#34d399", fontWeight: 600 }}>{stats.rtt_p50_ms.toFixed(2)} ms</td>
                  <td className="mono" style={{ padding: "12px", color: "#fbbf24" }}>{stats.rtt_p95_ms.toFixed(2)} ms</td>
                  <td className="mono" style={{ padding: "12px", color: "#f87171", fontWeight: 600 }}>{stats.rtt_p99_ms.toFixed(2)} ms</td>
                  <td className="mono" style={{ padding: "12px", color: "var(--text-dim)" }}>
                    {stats.rtt_min_ms.toFixed(1)} / {stats.rtt_max_ms.toFixed(1)} ms
                  </td>
                  <td className="mono" style={{ padding: "12px" }}>± {stats.jitter_ms.toFixed(2)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Latency Benchmark Engine Card */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Controlled Latency Benchmark Suite</h3>
            <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "2px" }}>
              Runs a dedicated profiling session to collect raw timestamp vectors for audit & CSV export.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Duration:</span>
              <select
                value={benchmarkDuration}
                onChange={(e) => setBenchmarkDuration(Number(e.target.value))}
                style={{
                  background: "rgba(0,0,0,0.4)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-main)",
                  borderRadius: "6px",
                  padding: "6px 10px",
                  fontSize: "12px",
                }}
              >
                <option value={15}>15 Seconds</option>
                <option value={30}>30 Seconds</option>
                <option value={60}>60 Seconds</option>
                <option value={120}>120 Seconds</option>
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Target:</span>
              <select
                value={targetGroup}
                onChange={(e) => setTargetGroup(e.target.value)}
                style={{
                  background: "rgba(0,0,0,0.4)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-main)",
                  borderRadius: "6px",
                  padding: "6px 10px",
                  fontSize: "12px",
                }}
              >
                <option value="fast_group">Fast Group (200ms)</option>
                <option value="medium_group">Medium Group (500ms)</option>
                <option value="all">All Groups</option>
              </select>
            </div>

            {latency.benchmark.active ? (
              <button className="btn-danger" onClick={handleStopBenchmark}>
                <Square style={{ width: "14px", height: "14px" }} /> Stop Session
              </button>
            ) : (
              <button className="btn-primary" onClick={handleStartBenchmark}>
                <Play style={{ width: "14px", height: "14px" }} /> Start Benchmark
              </button>
            )}

            <button className="btn-secondary" onClick={handleExportCsv}>
              <Download style={{ width: "14px", height: "14px" }} /> Export CSV
            </button>
          </div>
        </div>

        {latency.benchmark.active && (
          <div style={{ marginTop: "16px", padding: "12px 16px", background: "rgba(6, 182, 212, 0.1)", borderRadius: "8px", border: "1px solid var(--border-highlight)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
              <span>Profiling in progress...</span>
              <span className="mono">
                Samples Collected: <strong>{latency.benchmark.samples_collected}</strong> ({latency.benchmark.elapsed_seconds}s / {latency.benchmark.duration_seconds}s)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Methodological Transparency Note */}
      <div className="glass-panel" style={{ padding: "16px 20px", display: "flex", gap: "12px", alignItems: "flex-start", background: "rgba(18, 24, 38, 0.4)" }}>
        <AlertCircle style={{ width: "18px", height: "18px", color: "var(--primary-cyan)", flexShrink: 0, marginTop: "2px" }} />
        <div style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.5 }}>
          <strong>Timing & Measurement Limitations:</strong> Modbus TCP protocol does not natively transmit PLC-internal hardware sampling timestamps. Unless an explicit sequence timer register is programmed into the Selec MiBRX ladder logic, network RTT represents client-measured socket communication delay. Browser rendering delay is isolated using Web Worker monotonic clocks and requestAnimationFrame paint callbacks.
        </div>
      </div>
    </div>
  );
};
