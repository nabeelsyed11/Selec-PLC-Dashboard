import React, { useRef, useEffect } from "react";
import { TelemetryMessage } from "../types";
import { Activity, Radio, AlertTriangle, ShieldCheck, BarChart2 } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const VibrationPage: React.FC<Props> = ({ telemetry }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const vibration = telemetry?.vibration;

  // Draw waveform on HTML5 Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !vibration || !vibration.waveform_sample) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const samples = vibration.waveform_sample;

    ctx.clearRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Zero line
    ctx.strokeStyle = "rgba(6, 182, 212, 0.3)";
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    // Waveform trace
    ctx.strokeStyle = "#06b6d4";
    ctx.lineWidth = 2;
    ctx.beginPath();

    const maxAmplitude = 3.0; // +/- 3g vertical scale
    const stepX = width / (samples.length - 1 || 1);

    samples.forEach((val, i) => {
      const x = i * stepX;
      const normalizedY = height / 2 - (val / maxAmplitude) * (height / 2);
      if (i === 0) {
        ctx.moveTo(x, normalizedY);
      } else {
        ctx.lineTo(x, normalizedY);
      }
    });

    ctx.stroke();
  }, [vibration]);

  if (!vibration) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Header Card */}
      <div className="glass-panel" style={{ padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Direct Vibration Acquisition & FFT Analysis</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
            Acquired directly via Raspberry Pi 5 interface ({vibration.interface}) at {vibration.sample_rate_hz} Hz
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Health:</span>
          {!telemetry.simulation_mode && vibration.interface === "NO_HARDWARE_DETECTED" ? (
            <span className="badge-quality-disconnected" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600 }}>
              NO SENSOR ATTACHED
            </span>
          ) : vibration.critical_alarm ? (
            <span className="badge-quality-disconnected" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600 }}>
              CRITICAL VIBRATION
            </span>
          ) : vibration.warning_alarm ? (
            <span className="badge-quality-stale" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600 }}>
              WARNING THRESHOLD
            </span>
          ) : (
            <span className="badge-quality-valid" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600 }}>
              NORMAL BEARING BEHAVIOR
            </span>
          )}
        </div>
      </div>

      {/* Disconnection Warning */}
      {!telemetry.simulation_mode && vibration.interface === "NO_HARDWARE_DETECTED" && (
        <div
          style={{
            padding: "14px 18px",
            borderRadius: "8px",
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.35)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <AlertTriangle style={{ width: "20px", height: "20px", color: "#f87171", flexShrink: 0 }} />
          <div style={{ fontSize: "13px" }}>
            <span style={{ fontWeight: 700, color: "#f87171" }}>Physical Mode Active:</span>{" "}
            No physical I2C accelerometer (ADXL345/MPU6050) was detected on Raspberry Pi GPIO pins 2 & 3. Simulated waveforms are disabled so no false vibration is displayed. Connect a sensor to Pi GPIO or turn Simulation ON in <strong>PLC Settings</strong> to test.
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>RMS Acceleration</div>
          <div className="mono" style={{ fontSize: "28px", fontWeight: 700, color: vibration.warning_alarm ? "#ef4444" : "var(--primary-cyan)", marginTop: "4px" }}>
            {vibration.rms_g.toFixed(2)} <span style={{ fontSize: "16px", fontWeight: 400 }}>g</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Warn: 1.8g / Crit: 3.5g</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Peak Acceleration</div>
          <div className="mono" style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px" }}>
            {vibration.peak_g.toFixed(2)} <span style={{ fontSize: "16px", fontWeight: 400 }}>g</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Max instantaneous pulse</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Peak-to-Peak</div>
          <div className="mono" style={{ fontSize: "28px", fontWeight: 700, marginTop: "4px" }}>
            {vibration.peak_to_peak_g.toFixed(2)} <span style={{ fontSize: "16px", fontWeight: 400 }}>g</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Full dynamic excursion</div>
        </div>

        <div className="glass-panel" style={{ padding: "18px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Dominant Frequency</div>
          <div className="mono" style={{ fontSize: "28px", fontWeight: 700, color: "#34d399", marginTop: "4px" }}>
            {vibration.dominant_frequency_hz.toFixed(1)} <span style={{ fontSize: "16px", fontWeight: 400 }}>Hz</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>Crest Factor: {vibration.crest_factor.toFixed(2)}</div>
        </div>
      </div>

      {/* Real-time Oscilloscope Waveform Display */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Real-time Time-Domain Acceleration Waveform (Scope)</h3>
          <span className="mono" style={{ fontSize: "12px", color: "var(--text-muted)" }}>Scale: ± 3.0 g</span>
        </div>
        <div style={{ width: "100%", height: "180px", background: "rgba(0,0,0,0.4)", borderRadius: "8px", overflow: "hidden" }}>
          <canvas ref={canvasRef} width={800} height={180} style={{ width: "100%", height: "100%" }} />
        </div>
      </div>

      {/* FFT Frequency Spectrum Bins */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <BarChart2 style={{ width: "18px", height: "18px", color: "var(--primary-cyan)" }} />
          FFT Spectral Magnitude Distribution (0 - 500 Hz)
        </h3>
        <div style={{ display: "flex", alignItems: "flex-end", height: "160px", gap: "4px", background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "8px" }}>
          {vibration.fft_magnitudes?.slice(0, 48).map((mag, idx) => {
            const freq = vibration.fft_frequencies?.[idx] || 0;
            const barHeight = Math.min(100, (mag / 1.5) * 100);
            return (
              <div
                key={idx}
                title={`${freq.toFixed(1)} Hz: ${mag.toFixed(3)}g`}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  height: "100%",
                  justifyContent: "flex-end",
                }}
              >
                <div
                  style={{
                    width: "100%",
                    height: `${Math.max(4, barHeight)}%`,
                    backgroundColor: freq === vibration.dominant_frequency_hz ? "#34d399" : "var(--primary-cyan)",
                    borderRadius: "2px 2px 0 0",
                    transition: "height 0.15s ease",
                  }}
                />
              </div>
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-dim)", marginTop: "8px" }}>
          <span>0 Hz (DC)</span>
          <span>125 Hz</span>
          <span>250 Hz (Nyquist Mid)</span>
          <span>500 Hz</span>
        </div>
      </div>
    </div>
  );
};
