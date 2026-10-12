"""
Unit tests for Vibration Analysis (RMS, Peak, Peak-to-Peak, and FFT Spectrum).
"""
import pytest
import numpy as np
from app.vibration.analysis import analyze_vibration_window


def test_vibration_pure_sine():
    # 50 Hz sine wave with amplitude 2.0g sampled at 1000 Hz
    fs = 1000
    N = 1000
    t = np.arange(N) / fs
    f0 = 50.0
    signal = 2.0 * np.sin(2 * np.pi * f0 * t)

    metrics = analyze_vibration_window(
        samples=signal,
        sample_rate_hz=fs,
        warning_limit_rms=1.8,
        critical_limit_rms=3.5
    )

    # Theoretical RMS of sine with amplitude A is A / sqrt(2) = 2.0 / 1.414 = 1.414g
    assert pytest.approx(metrics.rms_g, 0.05) == 1.414
    # Peak should be ~2.0g
    assert pytest.approx(metrics.peak_g, 0.05) == 2.0
    # Peak-to-Peak should be ~4.0g
    assert pytest.approx(metrics.peak_to_peak_g, 0.1) == 4.0
    # Dominant frequency should be 50.0 Hz
    assert pytest.approx(metrics.dominant_frequency_hz, 1.0) == 50.0
    # RMS (1.414) is below warning limit (1.8)
    assert not metrics.warning_alarm
    assert not metrics.critical_alarm


def test_vibration_alarm_thresholds():
    fs = 1000
    N = 500
    # High amplitude signal: RMS will exceed 3.5g
    signal = 6.0 * np.sin(2 * np.pi * 30.0 * (np.arange(N) / fs))

    metrics = analyze_vibration_window(
        samples=signal,
        sample_rate_hz=fs,
        warning_limit_rms=1.8,
        critical_limit_rms=3.5
    )

    assert metrics.warning_alarm
    assert metrics.critical_alarm
