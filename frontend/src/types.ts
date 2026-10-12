export type QualityFlag = "VALID" | "STALE" | "DISCONNECTED" | "SIMULATED";

export interface SignalData {
  name: string;
  raw_value: number;
  value: number;
  unit: string;
  quality: QualityFlag;
  group: string;
  t_request?: string;
  t_response?: string;
  rtt_ms?: number;
}

export interface GroupLatencyStats {
  count: number;
  rtt_mean_ms: number;
  rtt_p50_ms: number;
  rtt_p95_ms: number;
  rtt_p99_ms: number;
  rtt_min_ms: number;
  rtt_max_ms: number;
  ingest_mean_ms: number;
  ingest_p95_ms: number;
  publish_mean_ms: number;
  update_interval_mean_ms: number;
  jitter_ms: number;
}

export interface LatencyPayload {
  groups: Record<string, GroupLatencyStats>;
  benchmark: {
    active: boolean;
    samples_collected: number;
    duration_seconds: number;
    elapsed_seconds: number;
  };
}

export interface AlarmItem {
  name: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  message: string;
  state: "ACTIVE" | "ACKNOWLEDGED" | "CLEARED";
  triggered_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
}

export interface VibrationPayload {
  rms_g: number;
  peak_g: number;
  peak_to_peak_g: number;
  crest_factor: number;
  dominant_frequency_hz: number;
  warning_alarm: boolean;
  critical_alarm: boolean;
  sample_rate_hz: number;
  interface: string;
  fft_frequencies: number[];
  fft_magnitudes: number[];
  waveform_sample: number[];
}

export interface SystemTelemetry {
  uptime_seconds: number;
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  disk_percent: number;
  cpu_temperature_c?: number | null;
  gateway_time_utc: string;
}

export interface GroupDiagnosticSummary {
  total_polls: number;
  successful_polls: number;
  failed_polls: number;
  consecutive_failures: number;
  error_rate_pct: number;
  last_rtt_ms: number;
  min_rtt_ms: number;
  max_rtt_ms: number;
  avg_rtt_ms: number;
  last_successful_time?: string | null;
  last_error?: string | null;
}

export interface DiagnosticsPayload {
  connected: boolean;
  reconnect_count: number;
  time_since_last_poll_sec?: number | null;
  is_system_stale: boolean;
  groups: Record<string, GroupDiagnosticSummary>;
}

export interface TelemetryMessage {
  type: string;
  timestamp: string;
  machine_state: "RUNNING" | "STOPPED" | "IDLE" | "FAULTED" | "COMM_LOST";
  signals: Record<string, SignalData>;
  latency: LatencyPayload;
  alarms: AlarmItem[];
  vibration: VibrationPayload;
  telemetry: SystemTelemetry;
  diagnostics: DiagnosticsPayload;
  t_publish_mono?: number;
  t_publish_iso?: string;
}

export interface WritableCommandSpec {
  name: string;
  address: number;
  function_code: number;
  description: string;
  min_value?: number | null;
  max_value?: number | null;
  requires_interlock: boolean;
  confirmation_required: boolean;
}

export interface ControlAuditLog {
  id: number;
  timestamp: string;
  operator: string;
  client_ip: string;
  command_name: string;
  target_address: number;
  command_value: number;
  interlocks_verified: boolean;
  status: string;
  readback_verified: boolean;
  readback_value?: number | null;
  details: string;
}
