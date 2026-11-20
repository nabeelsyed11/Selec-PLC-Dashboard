#!/usr/bin/env python3
"""
Diagnostic & Calibration Tool for SW-420 / 801S Digital Vibration Sensor
Directly tests Raspberry Pi GPIO 17 (Physical Header Pin 11).

Wiring Check:
  * VCC -> Physical Pin 1 (3.3V Power)
  * GND -> Physical Pin 6 (Ground)
  * D0  -> Physical Pin 11 (GPIO 17)
"""
import sys
import time
import subprocess
from pathlib import Path

PIN = 17

print("\n" + "=" * 60)
print("     Raspberry Pi Vibration Sensor Diagnostic & Live Test    ")
print("=" * 60)
print(f"Testing GPIO: BCM {PIN} (Physical Header Pin 11)")
print("Wiring Check:")
print("  * Sensor VCC -> Physical Pin 1 (3.3V)")
print("  * Sensor GND -> Physical Pin 6 (Ground)")
print("  * Sensor D0  -> Physical Pin 11 (GPIO 17)")
print("=" * 60 + "\n")

# Detect available backend
read_fn = None
backend_name = "Unknown"

# 1. Try gpiozero
try:
    from gpiozero import DigitalInputDevice
    dev = DigitalInputDevice(PIN, pull_up=False)
    read_fn = lambda: 1 if dev.is_active else 0
    backend_name = "gpiozero"
except Exception:
    pass

# 2. Try RPi.GPIO
if not read_fn:
    try:
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        read_fn = lambda: GPIO.input(PIN)
        backend_name = "RPi.GPIO"
    except Exception:
        pass

# 3. Try gpiod
if not read_fn:
    try:
        import gpiod
        chip_path = "/dev/gpiochip4" if Path("/dev/gpiochip4").exists() else "/dev/gpiochip0"
        if hasattr(gpiod, "request_lines"):
            req = gpiod.request_lines(
                chip_path,
                consumer="vibration_diag",
                config={PIN: gpiod.LineSettings(direction=gpiod.line.Direction.INPUT)}
            )
            read_fn = lambda: req.get_value(PIN)
        else:
            chip = gpiod.Chip("gpiochip4" if Path("/dev/gpiochip4").exists() else "gpiochip0")
            line = chip.get_line(PIN)
            line.request(consumer="vibration_diag", type=gpiod.LINE_REQ_DIR_IN)
            read_fn = lambda: line.get_value()
        backend_name = "libgpiod"
    except Exception:
        pass

# 4. Try pinctrl (Raspberry Pi 5 / Bookworm / Trixie native tool)
if not read_fn:
    try:
        res = subprocess.run(["pinctrl", "get", str(PIN)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            def pinctrl_read():
                try:
                    out = subprocess.check_output(["pinctrl", "get", str(PIN)], text=True)
                    return 1 if "hi" in out.lower() else 0
                except Exception:
                    return 0
            read_fn = pinctrl_read
            backend_name = "pinctrl CLI (Pi native)"
    except Exception:
        pass

# 5. Try raspi-gpio (Raspberry Pi 4 native tool)
if not read_fn:
    try:
        res = subprocess.run(["raspi-gpio", "get", str(PIN)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            def raspi_gpio_read():
                try:
                    out = subprocess.check_output(["raspi-gpio", "get", str(PIN)], text=True)
                    return 1 if "level=1" in out.lower() or "hi" in out.lower() else 0
                except Exception:
                    return 0
            read_fn = raspi_gpio_read
            backend_name = "raspi-gpio CLI (Pi native)"
    except Exception:
        pass

if not read_fn:
    print("[ERROR] Could not initialize any GPIO driver (gpiozero, RPi.GPIO, gpiod, or pinctrl).")
    print("Please install gpiozero with: sudo apt install -y python3-gpiozero")
    sys.exit(1)

print(f"[OK] Connected via: {backend_name}")
print("\n>>> LIVE MONITORING STARTED (Press Ctrl+C to stop) <<<")
print(">>> GENTLY TAP OR VIBRATE THE SENSOR NOW! <<<\n")

initial_val = read_fn()
print(f"Current Baseline Level: {initial_val} ({'HIGH' if initial_val else 'LOW'})\n")

last_val = initial_val
trigger_count = 0
start_time = time.time()

try:
    while True:
        val = read_fn()
        if val != last_val:
            trigger_count += 1
            last_val = val
            print(f"[{time.strftime('%H:%M:%S')}] *** VIBRATION DETECTED! *** Pin changed to: {val} (Total pulses: {trigger_count})")
        time.sleep(0.02)  # 50 Hz poll rate
except KeyboardInterrupt:
    print("\n\n" + "=" * 60)
    print(f"Test completed. Total vibration triggers detected: {trigger_count}")
    if trigger_count == 0:
        print("\n[TROUBLESHOOTING TIP]:")
        print("  Zero triggers were registered.")
        print("  1. Verify the wires are firmly plugged into Pin 1 (3V3), Pin 6 (GND), and Pin 11 (D0).")
        print("  2. Turn the small blue potentiometer screw on the sensor module with a small screwdriver.")
        print("     Adjust it until the sensor's D0 indicator LED blinks when you tap the sensor.")
    else:
        print("\n[SUCCESS]: Physical sensor is working and sending live pulses to Pin 11!")
    print("=" * 60 + "\n")
