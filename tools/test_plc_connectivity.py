#!/usr/bin/env python3
"""
PLC Connectivity Test Script - Run locally to diagnose network issues
"""
import socket
import sys
import time

def test_tcp_connection(host, port, timeout=3.0):
    """Test raw TCP connectivity to PLC."""
    print(f"\nTesting TCP connection to {host}:{port}")
    print("-" * 50)

    # Test 1: Basic socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"[OK] TCP connection to {host}:{port} successful!")
            sock.close()
            return True
        else:
            print(f"[FAIL] TCP connection refused (error code: {result})")
            print("       PLC may be powered off, wrong IP, or firewall blocking")
            sock.close()
            return False
    except socket.gaierror as e:
        print(f"[FAIL] DNS/Address resolution failed: {e}")
        return False
    except socket.timeout:
        print(f"[FAIL] Connection timed out after {timeout}s")
        print("       PLC may be on different subnet or network cable issue")
        return False
    except Exception as e:
        print(f"[FAIL] Socket error: {e}")
        return False

def check_local_network():
    """Display local network configuration."""
    print("\nLocal Network Configuration:")
    print("-" * 50)

    import subprocess
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'IPv4' in line or 'Adapter' in line or 'Default Gateway' in line:
                print(f"  {line.strip()}")
    except Exception as e:
        print(f"  Could not get local IP: {e}")

if __name__ == "__main__":
    host = "192.168.1.50"
    port = 502

    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    check_local_network()
    success = test_tcp_connection(host, port)

    print("\n" + "=" * 50)
    if success:
        print("RESULT: PLC TCP connectivity OK - You can now use physical mode!")
        print("        Try the dashboard at http://localhost:8000")
    else:
        print("RESULT: PLC NOT REACHABLE")
        print("SOLUTIONS:")
        print("  1. Check Ethernet cable connection")
        print("  2. Verify PLC power and IP configuration")
        print("  3. Ensure PLC IP (192.168.1.50) is reachable from your PC")
        print("  4. Temporarily enable SIMULATION_MODE in .env to test dashboard")
    print("=" * 50)

    sys.exit(0 if success else 1)