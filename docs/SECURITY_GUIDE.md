# SECURITY_GUIDE.md — Industrial IoT Security & Hardening Checklist

> Best practices for securing the Selec MiBRX-6M PLC and Raspberry Pi 5 Gateway.

---

## 1. Network Segmentation & Firewall Isolation

- **Purdue Model Level 1/2 Isolation**: The PLC Modbus TCP interface and the Raspberry Pi 5 must reside on an isolated Operational Technology (OT) VLAN.
- **No Direct Internet Exposure**: Never port-forward TCP port 502 (Modbus) or port 8000 (HTTP) to the public internet. Use an authenticated VPN (WireGuard or Tailscale) or reverse proxy with mTLS.
- **Raspberry Pi Firewall**:
  ```bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow in on eth0 to any port 8000 proto tcp comment "LAN Dashboard Access"
  sudo ufw enable
  ```

---

## 2. Hardened Service Configuration

- **Unprivileged Daemon**: The service runs under `iotgateway` user with no interactive shell (`/bin/false`).
- **Sandboxing via systemd**:
  - `ProtectSystem=full` (read-only system directories)
  - `ProtectHome=true` (inaccessible home directories)
  - `NoNewPrivileges=true` (blocks privilege escalation)
  - `PrivateTmp=true` (isolated `/tmp` directory)

---

## 3. Remote Control Safety Guardrails

- **Disabled by Default**: Remote writing to PLC coils/registers is disabled out-of-the-box (`ALLOW_REMOTE_CONTROL=false`).
- **Strict Allowlist**: Only registers explicitly configured in `config/register_map.yaml` under `writable_allowlist` can ever be targeted. Arbitrary memory writes are blocked by software validation before any Modbus frame is transmitted.
- **Permissive Interlocks**: Software verifies hardware E-Stop and guard door status before executing commands.
- **Immutable Audit Logging**: Every command attempt (successful or rejected) is permanently recorded in SQLite with timestamp, operator name, client IP address, and readback verification.

---

## 4. SSH & Gateway Hardening

- Disable password authentication for SSH (`PasswordAuthentication no` in `/etc/ssh/sshd_config`).
- Enforce public-key authentication only.
- Set complex, unique passwords on Raspberry Pi system accounts.
- Enable automatic security updates:
  ```bash
  sudo apt install -y unattended-upgrades
  sudo dpkg-reconfigure --priority=low unattended-upgrades
  ```
