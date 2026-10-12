"""
Vibration Signal Analysis: Time-Domain Metrics and FFT Spectrum Extraction.
Calculates RMS, Peak, Peak-to-Peak, Crest Factor, and frequency domain spectrum.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import numpy as np


@dataclass
class VibrationMetrics:
    rms_g: float
    peak_g: float
    peak_to_peak_g: float
    crest_factor: float
    dominant_frequency_hz: float
    warning_alarm: bool
    critical_alarm: bool
    sample_rate_hz: int
    fft_frequencies: List[float]
    fft_magnitudes: List[float]
    waveform_sample: List[float]


def analyze_vibration_window(
    samples: np.ndarray,
    sample_rate_hz: int,
    warning_limit_rms: float = 1.8,
    critical_limit_rms: float = 3.5,
    max_fft_bins: int = 64,
) -> VibrationMetrics:
    """
    Analyzes an array of acceleration samples (in g units).
    """
    N = len(samples)
    if N < 16:
        return VibrationMetrics(
            rms_g=0.0,
            peak_g=0.0,
            peak_to_peak_g=0.0,
            crest_factor=0.0,
            dominant_frequency_hz=0.0,
            warning_alarm=False,
            critical_alarm=False,
            sample_rate_hz=sample_rate_hz,
            fft_frequencies=[],
            fft_magnitudes=[],
            waveform_sample=[],
        )

    # Remove DC bias (gravity offset / static tilt)
    dc_offset = np.mean(samples)
    detrended = samples - dc_offset

    # Time-domain metrics
    rms = float(np.sqrt(np.mean(detrended ** 2)))
    peak = float(np.max(np.abs(detrended)))
    pk_to_pk = float(np.max(detrended) - np.min(detrended))
    crest_factor = float(peak / rms) if rms > 0.001 else 0.0

    # Frequency-domain (FFT)
    # Apply Hanning window to reduce spectral leakage
    window = np.hanning(N)
    windowed_signal = detrended * window

    # Real FFT
    rfft_vals = np.fft.rfft(windowed_signal)
    magnitudes = np.abs(rfft_vals) * (2.0 / N)
    freqs = np.fft.rfftfreq(N, d=1.0 / sample_rate_hz)

    # Find dominant frequency peak (exclude DC bin at index 0)
    if len(magnitudes) > 1:
        dom_idx = int(np.argmax(magnitudes[1:])) + 1
        dominant_freq = float(freqs[dom_idx])
    else:
        dominant_freq = 0.0

    # Subsample FFT spectrum for lightweight JSON broadcast
    step = max(1, len(freqs) // max_fft_bins)
    sampled_freqs = [round(float(f), 1) for f in freqs[::step][:max_fft_bins]]
    sampled_mags = [round(float(m), 4) for m in magnitudes[::step][:max_fft_bins]]

    # Downsample raw waveform to 128 points for visual scope display
    scope_step = max(1, N // 128)
    waveform_display = [round(float(s), 3) for s in detrended[::scope_step][:128]]

    return VibrationMetrics(
        rms_g=round(rms, 3),
        peak_g=round(peak, 3),
        peak_to_peak_g=round(pk_to_pk, 3),
        crest_factor=round(crest_factor, 2),
        dominant_frequency_hz=round(dominant_freq, 1),
        warning_alarm=rms >= warning_limit_rms,
        critical_alarm=rms >= critical_limit_rms,
        sample_rate_hz=sample_rate_hz,
        fft_frequencies=sampled_freqs,
        fft_magnitudes=sampled_mags,
        waveform_sample=waveform_display,
    )
