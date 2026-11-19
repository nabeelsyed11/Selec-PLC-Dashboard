#!/usr/bin/env python3
"""Diagnostic probe: query live backend endpoints and print raw responses."""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def get(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"EXC: {e!r}"


def post(path, data):
    url = BASE + path
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"EXC: {e!r}"


def main():
    for p in ["/api/system/config", "/api/system/diagnostics", "/api/system/telemetry"]:
        st, body = get(p)
        print(f"GET {p} -> {st}")
        print(body[:2000])
        print("-" * 60)

    print("=== Switching to PHYSICAL mode (192.168.1.50:502, sim=false) ===")
    st, body = post("/api/system/config", {
        "plc_host": "192.168.1.50",
        "plc_port": 502,
        "plc_unit_id": 1,
        "simulation_mode": False,
        "plc_timeout_seconds": 2.0,
    })
    print(f"POST /api/system/config -> {st}")
    print(body[:2000])
    print("-" * 60)

    import time
    time.sleep(3)
    for p in ["/api/system/config", "/api/system/diagnostics"]:
        st, body = get(p)
        print(f"GET {p} -> {st}")
        print(body[:2000])
        print("-" * 60)


if __name__ == "__main__":
    main()