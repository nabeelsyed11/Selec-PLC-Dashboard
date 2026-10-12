# COMMISSIONING_CHECKLIST.md — Field Engineering & Commissioning Sign-Off

> **Equipment**: Selec MiBRX-6M PLC, Raspberry Pi 5 Gateway, Industrial Load Cell, Conveyor Drive, Vibration Sensor
> **Project**: Industrial IoT Monitoring, Latency Measurement, and Control Dashboard

---

## Pre-Power Checks

- [ ] **Wiring & Power Separation**: 24V DC logic power supply is separate from high-voltage AC mains and VFD motor cables.
- [ ] **Shielding & Grounding**: RS-485 cable shields and load cell cable shields grounded at a single earth point to avoid ground loops.
- [ ] **Vibration Sensor Wiring on Pi 5**: Accelerometer is connected to Pi 5 3.3V power, GND, SDA (GPIO 2), and SCL (GPIO 3). **CONFIRMED: No analog voltage > 3.3V is connected to Raspberry Pi GPIOs.**
- [ ] **Emergency Stop Hardware**: E-Stop pushbuttons and safety gate limit switches are wired directly into hardwired safety relays or dedicated safety inputs on the PLC.

---

## Network & Communication Verification

- [ ] **Ethernet Subnet**: Raspberry Pi 5 and Selec MiBRX-6M PLC are assigned static IP addresses on the same subnet (e.g. PLC: `192.168.1.50`, Pi: `192.168.1.100`, Subnet: `255.255.255.0`).
- [ ] **Ping Verification**: `ping 192.168.1.50` responds with RTT < 2.0 ms on wired switch.
- [ ] **Modbus Port Open**: `nc -zv 192.168.1.50 502` confirms port 502 is listening.
- [ ] **Safe Read-Only Discovery**: Run `python tools/modbus_test.py --host 192.168.1.50 --port 502` and confirm responses for Discrete Inputs and Holding Registers without Modbus exception errors.

---

## Sensor Calibration & Scaling Checks

- [ ] **Load Cell Tare**: Run `/api/production/tare-loadcell` with empty platform. Confirm weight reads `0.0 kg`.
- [ ] **Load Cell Calibration Mass**: Place certified test mass (e.g. 20.0 kg). Confirm reading matches within ±0.1 kg.
- [ ] **Motor Temperature**: Confirm ambient temperature reading (~20 - 30 °C). Verify high-temperature alarm trips in software when threshold set below current value.
- [ ] **Conveyor Belt Slip**: Induce slip or stop belt manually; confirm `BELT_SLIP` alarm is raised in dashboard within 1.0 second.
- [ ] **High-Speed Encoder Counter**: Rotate conveyor roller manually; confirm pulse count increments and does not drop counts. Verify rollover handling across boundary.
- [ ] **Production Counter**: Pass item across optical part sensor; confirm pulse increments production count by 1 and rate updates.
- [ ] **Vibration FFT**: Inspect FFT spectrum; confirm motor rotational speed harmonic (e.g. 25 - 50 Hz) is clearly visible and RMS reads within expected baseline (<1.0g).

---

## Safety & Control Handshake Verification

- [ ] **Disabled by Default**: Verify that control writes return HTTP 403 Forbidden when `ALLOW_REMOTE_CONTROL=false`.
- [ ] **Allowlist Enforcement**: Verify that attempts to write registers not in `config/register_map.yaml` are immediately blocked.
- [ ] **Interlock Enforcement**: Open safety guard door or trip E-Stop; attempt to issue VFD run command; confirm backend rejects command with `INTERLOCK_REJECTED`.
- [ ] **Readback & Feedback Verification**: Issue Pusher Extend command; confirm readback verified from PLC output coil AND extended reed switch feedback sensor verified within 1.5 seconds.
- [ ] **Audit Trail**: Confirm all executed commands are recorded in the `control_audit_logs` table with timestamp, operator ID, and IP address.

---

## Performance & Latency Sign-Off

- [ ] **Modbus TCP Round-Trip (P50)**: < 15 ms on dedicated industrial LAN.
- [ ] **Ingestion Overhead**: < 2 ms on Raspberry Pi 5.
- [ ] **UI Rendering Delay**: < 16 ms (within 60 FPS frame window).
- [ ] **Benchmark Export**: Run `tools/latency_benchmark.py` and inspect exported CSV for distribution anomalies.

---

**Commissioning Engineer**: __________________________  
**Signature**: _______________________________________  
**Date**: ____________________________________________
