#!/usr/bin/env python3
"""
Containerized Test Runner for Verba Observability

This script creates a temporary Docker container to run all tests in isolation,
ensuring tests run in the same environment as the deployed application.

Usage:
    python run_containerized_tests.py [--build-only] [--test-only] [--verbose]
"""

import subprocess
import time
import sys
import os
import json
import argparse
import tempfile
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class ContainerizedTestRunner:
    """Run tests in isolated Docker containers matching the deployment environment."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_image_name = "verba-test-runner"
        self.test_container_name = "verba-test-container"
        
        # All test files to run
        self.test_files = [
            "test_dependency_verification.py",
            "test_docker_build_verification.py", 
            "test_docker_compose_integration.py",
            "test_observability_integration.py",
            "test_end_to_end_tracing_integration.py",
            "test_error_handling.py",
            "test_feedback_integration.py",
            "test_observability_property.py",
            "test_property_7_minimal.py",
            "test_error_tracing_simple.py",
            "test_syntax_check.py"
        ]
        
        # Property-based test files (run with Hypothesis)
        self.property_test_files = [
            "test_observability_property.py",
            "test_property_7_minimal.py"
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp and level."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [{level}]"
        
        if level == "ERROR":
            print(f"❌ {prefix} {message}")
        elif level == "WARN":
            print(f"⚠️  {prefix} {message}")
        elif level == "SUCCESS":
            print(f"✅ {prefix} {message}")
        else:
            print(f"ℹ️  {prefix} {message}")
        
        if self.verbose and level == "DEBUG":
            print(f"🔍 {prefix} {message}")
    
    def run_command(self, cmd: List[str], timeout: int = 300, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr."""
        if self.verbose:
            self.log(f"Running command: {' '.join(cmd)}", "DEBUG")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.path.dirname(__file__)
            )
            
            success = result.returncode == 0
            if self.verbose and not success:
                self.log(f"Command failed with return code {result.returncode}", "DEBUG")
                if result.stderr:
                    self.log(f"STDERR: {result.stderr[:500]}...", "DEBUG")
            
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s", "ERROR")
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            self.log(f"Command execution error: {e}", "ERROR")
            return False, "", str(e)
    
    def create_test_dockerfile(self) -> str:
        """Create a Dockerfile for the test runner container."""
        dockerfile_content = """
# Test Runner Dockerfile - Based on Verba production image
FROM python:3.11

# Set working directory
WORKDIR /Verba

# Copy the entire Verba codebase
COPY . /Verba

# Install Verba and its dependencies
RUN pip install --no-cache-dir '.'
RUN pip install --no-cache-dir pandas

# Install observability dependencies (matching production)
RUN pip install --no-cache-dir \\
    arize-phoenix-otel \\
    opentelemetry-sdk \\
    opentelemetry-exporter-otlp \\
    openinference-instrumentation-langchain \\
    opentelemetry-instrumentation-requests

# Install additional test dependencies
RUN pip install --no-cache-dir \\
    pytest \\
    pytest-asyncio \\
    hypothesis \\
    requests \\
    aiohttp

# Install Docker client for integration tests
RUN apt-get update && apt-get install -y \\
    docker.io \\
    curl \\
    netcat-openbsd \\
    && rm -rf /var/lib/apt/lists/*

# Create test results directory
RUN mkdir -p /test-results

# Set environment variables for testing
ENV PYTHONPATH=/Verba
ENV OTEL_SERVICE_NAME=verba-test
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_METRICS_EXPORTER=none
ENV OTEL_LOGS_EXPORTER=none

# Default command runs all tests
CMD ["python", "-m", "pytest", "-v", "--tb=short"]
"""
        
        dockerfile_path = os.path.join(os.path.dirname(__file__), "Dockerfile.test")
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content.strip())
        
        return dockerfile_path
    
    def build_test_image(self) -> bool:
        """Build the Docker image for running tests."""
        self.log("Building test runner Docker image...")
        
        # Create test Dockerfile
        dockerfile_path = self.create_test_dockerfile()
        
        try:
            # Build the test image
            success, stdout, stderr = self.run_command([
                "docker", "build",
                "-f", dockerfile_path,
                "-t", self.test_image_name,
                "."
            ], timeout=600)  # 10 minutes for build
            
            if success:
                self.log("Test runner image built successfully", "SUCCESS")
                return True
            else:
                self.log(f"Failed to build test image: {stderr}", "ERROR")
                return False
                
        finally:
            # Clean up temporary Dockerfile
            if os.path.exists(dockerfile_path):
                os.remove(dockerfile_path)
    
    def run_test_in_container(self, test_file: str, network: Optional[str] = None) -> Tuple[bool, str, str]:
        """Run a specific test file in a container."""
        self.log(f"Running {test_file} in container...")
        
        # Prepare Docker run command
        docker_cmd = [
            "docker", "run", "--rm",
            "--name", f"{self.test_container_name}-{int(time.time())}",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",  # For Docker-in-Docker tests
        ]
        
        # Add network if specified (for integration tests)
        if network:
            docker_cmd.extend(["--network", network])
        
        # Add the image and command
        docker_cmd.extend([
            self.test_image_name,
            "python", f"/Verba/{test_file}"
        ])
        
        return self.run_command(docker_cmd, timeout=300)
    
    def run_property_test_with_hypothesis(self, test_file: str, iterations: int = 100) -> Tuple[bool, str, str]:
        """Run property-based tests with Hypothesis configuration."""
        self.log(f"Running property test {test_file} with {iterations} iterations...")
        
        docker_cmd = [
            "docker", "run", "--rm",
            "--name", f"{self.test_container_name}-property-{int(time.time())}",
            "-e", f"HYPOTHESIS_MAX_EXAMPLES={iterations}",
            "-e", "HYPOTHESIS_VERBOSITY=verbose",
            self.test_image_name,
            "python", f"/Verba/{test_file}"
        ]
        
        return self.run_command(docker_cmd, timeout=600)  # Longer timeout for property tests
    
    def run_all_unit_tests(self) -> Dict[str, bool]:
        """Run all unit tests in isolated containers."""
        self.log("Running all unit tests in containers...")
        
        test_results = {}
        
        for test_file in self.test_files:
            if test_file in self.property_test_files:
                # Run property tests with special configuration
                success, stdout, stderr = self.run_property_test_with_hypothesis(test_file)
            else:
                # Run regular unit tests
                success, stdout, stderr = self.run_test_in_container(test_file)
            
            test_results[test_file] = success
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {stdout[:1000]}...", "DEBUG")
                    self.log(f"STDERR: {stderr[:1000]}...", "DEBUG")
        
        return test_results
    
    def run_integration_tests_with_services(self) -> Dict[str, bool]:
        """Run integration tests with actual services running."""
        self.log("Running integration tests with live services...")
        
        # First, check if services are running
        success, stdout, stderr = self.run_command([
            "docker-compose", 
            "-f", "docker-compose.yml", 
            "-f", "docker-compose.phoenix.yml",
            "ps", "--format", "json"
        ], timeout=30)
        
        services_running = False
        if success:
            try:
                services = []
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        services.append(json.loads(line))
                
                running_services = [s['Service'] for s in services if 'running' in s.get('State', '').lower()]
                if 'verba' in running_services and 'phoenix' in running_services:
                    services_running = True
                    self.log("Found running services for integration tests", "SUCCESS")
            except:
                pass
        
        if not services_running:
            self.log("No running services found - integration tests will run in isolation", "WARN")
        
        # Integration tests that need service connectivity
        integration_tests = [
            "test_docker_compose_integration.py",
            "test_end_to_end_tracing_integration.py"
        ]
        
        test_results = {}
        
        for test_file in integration_tests:
            if services_running:
                # Get the network name for the running services
                network_name = "verba_ollama-docker"  # Default network name
                success, stdout, stderr = self.run_test_in_container(test_file, network=network_name)
            else:
                # Run in isolation
                success, stdout, stderr = self.run_test_in_container(test_file)
            
            test_results[test_file] = success
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {stdout[:1000]}...", "DEBUG")
                    self.log(f"STDERR: {stderr[:1000]}...", "DEBUG")
        
        return test_results
    
    def run_comprehensive_test_suite(self) -> bool:
        """Run the comprehensive test suite in containers."""
        self.log("Starting comprehensive containerized test suite...")
        
        # Build test image
        if not self.build_test_image():
            return False
        
        # Run unit tests
        unit_test_results = self.run_all_unit_tests()
        
        # Run integration tests
        integration_test_results = self.run_integration_tests_with_services()
        
        # Combine results
        all_test_results = {**unit_test_results, **integration_test_results}
        
        # Generate report
        self.generate_test_report(all_test_results)
        
        # Cleanup test image
        self.cleanup_test_image()
        
        # Return overall success
        return all(all_test_results.values())
    
    def generate_test_report(self, test_results: Dict[str, bool]) -> None:
        """Generate a comprehensive test report."""
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 80)
        print("🧪 CONTAINERIZED TEST REPORT")
        print("=" * 80)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n📋 Test Results by Category:")
        
        # Unit tests
        unit_tests = {k: v for k, v in test_results.items() if k not in [
            "test_docker_compose_integration.py", "test_end_to_end_tracing_integration.py"
        ]}
        unit_passed = sum(1 for result in unit_tests.values() if result)
        print(f"   Unit Tests: {unit_passed}/{len(unit_tests)} passed")
        
        # Integration tests
        integration_tests = {k: v for k, v in test_results.items() if k in [
            "test_docker_compose_integration.py", "test_end_to_end_tracing_integration.py"
        ]}
        integration_passed = sum(1 for result in integration_tests.values() if result)
        print(f"   Integration Tests: {integration_passed}/{len(integration_tests)} passed")
        
        # Property-based tests
        property_tests = {k: v for k, v in test_results.items() if k in self.property_test_files}
        property_passed = sum(1 for result in property_tests.values() if result)
        print(f"   Property Tests: {property_passed}/{len(property_tests)} passed")
        
        print(f"\n📋 Individual Test Results:")
        for test_file, result in sorted(test_results.items()):
            status = "✅ PASSED" if result else "❌ FAILED"
            test_type = ""
            if test_file in self.property_test_files:
                test_type = " (Property-Based)"
            elif test_file in ["test_docker_compose_integration.py", "test_end_to_end_tracing_integration.py"]:
                test_type = " (Integration)"
            
            print(f"   {test_file}{test_type}: {status}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_file, result in test_results.items():
                if not result:
                    print(f"   - {test_file}")
        
        print("\n" + "=" * 80)
        
        if passed_tests == total_tests:
            print("🎉 ALL CONTAINERIZED TESTS PASSED!")
            print("\n📝 Verified in Isolated Containers:")
            print("   ✅ Dependency verification")
            print("   ✅ Docker build verification")
            print("   ✅ Observability integration")
            print("   ✅ Error handling and resilience")
            print("   ✅ Property-based correctness tests")
            print("   ✅ End-to-end tracing integration")
        else:
            print("❌ SOME CONTAINERIZED TESTS FAILED!")
            print("\n🔧 Troubleshooting:")
            print("   1. Check individual test logs above")
            print("   2. Verify Docker environment and permissions")
            print("   3. Ensure sufficient resources for containers")
            print("   4. Check test dependencies and imports")
    
    def cleanup_test_image(self) -> None:
        """Clean up the test runner image."""
        self.log("Cleaning up test runner image...")
        
        success, stdout, stderr = self.run_command([
            "docker", "rmi", self.test_image_name
        ], timeout=60)
        
        if success:
            self.log("Test image cleaned up", "SUCCESS")
        else:
            self.log("Failed to clean up test image (may not exist)", "WARN")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Containerized Test Runner for Verba")
    parser.add_argument("--build-only", action="store_true",
                       help="Only build the test image and exit")
    parser.add_argument("--test-only", action="store_true",
                       help="Only run tests (assume image exists)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    runner = ContainerizedTestRunner(verbose=args.verbose)
    
    if args.build_only:
        runner.log("Build-only mode: creating test runner image...")
        success = runner.build_test_image()
        return 0 if success else 1
    
    if args.test_only:
        runner.log("Test-only mode: running tests with existing image...")
        # Run unit tests only
        test_results = runner.run_all_unit_tests()
        runner.generate_test_report(test_results)
        success = all(test_results.values())
        return 0 if success else 1
    
    # Run comprehensive test suite
    success = runner.run_comprehensive_test_suite()
    
    if success:
        runner.log("🎉 Comprehensive containerized test suite completed successfully!", "SUCCESS")
        return 0
    else:
        runner.log("❌ Comprehensive containerized test suite failed!", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())