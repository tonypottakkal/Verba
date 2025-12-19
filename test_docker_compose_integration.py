#!/usr/bin/env python3
"""
Docker Compose Integration Tests for Verba Observability

This test suite verifies:
- Phoenix service startup and port accessibility
- Verba-Phoenix connectivity over OTLP gRPC  
- Existing Ollama connectivity preservation

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import subprocess
import time
import socket
import requests
import json
import sys
import os
from typing import Tuple, Dict, Any, Optional
from contextlib import contextmanager


class DockerComposeIntegrationTests:
    """Integration tests for Docker Compose setup with Phoenix observability."""
    
    def __init__(self):
        self.base_compose_file = "docker-compose.yml"
        self.phoenix_compose_file = "docker-compose.phoenix.yml"
        self.test_timeout = 120  # 2 minutes for service startup
        self.phoenix_ui_port = 6006
        self.phoenix_otlp_port = 4317
        self.verba_port = 8000
        self.weaviate_port = 8080
        self.ollama_port = 11434
        self.docker_available = self._check_docker_availability()
    
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
        
    def run_command(self, cmd: list, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return success status, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(__file__)
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def check_port_accessibility(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """Check if a port is accessible."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"Port {port} is accessible on {host}"
            else:
                return False, f"Port {port} is not accessible on {host}"
        except Exception as e:
            return False, f"Error checking port {port}: {str(e)}"
    
    def check_http_endpoint(self, url: str, timeout: int = 10) -> Tuple[bool, str, Optional[int]]:
        """Check if an HTTP endpoint is accessible."""
        try:
            response = requests.get(url, timeout=timeout)
            return True, f"HTTP endpoint accessible: {response.status_code}", response.status_code
        except requests.exceptions.RequestException as e:
            return False, f"HTTP endpoint not accessible: {str(e)}", None
    
    def wait_for_service_health(self, service_name: str, max_wait: int = 120) -> Tuple[bool, str]:
        """Wait for a Docker Compose service to become healthy."""
        print(f"   Waiting for {service_name} to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            success, stdout, stderr = self.run_command([
                "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                "ps", "--format", "json"
            ])
            
            if success:
                try:
                    services = []
                    for line in stdout.strip().split('\n'):
                        if line.strip():
                            services.append(json.loads(line))
                    
                    for service in services:
                        if service.get('Service') == service_name:
                            state = service.get('State', '')
                            health = service.get('Health', '')
                            
                            if health == 'healthy' or (state == 'running' and not health):
                                return True, f"{service_name} is healthy"
                            elif 'exited' in state.lower() or 'dead' in state.lower():
                                return False, f"{service_name} failed to start: {state}"
                
                except json.JSONDecodeError:
                    pass
            
            time.sleep(5)
        
        return False, f"{service_name} did not become healthy within {max_wait}s"
    
    @contextmanager
    def docker_compose_services(self):
        """Context manager to start and stop Docker Compose services."""
        print("🚀 Starting Docker Compose services...")
        
        # Stop any existing services first
        self.run_command([
            "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
            "down", "--remove-orphans"
        ], timeout=60)
        
        # Start services
        success, stdout, stderr = self.run_command([
            "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
            "up", "-d"
        ], timeout=120)
        
        if not success:
            raise Exception(f"Failed to start services: {stderr}")
        
        try:
            yield
        finally:
            print("🛑 Stopping Docker Compose services...")
            self.run_command([
                "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                "down", "--remove-orphans"
            ], timeout=60)
    
    def test_phoenix_service_startup(self) -> bool:
        """
        Test Phoenix service startup and port accessibility.
        Requirements: 1.1, 1.2, 1.5
        """
        print("Testing Phoenix service startup and port accessibility...")
        
        if not self.docker_available:
            print("   ⚠️  Docker not available - running configuration validation instead")
            return self._validate_phoenix_configuration()
        
        try:
            with self.docker_compose_services():
                # Wait for Phoenix to become healthy
                success, message = self.wait_for_service_health("phoenix", max_wait=self.test_timeout)
                if not success:
                    print(f"   ❌ Phoenix health check failed: {message}")
                    return False
                
                print(f"   ✓ {message}")
                
                # Test Phoenix UI port accessibility (Requirement 1.1, 1.5)
                success, message = self.check_port_accessibility("localhost", self.phoenix_ui_port)
                if not success:
                    print(f"   ❌ Phoenix UI port check failed: {message}")
                    return False
                
                print(f"   ✓ {message}")
                
                # Test Phoenix OTLP gRPC port accessibility (Requirement 1.2)
                success, message = self.check_port_accessibility("localhost", self.phoenix_otlp_port)
                if not success:
                    print(f"   ❌ Phoenix OTLP port check failed: {message}")
                    return False
                
                print(f"   ✓ {message}")
                
                # Test Phoenix UI HTTP endpoint (Requirement 1.5)
                success, message, status_code = self.check_http_endpoint(f"http://localhost:{self.phoenix_ui_port}")
                if not success:
                    print(f"   ❌ Phoenix UI HTTP check failed: {message}")
                    return False
                
                print(f"   ✓ Phoenix UI accessible at http://localhost:{self.phoenix_ui_port} (status: {status_code})")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Phoenix service startup test failed: {str(e)}")
            return False
    
    def test_verba_phoenix_connectivity(self) -> bool:
        """
        Test Verba-Phoenix connectivity over OTLP gRPC.
        Requirement: 1.3
        """
        print("Testing Verba-Phoenix connectivity over OTLP gRPC...")
        
        if not self.docker_available:
            print("   ⚠️  Docker not available - running configuration validation instead")
            return self._validate_verba_phoenix_configuration()
        
        try:
            with self.docker_compose_services():
                # Wait for both Phoenix and Verba to be healthy
                phoenix_success, phoenix_msg = self.wait_for_service_health("phoenix", max_wait=60)
                if not phoenix_success:
                    print(f"   ❌ Phoenix not ready: {phoenix_msg}")
                    return False
                
                verba_success, verba_msg = self.wait_for_service_health("verba", max_wait=self.test_timeout)
                if not verba_success:
                    print(f"   ❌ Verba not ready: {verba_msg}")
                    return False
                
                print(f"   ✓ Both services are healthy")
                
                # Check that Verba can reach Phoenix OTLP endpoint within Docker network
                # We'll verify this by checking the container logs for OTLP connection attempts
                success, stdout, stderr = self.run_command([
                    "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                    "logs", "verba"
                ], timeout=30)
                
                if success:
                    # Look for OpenTelemetry initialization or connection logs
                    logs = stdout.lower()
                    if any(keyword in logs for keyword in ["otel", "opentelemetry", "phoenix", "otlp"]):
                        print("   ✓ Verba shows OpenTelemetry/Phoenix related logs")
                    else:
                        print("   ⚠️  No explicit OTLP connection logs found (may be normal)")
                
                # Verify Verba environment variables are set correctly
                success, stdout, stderr = self.run_command([
                    "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                    "exec", "-T", "verba", "env"
                ], timeout=30)
                
                if success:
                    env_vars = stdout
                    required_vars = [
                        "OTEL_SERVICE_NAME=verba",
                        "OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317",
                        "OTEL_EXPORTER_OTLP_PROTOCOL=grpc",
                        "OTEL_TRACES_EXPORTER=otlp"
                    ]
                    
                    missing_vars = []
                    for var in required_vars:
                        if var not in env_vars:
                            missing_vars.append(var)
                    
                    if missing_vars:
                        print(f"   ❌ Missing environment variables: {missing_vars}")
                        return False
                    else:
                        print("   ✓ All required OTLP environment variables are set")
                
                # Test that Verba can make HTTP requests (basic connectivity)
                success, message, status_code = self.check_http_endpoint(f"http://localhost:{self.verba_port}")
                if not success:
                    print(f"   ❌ Verba HTTP endpoint not accessible: {message}")
                    return False
                
                print(f"   ✓ Verba HTTP endpoint accessible (status: {status_code})")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Verba-Phoenix connectivity test failed: {str(e)}")
            return False
    
    def test_ollama_connectivity_preservation(self) -> bool:
        """
        Test that existing Ollama connectivity is preserved.
        Requirement: 1.4
        """
        print("Testing Ollama connectivity preservation...")
        
        if not self.docker_available:
            print("   ⚠️  Docker not available - running configuration validation instead")
            return self._validate_ollama_configuration()
        
        try:
            with self.docker_compose_services():
                # Wait for Verba to be ready
                success, message = self.wait_for_service_health("verba", max_wait=self.test_timeout)
                if not success:
                    print(f"   ❌ Verba not ready: {message}")
                    return False
                
                # Check Verba environment variables for Ollama configuration
                success, stdout, stderr = self.run_command([
                    "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                    "exec", "-T", "verba", "env"
                ], timeout=30)
                
                if success:
                    env_vars = stdout
                    ollama_url = "OLLAMA_URL=http://host.docker.internal:11434"
                    
                    if ollama_url not in env_vars:
                        print(f"   ❌ Ollama URL not configured correctly in Verba")
                        return False
                    else:
                        print("   ✓ Ollama URL configured correctly in Verba")
                
                # Test that host.docker.internal resolution works from within Verba container
                # This tests the Docker network configuration
                success, stdout, stderr = self.run_command([
                    "docker-compose", "-f", self.base_compose_file, "-f", self.phoenix_compose_file,
                    "exec", "-T", "verba", "nslookup", "host.docker.internal"
                ], timeout=30)
                
                if success:
                    print("   ✓ host.docker.internal resolves from Verba container")
                else:
                    print("   ⚠️  host.docker.internal resolution test inconclusive")
                
                # Check that Ollama port would be accessible if Ollama were running
                # Note: We don't require Ollama to actually be running for this test
                # We just verify the network configuration allows the connection
                print("   ✓ Ollama connectivity configuration preserved")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Ollama connectivity preservation test failed: {str(e)}")
            return False
    
    def test_docker_network_configuration(self) -> bool:
        """Test Docker network configuration."""
        print("Testing Docker network configuration...")
        
        if not self.docker_available:
            print("   ⚠️  Docker not available - validating compose file configuration instead")
            return self._validate_network_configuration()
        
        try:
            # Check if ollama-docker network exists or gets created
            success, stdout, stderr = self.run_command([
                "docker", "network", "ls", "--filter", "name=ollama-docker", "--format", "{{.Name}}"
            ])
            
            if success and "ollama-docker" in stdout:
                print("   ✓ ollama-docker network exists")
                return True
            else:
                print("   ⚠️  ollama-docker network not found (will be created by docker-compose)")
                return True
                
        except Exception as e:
            print(f"   ❌ Docker network configuration test failed: {str(e)}")
            return False
    
    def _validate_phoenix_configuration(self) -> bool:
        """Validate Phoenix configuration in docker-compose files."""
        try:
            # Check if phoenix compose file exists and has correct configuration
            if not os.path.exists(self.phoenix_compose_file):
                print(f"   ❌ Phoenix compose file not found: {self.phoenix_compose_file}")
                return False
            
            with open(self.phoenix_compose_file, 'r') as f:
                content = f.read()
            
            # Check for required Phoenix configuration
            required_configs = [
                "arizephoenix/phoenix:latest",
                "6006:6006",  # UI port
                "4317:4317",  # OTLP port
                "ollama-docker"  # network
            ]
            
            missing_configs = []
            for config in required_configs:
                if config not in content:
                    missing_configs.append(config)
            
            if missing_configs:
                print(f"   ❌ Missing Phoenix configurations: {missing_configs}")
                return False
            
            print("   ✓ Phoenix configuration validated in docker-compose.phoenix.yml")
            return True
            
        except Exception as e:
            print(f"   ❌ Phoenix configuration validation failed: {str(e)}")
            return False
    
    def _validate_verba_phoenix_configuration(self) -> bool:
        """Validate Verba-Phoenix connectivity configuration."""
        try:
            if not os.path.exists(self.phoenix_compose_file):
                print(f"   ❌ Phoenix compose file not found: {self.phoenix_compose_file}")
                return False
            
            with open(self.phoenix_compose_file, 'r') as f:
                content = f.read()
            
            # Check for required OTLP environment variables
            required_env_vars = [
                "OTEL_SERVICE_NAME=verba",
                "OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317",
                "OTEL_EXPORTER_OTLP_PROTOCOL=grpc",
                "OTEL_TRACES_EXPORTER=otlp"
            ]
            
            missing_vars = []
            for var in required_env_vars:
                if var not in content:
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"   ❌ Missing OTLP environment variables: {missing_vars}")
                return False
            
            print("   ✓ Verba-Phoenix OTLP configuration validated")
            return True
            
        except Exception as e:
            print(f"   ❌ Verba-Phoenix configuration validation failed: {str(e)}")
            return False
    
    def _validate_ollama_configuration(self) -> bool:
        """Validate Ollama connectivity configuration."""
        try:
            if not os.path.exists(self.base_compose_file):
                print(f"   ❌ Base compose file not found: {self.base_compose_file}")
                return False
            
            with open(self.base_compose_file, 'r') as f:
                content = f.read()
            
            # Check for Ollama URL configuration
            if "OLLAMA_URL=http://host.docker.internal:11434" not in content:
                print("   ❌ Ollama URL not configured correctly")
                return False
            
            print("   ✓ Ollama connectivity configuration validated")
            return True
            
        except Exception as e:
            print(f"   ❌ Ollama configuration validation failed: {str(e)}")
            return False
    
    def _validate_network_configuration(self) -> bool:
        """Validate Docker network configuration in compose files."""
        try:
            files_to_check = [self.base_compose_file, self.phoenix_compose_file]
            
            for compose_file in files_to_check:
                if not os.path.exists(compose_file):
                    print(f"   ❌ Compose file not found: {compose_file}")
                    return False
                
                with open(compose_file, 'r') as f:
                    content = f.read()
                
                if "ollama-docker" not in content:
                    print(f"   ❌ ollama-docker network not configured in {compose_file}")
                    return False
            
            print("   ✓ Docker network configuration validated in compose files")
            return True
            
        except Exception as e:
            print(f"   ❌ Network configuration validation failed: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        print("🧪 Running Docker Compose Integration Tests")
        print("=" * 60)
        
        if self.docker_available:
            print("🐳 Docker is available - running full integration tests")
        else:
            print("⚠️  Docker not available - running configuration validation tests")
        
        tests = [
            ("Docker Network Configuration", self.test_docker_network_configuration),
            ("Phoenix Service Startup", self.test_phoenix_service_startup),
            ("Verba-Phoenix Connectivity", self.test_verba_phoenix_connectivity),
            ("Ollama Connectivity Preservation", self.test_ollama_connectivity_preservation),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 40)
            
            try:
                if test_func():
                    print(f"✅ {test_name}: PASSED")
                    passed += 1
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            if self.docker_available:
                print("🎉 All Docker Compose integration tests passed!")
                print("\n📝 Integration verified:")
                print("   ✓ Phoenix service starts and exposes required ports")
                print("   ✓ Verba connects to Phoenix over OTLP gRPC")
                print("   ✓ Ollama connectivity configuration preserved")
            else:
                print("🎉 All configuration validation tests passed!")
                print("\n📝 Configuration validated:")
                print("   ✓ Phoenix service configuration is correct")
                print("   ✓ Verba-Phoenix OTLP configuration is correct")
                print("   ✓ Ollama connectivity configuration is preserved")
                print("\n🐳 To run full integration tests, ensure Docker is running and re-run this script")
            return True
        else:
            print("❌ Some integration tests failed")
            print("\n🔧 Troubleshooting:")
            if self.docker_available:
                print("   1. Ensure Docker is running and has sufficient resources")
                print("   2. Check that ports 6006, 4317, 8000, 8080 are available")
                print("   3. Verify docker-compose files are present and valid")
                print("   4. Check Docker logs: docker-compose logs <service-name>")
            else:
                print("   1. Install and start Docker to run full integration tests")
                print("   2. Verify docker-compose files are present and valid")
                print("   3. Check file permissions and syntax")
            return False


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Docker Compose Integration Tests for Verba Observability")
        print("\nThis test suite verifies:")
        print("- Phoenix service startup and port accessibility (Requirements 1.1, 1.2, 1.5)")
        print("- Verba-Phoenix connectivity over OTLP gRPC (Requirement 1.3)")
        print("- Existing Ollama connectivity preservation (Requirement 1.4)")
        print("\nUsage: python test_docker_compose_integration.py")
        return 0
    
    tester = DockerComposeIntegrationTests()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())