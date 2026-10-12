# HARDWARE_CHECKLIST.md — Physical Hardware Verification & Commissioning Checklist

> **Target Controller**: Selec MiBRX-6M Micro-PLC
> **Target Edge Device**: Raspberry Pi 5 (4GB / 8GB)
> **Direct Sensor**: Vibration Accelerometer

---

## 1. Information Requiring Verification Against Physical Hardware Manuals

Before running against the physical PLC, verify the following against the **Selec MiBRX-6M Hardware & Communication Manual**:

| Item # | Parameter | Default / Hypothesis in this Project | Items to Verify from Manufacturer Manual / Ladder Program |
|---|---|---|---|
| **HW-01** | PLC Modbus Node ID / Slave ID | `1` | Confirm Slave ID set in Selec MiBRX Ladder configuration (commonly 1, 2, or 255). |
| **HW-02** | Modbus TCP Port | `502` | Verify whether the Ethernet module on the MiBRX-6M uses standard port 502 or a custom port. |
| **HW-03** | PLC IP Address & Subnet | `192.168.1.50 / 255.255.255.0` | Verify static IP configured on PLC. Pi 5 must be on matching subnet (e.g. `192.168.1.100`). |
| **HW-04** | Register Addressing Base | 0-based vs 1-based (Holding Reg 40001 = offset 0 vs 1) | Verify if Selec Ladder Software addresses register `40001` as Modbus offset `0` or offset `1`. PyModbus defaults to 0-based offset. |
| **HW-05** | Word & Byte Endianness | Big-Endian (ABCD) with Word-Swap (CDAB) option | For 32-bit values (Encoder, Energy Meter, Floats), verify word order (High Word First vs Low Word First). |
| **HW-06** | Load Cell Input Range | 0 - 4000 raw counts for 0 - 500 kg | Confirm whether load cell amplifier connects to MiBRX analog input module (0-10V or 4-20mA, 12-bit = 0-4095 or 14-bit). |
| **HW-07** | Motor Temperature Sensor | PT100 / RTD input module, 0.1 °C per count | Verify temperature input module type and raw integer scaling (e.g., 253 = 25.3 °C). |
| **HW-08** | Belt Slip Sensor | Proximity switch into Digital Input | Verify NPN vs PNP polarity, pull-up/pull-down, and whether PLC debounces input in ladder. |
| **HW-09** | High-Speed Counter (Encoder) | 32-bit register at address 40005 | Verify High-Speed Counter (HSC) configuration in MiBRX ladder: pulse mode, quadrature, max frequency. |
| **HW-10** | RS-485 Energy Meter Gateway | Mapped to Holding Registers 40010 - 40025 | Confirm whether the MiBRX-6M acts as a Modbus Master to poll the RS-485 energy meter and store values into internal holding registers. |
| **HW-11** | Pusher Actuator Output | Digital Output Coil 00001 (DO 1) | Confirm PLC output relay/transistor address and interlock conditions. |
| **HW-12** | Pusher Limit Switch Feedback | Digital Input 10001 (DI 1) | Confirm limit switch wiring, normally open (NO) vs normally closed (NC). |
| **HW-13** | VFD Analog Reference | Analog Output 40004 (AO 1, 0-1000 = 0-50Hz) | Confirm DAC scaling in PLC ladder (e.g. 0-4095 or 0-1000). |
| **HW-14** | VFD Digital Run / Fault | DO 2 (Run command) / DI 2 (VFD Fault) | Confirm polarity and safety contactor wiring. |
| **HW-15** | Vibration Sensor on Pi 5 | Direct I2C (ADXL345 / MPU6050) or SPI or ADC (ADS1115) | **NEVER connect analog signal directly to Pi 5 GPIO** (Pi 5 GPIO is strictly 3.3V digital). Use an external ADC (ADS1115 / MCP3008) for analog accelerometer, or a digital I2C/SPI accelerometer. |

---

## 2. Physical Commissioning Verification Steps

1. **Step 1: Network Ping & Port Scan**
   ```bash
   ping 192.168.1.50
   nc -zv 192.168.1.50 502
   ```
2. **Step 2: Read-Only Modbus Communication Test**
   Run the project's safe test tool:
   ```bash
   python tools/modbus_test.py --host 192.168.1.50 --port 502 --unit 1
   ```
3. **Step 3: Vibration Sensor Hardware Check**
   For I2C sensors on Raspberry Pi 5:
   ```bash
   i2cdetect -y 1
   # Confirm device responds at 0x53 (ADXL345) or 0x68 (MPU6050) or 0x48 (ADS1115)
   ```
4. **Step 4: Safe Control Verification**
   Verify that all remote control writes remain strictly disabled until explicit interlocks and ladder logic are verified.
