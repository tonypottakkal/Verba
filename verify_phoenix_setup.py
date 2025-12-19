#!/usr/bin/env python3
"""
Verification script for Phoenix service integration.
This script verifies that Phoenix is accessible and ready to receive OTLP traces.
"""

import requests
import socket
import time
import sys
from typing import Tuple


def check_phoenix_ui(host: str = "localhost", port: int = 6006) -> Tuple[bool, str]:
    """Check if Phoenix UI is accessible."""
    try:
        response = requests.get(f"http://{host}:{port}", timeout=10)
        if response.status_code == 200:
            return True, f"Phoenix UI accessible at http://{host}:{port}"
        else:
            return False, f"Phoenix UI returned status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Failed to connect to Phoenix UI: {str(e)}"


def check_otlp_port(host: str = "localhost", port: int = 4317) -> Tuple[bool, str]:
    """Check if OTLP gRPC port is open and listening."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, f"OTLP gRPC port {port} is open and listening"
        else:
            return False, f"OTLP gRPC port {port} is not accessible"
    except Exception as e:
        return False, f"Error checking OTLP port: {str(e)}"


def check_docker_network() -> Tuple[bool, str]:
    """Check if ollama-docker network exists."""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "network", "ls", "--filter", "name=ollama-docker", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "ollama-docker" in result.stdout:
            return True, "Docker network 'ollama-docker' exists"
        else:
            return False, "Docker network 'ollama-docker' not found"
    except Exception as e:
        return False, f"Error checking Docker network: {str(e)}"


def main():
    """Run all verification checks."""
    print("🔍 Verifying Phoenix service integration setup...")
    print("=" * 60)
    
    checks = [
        ("Docker Network", check_docker_network),
        ("Phoenix UI", lambda: check_phoenix_ui()),
        ("OTLP gRPC Port", lambda: check_otlp_port()),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        try:
            success, message = check_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status}: {message}")
            
            if not success:
                all_passed = False
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All checks passed! Phoenix integration is ready.")
        print("\n📝 Next steps:")
        print("   1. Start services: docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d")
        print("   2. Access Phoenix UI: http://localhost:6006")
        print("   3. Verify Verba traces appear in Phoenix after making requests")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the setup.")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure Docker is running")
        print("   2. Start Phoenix: docker-compose -f docker-compose.phoenix.yml up -d phoenix")
        print("   3. Wait for Phoenix to fully start (may take 30-60 seconds)")
        print("   4. Re-run this verification script")
        return 1


if __name__ == "__main__":
    sys.exit(main())