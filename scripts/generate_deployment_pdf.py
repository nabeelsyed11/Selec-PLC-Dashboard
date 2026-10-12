"""
Generates publication-quality PDF deployment manual for Selec MiBRX-6M PLC
and Raspberry Pi 5 Industrial IoT Gateway.
Includes Full-Folder Copy-Paste Quick Start instructions.
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds running headers and 'Page X of Y' footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages after page 1)
        if self._pageNumber > 1:
            self.drawString(36, 810, "SELEC MiBRX-6M PLC & Raspberry Pi 5 — Deployment & Commissioning Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 804, 559, 804)

        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 42, 559, 42)
        
        self.drawString(36, 30, "Confidential — Industrial IoT Engineering Documentation")
        self.drawRightString(559, 30, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    # Custom typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=10,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#f8fafc"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    badge_style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#166534"),
        alignment=1,
    )

    story = []

    # Title Banner
    story.append(Paragraph("SELEC MiBRX-6M PLC &amp; RASPBERRY PI 5 GATEWAY", title_style))
    story.append(Paragraph("Industrial IoT Monitoring, Latency Measurement, and Control Deployment Manual", subtitle_style))
    
    meta_text = (
        "<b>Target Controller:</b> Selec MiBRX-6M Modbus TCP &nbsp;|&nbsp; "
        "<b>Edge Gateway:</b> Raspberry Pi 5 (64-bit OS) &nbsp;|&nbsp; "
        "<b>Status:</b> Production Ready & Verified"
    )
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 8))

    # 1. System Cross-Check & Verification
    story.append(Paragraph("1. System Cross-Check &amp; Signal Verification", h1_style))
    story.append(Paragraph(
        "All required machine signals, field interfaces, and calculation routines have been verified in the platform codebase:",
        body_style
    ))

    # Cross-Check Table
    table_data = [
        [
            Paragraph("Signal / Equipment", table_header_style),
            Paragraph("Physical Interface / Mapping", table_header_style),
            Paragraph("Implementation in Gateway", table_header_style),
            Paragraph("Status", table_header_style),
        ],
        [
            Paragraph("<b>Selec MiBRX-6M PLC</b>", table_body_style),
            Paragraph("Modbus TCP (Port 502, Slave ID 1)", table_body_style),
            Paragraph("<code>backend/app/plc/modbus_client.py</code>: Async grouped block polling, auto-reconnect, exponential backoff.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Load Cell</b>", table_body_style),
            Paragraph("MiBRX Analog In (0-10V / 4-20mA to Reg 40001)", table_body_style),
            Paragraph("<code>backend/app/sensors/processing.py</code>: Tare zeroing + span calibration: <i>kg = (raw - tare) &times; factor</i>.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Motor Temperature</b>", table_body_style),
            Paragraph("PT100/RTD Module (Reg 40002, 0.1&deg;C/count)", table_body_style),
            Paragraph("<code>backend/app/sensors/processing.py</code>: Warning at 75&deg;C, Critical Alarm at 90&deg;C with 2&deg;C recovery hysteresis.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Belt Slip Sensor</b>", table_body_style),
            Paragraph("Proximity switch (Discrete Input 10001)", table_body_style),
            Paragraph("<code>backend/app/sensors/processing.py</code>: Debounced state + cross-check with VFD reference vs encoder speed.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Rotary Encoder</b>", table_body_style),
            Paragraph("High-Speed Counter (Regs 40003-40004, 32-bit UINT)", table_body_style),
            Paragraph("<code>backend/app/plc/decoder.py</code>: 32-bit rollover aware ($0 \\to 4.29 \\times 10^9$); roller RPM &amp; linear speed (m/s).", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Energy Meter</b>", table_body_style),
            Paragraph("RS-485 Modbus RTU into MiBRX Regs 40011-40022", table_body_style),
            Paragraph("<code>backend/app/plc/decoder.py</code>: 32-bit IEEE-754 floats for Voltage (V), Current (A), kW, PF, and cumulative kWh.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Production Counter</b>", table_body_style),
            Paragraph("Optical sensor pulse (Regs 40006-40007, 32-bit UINT)", table_body_style),
            Paragraph("<code>backend/app/sensors/processing.py</code>: Cumulative parts count, shift tracking, and dynamic rate (parts/min).", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Pusher Actuator</b>", table_body_style),
            Paragraph("Coil 00001 (Command) + Inputs 10002/10003 (Feedback)", table_body_style),
            Paragraph("<code>backend/app/control/service.py</code>: Separates commanded state from feedback; mismatch alarm if timeout > 1.5s.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>VFD Analog &amp; Digital</b>", table_body_style),
            Paragraph("Coil 00002 (Run/Stop), Reg 40031 (SP), Inputs 10004/10005", table_body_style),
            Paragraph("<code>backend/app/control/service.py</code>: Speed setpoint clamp (5-50 Hz), Run/Stop commands, and VFD fault monitoring.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Vibration Sensor</b>", table_body_style),
            Paragraph("Direct Raspberry Pi 5 connection (I2C GPIO 2/3)", table_body_style),
            Paragraph("<code>backend/app/vibration/sensor.py</code>: High-speed sampling (1000 Hz) computing RMS, Peak, Pk-Pk, and 512-pt FFT spectrum.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
        [
            Paragraph("<b>Latency Measurement</b>", table_body_style),
            Paragraph("Monotonic clock on edge + UTC ISO8601", table_body_style),
            Paragraph("<code>backend/app/latency/monitor.py</code>: Separates Modbus RTT, ingestion, publish, and render lag. Computes P50, P95, P99, Jitter.", table_body_style),
            Paragraph("VERIFIED", badge_style),
        ],
    ]

    col_widths = [105, 130, 230, 58]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#dcfce7")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # 2. Can I paste this whole folder in Pi? (NEW SECTION)
    story.append(Paragraph("2. Direct Whole-Folder Transfer to Raspberry Pi 5 (Quick Start)", h1_style))
    story.append(Paragraph(
        "<b>YES! You can copy and paste this whole folder directly onto the Raspberry Pi 5</b> "
        "(via USB flash drive, SCP, SFTP, or FileZilla into <code>/home/pi/Selec-PLC-Dashboard</code> or <code>/opt/selec-iot-dashboard</code>).",
        body_style
    ))

    # Callout Box: 2 Rules
    rule_text = (
        "<b>CRITICAL RULE 1: Do NOT use the Windows <code>venv/</code> folder on the Pi!</b><br/>"
        "The <code>venv/</code> folder created on Windows contains Windows binaries (<code>.exe</code>, <code>.dll</code>). "
        "A Raspberry Pi 5 runs 64-bit Linux ARM64, which cannot execute Windows binaries. "
        "When pasting onto the Pi, simply delete the existing <code>venv/</code> folder and let Python build a fresh Linux ARM64 virtual environment.<br/><br/>"
        "<b>TRANSFER TIP 2: Skip <code>frontend/node_modules/</code> to save time:</b><br/>"
        "Inside <code>frontend/node_modules/</code> there are thousands of tiny files. Because the React website is <b>already pre-compiled into "
        "<code>frontend/dist/</code></b>, you do not need <code>node_modules</code> on the Pi at all! Skipping it makes copying take 5 seconds."
    )
    rule_table = Table([[Paragraph(rule_text, body_style)]], colWidths=[523])
    rule_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93c5fd")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rule_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Exact Commands to Run Immediately After Pasting on the Pi:</b>", h2_style))
    quick_cmds = (
        "# 1. Navigate into the pasted folder on your Raspberry Pi:\n"
        "cd ~/Selec-PLC-Dashboard\n\n"
        "# 2. Remove the Windows virtual environment (if copied) and create fresh Linux ARM64 venv:\n"
        "rm -rf venv\n"
        "python3 -m venv venv\n"
        "./venv/bin/pip install --upgrade pip\n"
        "./venv/bin/pip install -r backend/requirements.txt\n\n"
        "# 3. Configure your PLC IP in .env:\n"
        "nano .env   # Set PLC_HOST=192.168.1.50 and SIMULATION_MODE=false\n\n"
        "# 4. Launch the Gateway & Dashboard immediately:\n"
        "./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend\n\n"
        "# 5. Access the live dashboard on any browser on your network:\n"
        "# 👉 http://<RASPBERRY_PI_IP>:8000"
    )
    quick_table = Table([[Preformatted(quick_cmds, code_style)]], colWidths=[523])
    quick_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#334155")),
    ]))
    story.append(quick_table)
    story.append(Spacer(1, 10))

    # 3. Files to Deploy (Minimal list)
    story.append(Paragraph("3. Directory Layout on the Raspberry Pi 5", h1_style))
    tree_text = (
        "/opt/selec-iot-dashboard/ (or ~/Selec-PLC-Dashboard/)\n"
        "├── backend/                       # Python backend source code\n"
        "│   ├── app/                       # FastAPI, PLC poller, vibration, latency, control\n"
        "│   └── requirements.txt           # Python dependencies (PyModbus, FastAPI, etc.)\n"
        "├── config/\n"
        "│   └── register_map.yaml          # Selec MiBRX-6M register definitions & allowlist\n"
        "├── frontend/\n"
        "│   └── dist/                      # Pre-built React production bundle (HTML, JS, CSS)\n"
        "├── tools/\n"
        "│   ├── modbus_test.py             # Diagnostic tool to test PLC communication\n"
        "│   └── latency_benchmark.py       # Benchmark runner with CSV export\n"
        "├── deploy/\n"
        "│   └── systemd/\n"
        "│       └── selec-iot.service      # systemd service unit for auto-start on boot\n"
        "├── .env                           # Environment configuration\n"
        "└── .env.example"
    )
    tree_table = Table([[Preformatted(tree_text, code_style)]], colWidths=[523])
    tree_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#334155")),
    ]))
    story.append(tree_table)

    story.append(PageBreak())

    # 4. Standard Systemd Production Deployment
    story.append(Paragraph("4. Permanent Background Daemon Setup (systemd)", h1_style))
    story.append(Paragraph("To ensure the dashboard starts automatically upon power-on and survives reboot, install the systemd daemon:", body_style))

    daemon_cmds = (
        "# 1. Create dedicated user and set permissions:\n"
        "sudo useradd -r -s /bin/false -d /opt/selec-iot-dashboard -m iotgateway\n"
        "sudo usermod -aG i2c,spi,dialout iotgateway\n"
        "sudo cp -r ~/Selec-PLC-Dashboard /opt/selec-iot-dashboard\n"
        "sudo chown -R iotgateway:iotgateway /opt/selec-iot-dashboard\n\n"
        "# 2. Install & enable systemd service unit:\n"
        "sudo cp /opt/selec-iot-dashboard/deploy/systemd/selec-iot.service /etc/systemd/system/\n"
        "sudo systemctl daemon-reload\n"
        "sudo systemctl enable --now selec-iot\n\n"
        "# 3. Verify status & view live logs:\n"
        "sudo systemctl status selec-iot\n"
        "sudo journalctl -u selec-iot -f"
    )
    daemon_table = Table([[Preformatted(daemon_cmds, code_style)]], colWidths=[523])
    daemon_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#334155")),
    ]))
    story.append(daemon_table)
    story.append(Spacer(1, 10))

    # 5. Accessing Dashboard
    story.append(Paragraph("5. Dashboard Views Reference (Port 8000)", h1_style))
    story.append(Paragraph("Access the dashboard at <code>http://&lt;RASPBERRY_PI_IP&gt;:8000</code>. It includes 8 dedicated views:", body_style))

    views_data = [
        [
            Paragraph("<b>1. Overview:</b> Real-time machine state (RUNNING, IDLE, FAULTED, COMM_LOST), primary KPIs, PLC link health, and Pi 5 CPU/RAM/Temp.", table_body_style),
            Paragraph("<b>2. Live Monitoring:</b> Per-signal cards with live values, units, quality badges (VALID, STALE, DISCONNECTED, SIMULATED), and RTT.", table_body_style),
        ],
        [
            Paragraph("<b>3. Latency Analytics:</b> Breakdown of Modbus RTT, ingestion delay, publish delay, and client render lag with P50, P95, P99 percentiles and CSV export.", table_body_style),
            Paragraph("<b>4. Vibration Analysis:</b> Real-time oscilloscope waveform, RMS/Peak metrics, and 512-pt FFT frequency spectrum (0-500 Hz).", table_body_style),
        ],
        [
            Paragraph("<b>5. Production:</b> Total counts, shift accumulation, throughput rate (parts/min), and Load Cell Zero Tare calibration action.", table_body_style),
            Paragraph("<b>6. Energy Monitor:</b> 3-phase Voltage, Current, Active Power (kW), Power Factor, and specific energy per unit (kWh/part).", table_body_style),
        ],
        [
            Paragraph("<b>7. Alarms &amp; Events:</b> Active alarms banner, severity indicators (INFO, WARNING, CRITICAL), and operator acknowledgement logging.", table_body_style),
            Paragraph("<b>8. Safe Control Panel:</b> Interlock permissive verification, allowlisted commands (Pusher, VFD), confirmation modal, and immutable audit trail.", table_body_style),
        ],
    ]

    v_table = Table(views_data, colWidths=[260, 260])
    v_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(v_table)
    story.append(Spacer(1, 14))

    # Sign-off box
    signoff_data = [
        [
            Paragraph("<b>Commissioned By:</b> ___________________________", table_body_style),
            Paragraph("<b>Date:</b> ______________", table_body_style),
            Paragraph("<b>Signature:</b> ___________________________", table_body_style),
        ]
    ]
    signoff_table = Table(signoff_data, colWidths=[200, 120, 203])
    signoff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([signoff_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated updated PDF: {output_path}")


if __name__ == "__main__":
    out_file = str(Path(__file__).resolve().parent.parent / "docs" / "Selec_MiBRX_PLC_Raspberry_Pi_5_Deployment_Guide.pdf")
    generate_pdf(out_file)
