#!/usr/bin/env python3
"""
Generates the comprehensive Industrial IoT Integration Word Document (.docx)
with 4 embedded visual flowcharts, architecture diagrams, register tables,
and copy-paste commands for the Selec MiBRX-6M PLC and Raspberry Pi Gateway.
"""
import os
from pathlib import Path
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = DOCS_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

FLOWCHART_1_PATH = IMAGES_DIR / "flowchart_architecture.png"
FLOWCHART_2_PATH = IMAGES_DIR / "flowchart_telemetry_pipeline.png"
FLOWCHART_3_PATH = IMAGES_DIR / "flowchart_commissioning.png"
FLOWCHART_4_PATH = IMAGES_DIR / "flowchart_dashboards_nodered.png"

OUTPUT_DOCX_PATH = DOCS_DIR / "Selec_PLC_IoT_Integration_Guide.docx"
ROOT_DOCX_PATH = ROOT_DIR / "Selec_PLC_IoT_Integration_Guide.docx"


def set_cell_shading(cell, color_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = OxmlElement('w:tcMar')
    for margin_name, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{margin_name}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tc_mar.append(node)
    tc_pr.append(tc_mar)


# Flowchart 1: Architecture
def generate_architecture_flowchart():
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    c_plc = "#E0F2FE"
    c_plc_b = "#0284C7"
    c_pi = "#DCFCE7"
    c_pi_b = "#16A34A"
    c_ui = "#FEF3C7"
    c_ui_b = "#D97706"

    # PLC
    rect_plc = patches.FancyBboxPatch((4, 25), 24, 52, boxstyle="round,pad=1", facecolor=c_plc, edgecolor=c_plc_b, linewidth=2)
    ax.add_patch(rect_plc)
    ax.text(16, 72, "Selec MiBRX-6M PLC", ha="center", va="center", fontsize=12, fontweight="bold", color="#0369A1")
    ax.text(16, 66, "IP: 192.168.1.50\nPort: 502 (Slave ID: 1)", ha="center", va="center", fontsize=9, color="#075985")
    ax.text(16, 51, "Physical I/O Points:\n- Inputs: I0..I7 (FC 02)\n- Analog: IW0 (Reg 40768)\n- Coils: Q0..Q7 (FC 01)", ha="center", va="center", fontsize=8.5, color="#1E293B", bbox=dict(boxstyle="square,pad=0.5", facecolor="#FFFFFF", edgecolor="#BAE6FD"))
    ax.text(16, 31, "[Modbus TCP Server Task: RUN]", ha="center", va="center", fontsize=8, fontweight="bold", color="#0284C7")

    # Ethernet Link
    ax.annotate("", xy=(38, 51), xytext=(28, 51), arrowprops=dict(arrowstyle="<->", color="#2563EB", lw=3))
    ax.text(33, 56, "Ethernet (RJ45)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1D4ED8")
    ax.text(33, 46, "Subnet: /24\nRTT: 5.5 ms", ha="center", va="center", fontsize=7.5, color="#475569")

    # Gateway
    rect_pi = patches.FancyBboxPatch((38, 15), 32, 72, boxstyle="round,pad=1", facecolor=c_pi, edgecolor=c_pi_b, linewidth=2)
    ax.add_patch(rect_pi)
    ax.text(54, 82, "Raspberry Pi 4B Gateway", ha="center", va="center", fontsize=12, fontweight="bold", color="#15803D")
    ax.text(54, 76, "eth0: 192.168.1.100 (Direct PLC Subnet)\nwlan0: 192.168.31.x (Local Wi-Fi Network)", ha="center", va="center", fontsize=8, color="#166534")

    p1 = patches.FancyBboxPatch((41, 57), 26, 14, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#86EFAC", linewidth=1.5)
    ax.add_patch(p1)
    ax.text(54, 65, "Async Modbus Engine", ha="center", va="center", fontsize=9, fontweight="bold", color="#166534")
    ax.text(54, 60, "PyModbus (call_modbus wrapper)\nAdaptive Reconnect & Fallbacks", ha="center", va="center", fontsize=7.5, color="#334155")

    p2 = patches.FancyBboxPatch((41, 38), 26, 14, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#86EFAC", linewidth=1.5)
    ax.add_patch(p2)
    ax.text(54, 46, "Real-Time Telemetry State", ha="center", va="center", fontsize=9, fontweight="bold", color="#166534")
    ax.text(54, 41, "IW0 (Int16 = 50) + DI Bits\n50-Point Rolling Buffer", ha="center", va="center", fontsize=7.5, color="#334155")

    p3 = patches.FancyBboxPatch((41, 19), 26, 14, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#86EFAC", linewidth=1.5)
    ax.add_patch(p3)
    ax.text(54, 27, "FastAPI & Uvicorn Engine", ha="center", va="center", fontsize=9, fontweight="bold", color="#166534")
    ax.text(54, 22, "WebSocket /ws (10 Hz Live Broadcast)\nREST API Endpoints", ha="center", va="center", fontsize=7.5, color="#334155")

    ax.annotate("", xy=(54, 57), xytext=(54, 52), arrowprops=dict(arrowstyle="->", color="#16A34A", lw=2))
    ax.annotate("", xy=(54, 38), xytext=(54, 33), arrowprops=dict(arrowstyle="->", color="#16A34A", lw=2))

    # Link to UI
    ax.annotate("", xy=(80, 51), xytext=(70, 51), arrowprops=dict(arrowstyle="->", color="#D97706", lw=3))
    ax.text(75, 56, "HTTP / WS", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#B45309")
    ax.text(75, 46, "Ports 8080 & 8000", ha="center", va="center", fontsize=7.5, color="#78350F")

    # UI Box
    rect_ui = patches.FancyBboxPatch((80, 20), 17, 62, boxstyle="round,pad=1", facecolor=c_ui, edgecolor=c_ui_b, linewidth=2)
    ax.add_patch(rect_ui)
    ax.text(88.5, 76, "Clients & Consumers", ha="center", va="center", fontsize=11, fontweight="bold", color="#B45309")

    u1 = patches.FancyBboxPatch((82, 55), 13, 15, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#FDE68A", linewidth=1.2)
    ax.add_patch(u1)
    ax.text(88.5, 64, "Simple Dashboard\n(Port 8080)", ha="center", va="center", fontsize=8, fontweight="bold", color="#92400E")
    ax.text(88.5, 58, "Dedicated IW0 (40768)\nRealtime Trend Chart", ha="center", va="center", fontsize=7, color="#475569")

    u2 = patches.FancyBboxPatch((82, 36), 13, 15, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#FDE68A", linewidth=1.2)
    ax.add_patch(u2)
    ax.text(88.5, 45, "Full Industrial UI\n(Port 8000)", ha="center", va="center", fontsize=8, fontweight="bold", color="#92400E")
    ax.text(88.5, 39, "React 19, FFT Vibration,\nAlarms, Machine Control", ha="center", va="center", fontsize=7, color="#475569")

    u3 = patches.FancyBboxPatch((82, 23), 13, 9.5, boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#FDE68A", linewidth=1.2)
    ax.add_patch(u3)
    ax.text(88.5, 27.5, "Node-RED Integration\n(Port 1880 - Alerts / MQTT)", ha="center", va="center", fontsize=7, fontweight="bold", color="#B91C1C")

    plt.tight_layout()
    plt.savefig(FLOWCHART_1_PATH, dpi=300, bbox_inches="tight")
    plt.close()


# Flowchart 2: Telemetry Pipeline
def generate_telemetry_flowchart():
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    stages = [
        ("Step 1: Network Layer", "Static Subnet Setup\neth0: 192.168.1.100\nPLC: 192.168.1.50\n(RTT: 5.5 ms)", "#E0F2FE", "#0284C7"),
        ("Step 2: Modbus TCP Client", "PyModbus Handshake\nPort: 502 | Unit ID: 1\ncall_modbus helper\n(device_id/slave compat)", "#DCFCE7", "#16A34A"),
        ("Step 3: Signal Polling", "FC 02: Read I0..I7\n(Bits: Pusher Ext=1)\nFC 03/04: Read IW0\n(Offset 767/40768 -> 50)", "#FEF3C7", "#D97706"),
        ("Step 4: Quality & Buffer", "Convert to Int16\nTimestamp (UTC & Mono)\nQuality Validation\n50-Point Trend Rolling", "#F3E8FF", "#9333EA"),
        ("Step 5: Client Broadcast", "FastAPI WebSocket\nBroadcast at 5-10 Hz\nChart.js Live Plot\nSimple View & Full Suite", "#FCE7F3", "#DB2777"),
    ]

    for idx, (title, text, bg, border) in enumerate(stages):
        x = 2 + idx * 20
        y = 6
        w = 16
        h = 36
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8", facecolor=bg, edgecolor=border, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 5, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color=border)
        ax.text(x + w/2, y + h/2 - 3, text, ha="center", va="center", fontsize=7.5, color="#1E293B")

        if idx < len(stages) - 1:
            ax.annotate("", xy=(x + w + 3.5, y + h/2), xytext=(x + w + 0.5, y + h/2),
                        arrowprops=dict(arrowstyle="->", color="#475569", lw=2.5))

    plt.tight_layout()
    plt.savefig(FLOWCHART_2_PATH, dpi=300, bbox_inches="tight")
    plt.close()


# Flowchart 3: Commissioning Steps
def generate_commissioning_flowchart():
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    steps = [
        ("1. Set Static IP", "sudo nmcli conn up\neth0: 192.168.1.100\nPing 192.168.1.50", "#E0F2FE", "#0284C7"),
        ("2. Install Deps", "sudo apt install\npython3-venv git\nlibopenblas-dev", "#DCFCE7", "#16A34A"),
        ("3. Clone Repo", "git clone Selec-PLC\ncd Selec-PLC\npython3 -m venv venv", "#FEF3C7", "#D97706"),
        ("4. Run Test Tool", "python modbus_test.py\nVerify IW0 (50)\nVerify Pusher Ext (1)", "#F3E8FF", "#9333EA"),
        ("5. Launch UI", "./start_simple.sh\nPort 8080 or Port 8000\nLive Dashboard Online", "#FCE7F3", "#DB2777"),
    ]

    for idx, (title, text, bg, border) in enumerate(steps):
        x = 2 + idx * 20
        y = 7
        w = 16
        h = 35
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8", facecolor=bg, edgecolor=border, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 5, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color=border)
        ax.text(x + w/2, y + h/2 - 2, text, ha="center", va="center", fontsize=7.5, color="#1E293B")

        if idx < len(steps) - 1:
            ax.annotate("", xy=(x + w + 3.5, y + h/2), xytext=(x + w + 0.5, y + h/2),
                        arrowprops=dict(arrowstyle="->", color="#475569", lw=2.5))

    plt.tight_layout()
    plt.savefig(FLOWCHART_3_PATH, dpi=300, bbox_inches="tight")
    plt.close()


# Flowchart 4: Dual Dashboard & Node-RED Integration
def generate_dashboards_flowchart():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    # Central Gateway Core
    core_box = patches.FancyBboxPatch((35, 10), 30, 32, boxstyle="round,pad=1", facecolor="#DCFCE7", edgecolor="#16A34A", linewidth=2)
    ax.add_patch(core_box)
    ax.text(50, 36, "FastAPI Telemetry Core", ha="center", va="center", fontsize=11, fontweight="bold", color="#15803D")
    ax.text(50, 26, "Connected to 192.168.1.50:502\n- IW0: 50 (Address 40768)\n- Discrete Inputs: 8 Bits\n- Socket RTT: 5.5 ms", ha="center", va="center", fontsize=8, color="#166534")
    ax.text(50, 16, "Live WebSocket Broadcast (/ws)", ha="center", va="center", fontsize=8, fontweight="bold", color="#047857")

    # Left: Simple Dashboard
    left_box = patches.FancyBboxPatch((3, 10), 26, 32, boxstyle="round,pad=1", facecolor="#E0F2FE", edgecolor="#0284C7", linewidth=2)
    ax.add_patch(left_box)
    ax.text(16, 36, "Simple Dashboard\n(Port 8080)", ha="center", va="center", fontsize=10, fontweight="bold", color="#0369A1")
    ax.text(16, 24, "• ./start_simple.sh\n• Giant IW0 Integer Value (50)\n• Chart.js Live Trend Curve\n• Pusher Extended LED\n• Zero Setup Overhead", ha="center", va="center", fontsize=7.5, color="#075985")

    # Right Top: Full Industrial Suite
    right1_box = patches.FancyBboxPatch((71, 26), 26, 17, boxstyle="round,pad=0.8", facecolor="#FEF3C7", edgecolor="#D97706", linewidth=1.8)
    ax.add_patch(right1_box)
    ax.text(84, 38, "Full Industrial Gateway (Port 8000)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#92400E")
    ax.text(84, 31, "• React 19 UI & Latency Analytics\n• FFT Vibration & Machine Controls", ha="center", va="center", fontsize=7, color="#78350F")

    # Right Bottom: Node-RED
    right2_box = patches.FancyBboxPatch((71, 7), 26, 17, boxstyle="round,pad=0.8", facecolor="#FCE7F3", edgecolor="#DB2777", linewidth=1.8)
    ax.add_patch(right2_box)
    ax.text(84, 19, "Node-RED Integration (Port 1880)", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#9D174D")
    ax.text(84, 12, "• WebSocket in from ws://localhost:8000/ws\n• Telegram / WhatsApp / MQTT Push", ha="center", va="center", fontsize=7, color="#831843")

    # Arrows
    ax.annotate("", xy=(34, 26), xytext=(30, 26), arrowprops=dict(arrowstyle="<-", color="#0284C7", lw=2.5))
    ax.annotate("", xy=(70, 35), xytext=(66, 30), arrowprops=dict(arrowstyle="->", color="#D97706", lw=2.5))
    ax.annotate("", xy=(70, 16), xytext=(66, 20), arrowprops=dict(arrowstyle="->", color="#DB2777", lw=2.5))

    plt.tight_layout()
    plt.savefig(FLOWCHART_4_PATH, dpi=300, bbox_inches="tight")
    plt.close()


def create_word_document():
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    navy = RGBColor(15, 23, 42)
    cyan_dark = RGBColor(3, 105, 161)
    gray_muted = RGBColor(100, 116, 139)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("SELEC MiBRX-6M PLC & RASPBERRY PI GATEWAY")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = navy

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Complete Industrial IoT Integration Architecture, Flowcharts & Commissioning Manual")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = cyan_dark

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_meta = p_meta.add_run("Target: Selec MiBRX-6M (192.168.1.50:502) | Gateway: Raspberry Pi 4B (192.168.1.100) | Version 1.0.0")
    run_meta.font.name = "Calibri"
    run_meta.font.size = Pt(10)
    run_meta.font.color.rgb = gray_muted

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1. Executive Summary
    h1 = doc.add_heading("1. Executive Summary & Architecture Overview", level=1)
    h1.style.font.color.rgb = navy
    p1 = doc.add_paragraph(
        "This engineering manual documents the complete Industrial Internet of Things (IIoT) edge architecture "
        "integrating a Selec MiBRX-6M Programmable Logic Controller (PLC) with a Raspberry Pi 4B Gateway running Linux. "
        "The system achieves high-speed, deterministic telemetry acquisition over Modbus TCP on standard port 502 with Unit ID 1. "
        "Specialized implementation is provided for reading physical Input Word IW0 (mapped at Modbus Holding Register 40768) in 16-bit signed integer "
        "format (delivering real-time process value of 50), along with 8-bit Discrete Input status monitoring (FC 02) "
        "with an instantaneous round-trip socket latency of ~5.5 ms."
    )
    p1.paragraph_format.line_spacing = 1.15

    # 2. Hardware Specs Table
    h2 = doc.add_heading("2. System Hardware & Network Specifications", level=1)
    h2.style.font.color.rgb = navy

    table = doc.add_table(rows=7, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    headers = ["System Component", "Hardware / Parameter", "Configuration & Operational Value"]
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        set_cell_shading(hdr_cells[i], "1E293B")
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
                r.font.size = Pt(10)

    specs = [
        ("Target Industrial Controller", "Selec MiBRX-6M Micro-PLC", "IP: 192.168.1.50 | MAC: 80:34:28:1d:db:dd | Mode: RUN"),
        ("IoT Edge Gateway", "Raspberry Pi 4B (ARM64)", "Linux Debian 13 (Trixie/Bookworm) | 4GB RAM"),
        ("Ethernet Network (eth0)", "Direct Cat6 Industrial Cable", "Static IP: 192.168.1.100/24 (Same Subnet as PLC)"),
        ("Wi-Fi Interface (wlan0)", "Local Plant / Lab Wi-Fi", "IP: 192.168.31.71 (Isolated routing via NetworkManager)"),
        ("Modbus Protocol Specification", "Modbus TCP (RFC 791 / MBAP)", "Port: 502 | Unit / Slave ID: 1 | Socket Latency: 5.5 ms"),
        ("Input Word 0 (IW0)", "Selec Analog / Process Input", "Modbus Register: 40768 (Offset 767) | Format: Int16 | Data: 50"),
    ]

    for row_idx, data in enumerate(specs, start=1):
        row_cells = table.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            if row_idx % 2 == 1:
                set_cell_shading(row_cells[col_idx], "F8FAFC")
            for p in row_cells[col_idx].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 3. Flowchart 1: Architecture
    h3 = doc.add_heading("3. Flowchart 1: End-to-End System & Network Architecture", level=1)
    h3.style.font.color.rgb = navy
    doc.add_paragraph(
        "Figure 1 details the complete hardware interconnection, Linux network interfaces (eth0 vs wlan0), "
        "the Python async Modbus polling engine, and the client interfaces (Simple Dashboard on port 8080, Full Industrial UI on port 8000, and Node-RED on port 1880)."
    )
    doc.add_picture(str(FLOWCHART_1_PATH), width=Inches(6.8))
    p_cap1 = doc.add_paragraph("Figure 1: Selec MiBRX-6M to Raspberry Pi 4B IoT Gateway Architecture Diagram.")
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap1.runs[0].font.size = Pt(9)
    p_cap1.runs[0].font.italic = True
    p_cap1.runs[0].font.color.rgb = gray_muted

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 4. Flowchart 2: Telemetry Pipeline
    h4 = doc.add_heading("4. Flowchart 2: Real-Time Modbus Telemetry Pipeline & State Machine", level=1)
    h4.style.font.color.rgb = navy
    doc.add_paragraph(
        "Figure 2 illustrates the step-by-step state machine from physical Ethernet ARP handshake, "
        "through PyModbus query generation, register decoding, timestamping, to WebSocket streaming."
    )
    doc.add_picture(str(FLOWCHART_2_PATH), width=Inches(6.8))
    p_cap2 = doc.add_paragraph("Figure 2: Real-Time Modbus Data Acquisition & Telemetry Pipeline State Machine.")
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap2.runs[0].font.size = Pt(9)
    p_cap2.runs[0].font.italic = True
    p_cap2.runs[0].font.color.rgb = gray_muted

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 5. Flowchart 3: Commissioning Steps
    h5 = doc.add_heading("5. Flowchart 3: Commissioning & Startup Process", level=1)
    h5.style.font.color.rgb = navy
    doc.add_paragraph(
        "Figure 3 outlines the five chronological phases to bring up the system from a freshly installed Raspberry Pi OS to live production operation."
    )
    doc.add_picture(str(FLOWCHART_3_PATH), width=Inches(6.8))
    p_cap3 = doc.add_paragraph("Figure 3: Chronological Gateway Commissioning Workflow.")
    p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap3.runs[0].font.size = Pt(9)
    p_cap3.runs[0].font.italic = True
    p_cap3.runs[0].font.color.rgb = gray_muted

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 6. Flowchart 4: Dual Dashboard & Node-RED Architecture
    h6 = doc.add_heading("6. Flowchart 4: Dual-Dashboard & Node-RED Integration Architecture", level=1)
    h6.style.font.color.rgb = navy
    doc.add_paragraph(
        "Figure 4 visualizes how the single FastAPI telemetry engine powers both the dedicated lightweight IW0 dashboard (port 8080), "
        "the full industrial suite (port 8000), and Node-RED automation workflows (port 1880)."
    )
    doc.add_picture(str(FLOWCHART_4_PATH), width=Inches(6.8))
    p_cap4 = doc.add_paragraph("Figure 4: Multi-Consumer Telemetry Architecture (Port 8080, Port 8000, Port 1880).")
    p_cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap4.runs[0].font.size = Pt(9)
    p_cap4.runs[0].font.italic = True
    p_cap4.runs[0].font.color.rgb = gray_muted

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 7. Step-by-Step Commissioning Commands
    h7 = doc.add_heading("7. Step-by-Step Commissioning & Setup Commands", level=1)
    h7.style.font.color.rgb = navy

    doc.add_paragraph("Follow these exact, copy-paste terminal commands to deploy the gateway on Raspberry Pi OS from scratch:")

    steps = [
        ("Step 1: Configure Permanent Static IP on eth0",
         "sudo nmcli connection modify \"Wired connection 1\" ipv4.addresses 192.168.1.100/24 ipv4.method manual\n"
         "sudo nmcli connection up \"Wired connection 1\"\n"
         "ping -c 3 192.168.1.50"),
        ("Step 2: Install Raspberry Pi System Packages",
         "sudo apt update\n"
         "sudo apt install -y git python3 python3-venv python3-pip libopenblas-dev build-essential"),
        ("Step 3: Clone Fresh Repository from GitHub",
         "cd ~\n"
         "git clone https://github.com/nabeelsyed11/Selec-PLC-Dashboard.git\n"
         "cd Selec-PLC-Dashboard"),
        ("Step 4: Create Virtual Environment & Install Dependencies",
         "python3 -m venv venv\n"
         "./venv/bin/pip install --upgrade pip\n"
         "./venv/bin/pip install -r backend/requirements.txt"),
        ("Step 5: Verify Live Modbus Telemetry with Diagnostic Tool",
         "./venv/bin/python tools/modbus_test.py\n"
         "# Verifies: Socket latency (5.5 ms), Bit 1 Pusher Extended (1), and IW0 (50)"),
        ("Step 6: Launch the Simple IW0 Live Dashboard (Port 8080)",
         "chmod +x start_simple.sh\n"
         "./start_simple.sh\n"
         "# Navigate in browser to: http://localhost:8080"),
        ("Step 7: Launch Full Industrial IoT Gateway Dashboard (Port 8000)",
         "chmod +x start.sh\n"
         "./start.sh\n"
         "# Navigate in browser to: http://localhost:8000"),
    ]

    for title, cmd_block in steps:
        p_st = doc.add_paragraph()
        r_st = p_st.add_run(title)
        r_st.bold = True
        r_st.font.size = Pt(11)
        r_st.font.color.rgb = cyan_dark

        table_cmd = doc.add_table(rows=1, cols=1)
        table_cmd.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_cmd.style = 'Table Grid'
        cell = table_cmd.rows[0].cells[0]
        set_cell_shading(cell, "0F172A")
        set_cell_margins(cell, top=120, bottom=120, left=200, right=200)

        p_c = cell.paragraphs[0]
        p_c.paragraph_format.line_spacing = 1.15
        r_code = p_c.add_run(cmd_block)
        r_code.font.name = "Consolas"
        r_code.font.size = Pt(9.5)
        r_code.font.color.rgb = RGBColor(56, 189, 248)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 8. Troubleshooting Matrix
    h8 = doc.add_heading("8. Engineering Troubleshooting & Resolution Log", level=1)
    h8.style.font.color.rgb = navy

    tbl_ts = doc.add_table(rows=5, cols=3)
    tbl_ts.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_ts.style = 'Table Grid'

    ts_headers = ["Symptom / Error", "Root Cause Analysis", "Applied Engineering Resolution"]
    hdr_ts = tbl_ts.rows[0].cells
    for i, h in enumerate(ts_headers):
        hdr_ts[i].text = h
        set_cell_shading(hdr_ts[i], "1E293B")
        for p in hdr_ts[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
                r.font.size = Pt(9.5)

    ts_data = [
        ("Nmap showed 'filtered', ping timed out",
         "Linux routed 192.168.1.50 packets to wlan0 default gateway (192.168.31.1) rather than eth0.",
         "Assigned static IP 192.168.1.100/24 to eth0 via nmcli. Ping dropped to 0.15 ms immediately."),
        ("PyModbus TypeError: unexpected keyword 'slave'",
         "PyModbus 3.8+ deprecated and removed 'slave' in favor of 'device_id'.",
         "Implemented call_modbus() dynamic wrapper inspecting method signatures across PyModbus versions."),
        ("Holding Regs FC 03: Exception 1 (Illegal Function)",
         "Selec ladder software only activates Modbus FC 03 for registers mapped in the Slave Table.",
         "Discovered user's active register at 40768 (IW0, offset 767) returning value 50. Handled gracefully."),
        ("ModuleNotFoundError: No module named 'fastapi'",
         "Shell script invoked global /usr/bin/python3 rather than native Linux ./venv/bin/python.",
         "Hardcoded script execution path to $SCRIPT_DIR/venv/bin/python with automatic dependency self-healing."),
    ]

    for row_idx, data in enumerate(ts_data, start=1):
        row_cells = tbl_ts.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            if row_idx % 2 == 1:
                set_cell_shading(row_cells[col_idx], "F8FAFC")
            for p in row_cells[col_idx].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # Footer note
    p_foot = doc.add_paragraph()
    p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_foot = p_foot.add_run("--- End of Technical Documentation ---")
    r_foot.font.italic = True
    r_foot.font.color.rgb = gray_muted
    r_foot.font.size = Pt(9)

    # Save to both docs/ and project root for instant access
    doc.save(OUTPUT_DOCX_PATH)
    shutil.copy2(OUTPUT_DOCX_PATH, ROOT_DOCX_PATH)
    print(f"[+] Saved to: {OUTPUT_DOCX_PATH}")
    print(f"[+] Saved to root: {ROOT_DOCX_PATH}")


def main():
    print("[*] Generating Flowchart 1 (Architecture)...")
    generate_architecture_flowchart()
    print("[*] Generating Flowchart 2 (Telemetry Pipeline)...")
    generate_telemetry_flowchart()
    print("[*] Generating Flowchart 3 (Commissioning Workflow)...")
    generate_commissioning_flowchart()
    print("[*] Generating Flowchart 4 (Dual Dashboard & Node-RED)...")
    generate_dashboards_flowchart()
    print("[*] Building Microsoft Word Document (.docx)...")
    create_word_document()


if __name__ == "__main__":
    main()
