# Selec PLC Connection Setup - Step by Step

## Current Status
- PC WiFi: 192.168.31.152 (online)
- PC Ethernet: DISCONNECTED ❌
- PLC IP: 192.168.1.50:502 (unreachable)

## To Connect Real PLC

### Step 1: Physical Connection
1. Get an Ethernet cable
2. Plug one end into your PC's **green RJ45 port** (not the one you usually ignore)
3. Plug the other end into:
   - PLC Ethernet port, OR
   - A network switch/hub, then to the PLC

### Step 2: Verify Connection
After plugging in:
1. Open Control Panel → Network and Sharing Center → Change adapter settings
2. Find "Ethernet" and click
3. Check "Status" - it should say "This device is working properly"

### Step 3: Check PLC IP
On the PLC display or configuration screen:
- Navigate to Network settings
- Find the IP address - it might NOT be 192.168.1.50

### Step 4: Update .env If IP Changed
If PLC IP is different, edit `.env`:
```
PLC_HOST=YOUR_NEW_IP
PLC_PORT=502
```

### Step 5: Launch Dashboard
Run:
```bash
run_simulation.bat
```

Dashboard will show live PLC data!

---

## Alternative: Use Wi-Fi Bridging
If you can't use Ethernet:
1. Configure router to bridge WiFi and Ethernet
2. Assign PCL fixed IP via router DHCP reservation

---

## Quick Check
Run this to verify connection:
```bash
python tools/test_plc_connectivity.py
```