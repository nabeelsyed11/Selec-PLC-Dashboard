# TROUBLESHOOTING.md — Industrial Field Diagnostics Playbook

> Diagnostic guide for common Modbus TCP exceptions, high latency spikes, sensor errors, and interlock faults.

---

## 1. Modbus Communication Failures

### Symptom: Dashboard shows `COMM_LOST` or `Connection refused`
1. **Network ping**:
   ```bash
   ping 192.168.1.50
   ```
   If no response: Check physical RJ-45 cable, link LEDs on PLC Ethernet module and Pi 5, and subnet mask (`255.255.255.0`).
2. **Port connectivity**:
   ```bash
   nc -zv 192.168.1.50 502
   ```
   If port is closed: Verify that the Modbus TCP server task in Selec MiBRX Ladder software is set to RUN mode and not stopped.
3. **Unit ID / Slave ID mismatch**:
   By default, Selec MiBRX-6M uses Slave ID `1`. If configured as `2` or `255`, update `PLC_UNIT_ID` in `.env` and `config/register_map.yaml`.

---

## 2. Modbus Exception Responses (Illegal Data Address / Value)

### Symptom: `Modbus error reading holding registers: 0x83 (Exception Code 02)`
- **Exception 02 (Illegal Data Address)**: The requested register address does not exist in the PLC memory map, or the number of registers requested exceeds the declared block size.
- **Root Cause & Fix**:
  - Check whether the Selec MiBRX-6M ladder addresses registers starting from `0` or `1`. (e.g. 40001 = offset `0` vs offset `1`).
  - In `config/register_map.yaml`, reduce `count` or split contiguous reads into smaller blocks.

---

## 3. High Latency or Jitter Spikes

### Symptom: RTT exceeds 50 ms or Jitter > 20 ms
1. **Network traffic**: Ensure the PLC and Raspberry Pi 5 are connected via an unmanaged industrial switch or direct cross-over cable, not shared with heavy enterprise Wi-Fi or office streaming traffic.
2. **Polling cycle overlap**: Verify that `fast_group` interval (`200 ms`) is not shorter than the sum of all block read round-trip times. Increase interval to `250 ms` if PLC processor scan time is slow.
3. **CPU throttling on Pi 5**: Run `vcgencmd get_throttled` to ensure power supply is delivering 5V/5A and not causing CPU undervoltage throttling.

---

## 4. Stale Data Warning (`STALE` quality flag)

### Symptom: Signals marked as `STALE` (Yellow badge)
- **Explanation**: The time elapsed since the last successful response exceeds `max_data_age_seconds` (default: 3.0 seconds).
- **Remedy**:
  - Inspect journalctl: `sudo journalctl -u selec-iot -n 50 --no-pager`
  - Look for socket read timeout warnings or repeated reconnection attempts.

---

## 5. Vibration Sensor I2C Failures on Pi 5

### Symptom: `Vibration acquisition fallback to mock driver`
1. **Verify I2C bus is enabled in Pi OS**:
   ```bash
   sudo raspi-config nonint do_i2c 0
   ```
2. **Check device detection**:
   ```bash
   sudo i2cdetect -y 1
   ```
   Confirm device address `0x53` (ADXL345) or `0x68` (MPU6050) appears on the bus. If showing `--`, check pull-up resistors (4.7kΩ on SDA/SCL) and 3.3V power rails.

---

## 6. Remote Control Command Rejected

### Symptom: HTTP 403 Forbidden: `Remote control is disabled by default`
- **Explanation**: System safety default.
- **To Enable**:
  1. Open `.env`
  2. Set `ALLOW_REMOTE_CONTROL=true`
  3. Restart service: `sudo systemctl restart selec-iot`

### Symptom: HTTP 400 Bad Request: `Machine safety interlock permissive not satisfied`
- Verify that E-Stop circuit is healthy (`emergency_stop_ok == 1`), safety guard door is closed (`safety_guard_closed == 1`), and VFD has no active faults.
