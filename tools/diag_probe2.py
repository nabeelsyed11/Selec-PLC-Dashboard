#!/usr/bin/env python3
"""Probe signals/alarms/latency endpoints in current (physical) mode."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def get(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"EXC: {e!r}"


def main():
    for p in ["/api/signals", "/api/alarms", "/api/latency", "/api/system/config"]:
        st, body = get(p)
        print(f"GET {p} -> {st}")
        try:
            data = json.loads(body)
            print(json.dumps(data, indent=2)[:3000])
        except Exception:
            print(body[:1500])
        print("-" * 60)


if __name__ == "__main__":
    main()