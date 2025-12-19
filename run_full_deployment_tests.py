#!/usr/bin/env python3
"""
Full Deployment Test Runner for Verba with Observability

This script:
1. Starts the complete Docker Compose stack (Verba + Weaviate + Phoenix)
2. Runs all tests in a temporary Docker container to verify deployment
3. Provides comprehensive verification of the observability integration

Usage:
    python run_full_deployment_tests.py [--cleanup-only] [--no-cleanup] [--verbose]
"""

import subprocess
import time
import sys
import os
import json
import argparse
from typing import List, Dict, Any, Tuple, Optional
from contextlib import contextmanager


class FullDeploymentTestRunner:
    """Comprehensive test runner for full Verba deployment with observability."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.base_compose_file = "docker-compose.yml"
        self.phoenix_compose_file = "docker-compose.phoenix.yml"
        self.test_timeout = 300  # 5 minutes for full deployment
        self.service_health_timeout = 180  # 3 minutes for service health
        
        # All test files to run in the deployment
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
            "test_error_tracing_simple.py"
        ]
        
        # Services that need to be healthy before running tests
        self.required_services = ["phoenix", "weaviate", "verba"]
        
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
    
    def run_command(self, cmd: List[str], timeout: int = 30, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
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
                self.log(f"STDERR: {result.stderr}", "DEBUG")
            
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s", "ERROR")
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            self.log(f"Command execution error: {e}", "ERROR")
            return False, "", str(e)
    
    def check_docker_availability(self) -> bool:
        """Check if Docker and Docker Compose are available."""
        self.log("Checking Docker availability...")
        
        # Check Docker
        success, stdout, stderr = self.run_command(["docker", "version"], timeout=10)
        if not success:
            self.log("Docker is not available or not running", "ERROR")
            return False
        
        # Check Docker Compose
        success, stdout, stderr = self.run_command(["docker-compose", "version"], timeout=10)
        if not success:
            self.log("Docker Compose is not available", "ERROR")
            return False
        
        self.log("Docker and Docker Compose are available", "SUCCESS")
        return True
    
    def cleanup_existing_deployment(self) -> bool:
        """Clean up any existing deployment."""
        self.log("Cleaning up existing deployment...")
        
        # Stop and remove containers
        success, stdout, stderr = self.run_command([
            "docker-compose", 
            "-f", self.base_compose_file, 
            "-f", self.phoenix_compose_file,
            "down", "--remove-orphans", "--volumes"
        ], timeout=120)
        
        if not success:
            self.log(f"Cleanup failed: {stderr}", "WARN")
            return False
        
        # Remove any dangling containers
        self.run_command(["docker", "system", "prune", "-f"], timeout=60)
        
        self.log("Cleanup completed", "SUCCESS")
        return True
    
    def wait_for_service_health(self, service_name: str, max_wait: int = 180) -> bool:
        """Wait for a service to become healthy."""
        self.log(f"Waiting for {service_name} to become healthy (max {max_wait}s)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            success, stdout, stderr = self.run_command([
                "docker-compose", 
                "-f", self.base_compose_file, 
                "-f", self.phoenix_compose_file,
                "ps", "--format", "json"
            ], timeout=30)
            
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
                            
                            if health == 'healthy':
                                self.log(f"{service_name} is healthy", "SUCCESS")
                                return True
                            elif state == 'running' and not health:
                                # Service is running but has no health check
                                self.log(f"{service_name} is running (no health check)", "SUCCESS")
                                return True
                            elif 'exited' in state.lower() or 'dead' in state.lower():
                                self.log(f"{service_name} failed to start: {state}", "ERROR")
                                return False
                            else:
                                if self.verbose:
                                    self.log(f"{service_name} status: {state} (health: {health})", "DEBUG")
                
                except json.JSONDecodeError as e:
                    if self.verbose:
                        self.log(f"Failed to parse service status: {e}", "DEBUG")
            
            time.sleep(10)
        
        self.log(f"{service_name} did not become healthy within {max_wait}s", "ERROR")
        return False
    
    def start_full_deployment(self) -> bool:
        """Start the complete Docker Compose deployment."""
        self.log("Starting full Docker Compose deployment...")
        
        # Build and start services
        success, stdout, stderr = self.run_command([
            "docker-compose", 
            "-f", self.base_compose_file, 
            "-f", self.phoenix_compose_file,
            "up", "-d", "--build"
        ], timeout=300)
        
        if not success:
            self.log(f"Failed to start deployment: {stderr}", "ERROR")
            return False
        
        self.log("Docker Compose services started", "SUCCESS")
        
        # Wait for all required services to be healthy
        for service in self.required_services:
            if not self.wait_for_service_health(service, self.service_health_timeout):
                self.log(f"Service {service} failed to become healthy", "ERROR")
                return False
        
        self.log("All services are healthy and ready", "SUCCESS")
        return True
    
    def run_test_in_container(self, test_file: str) -> Tuple[bool, str, str]:
        """Run a specific test file inside the Verba container."""
        self.log(f"Running test: {test_file}")
        
        # Copy test file to container and run it
        success, stdout, stderr = self.run_command([
            "docker-compose", 
            "-f", self.base_compose_file, 
            "-f", self.phoenix_compose_file,
            "exec", "-T", "verba", "python", f"/Verba/{test_file}"
        ], timeout=120)
        
        return success, stdout, stderr
    
    def run_all_tests_in_deployment(self) -> Dict[str, bool]:
        """Run all tests inside the deployed containers."""
        self.log("Running all tests in deployment...")
        
        test_results = {}
        
        for test_file in self.test_files:
            self.log(f"Executing {test_file}...")
            
            success, stdout, stderr = self.run_test_in_container(test_file)
            test_results[test_file] = success
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {stdout}", "DEBUG")
                    self.log(f"STDERR: {stderr}", "DEBUG")
        
        return test_results
    
    def run_integration_verification(self) -> bool:
        """Run integration verification tests."""
        self.log("Running integration verification...")
        
        # Test Phoenix UI accessibility
        success, stdout, stderr = self.run_command([
            "curl", "-f", "-s", "http://localhost:6006"
        ], timeout=30)
        
        if success:
            self.log("Phoenix UI is accessible", "SUCCESS")
        else:
            self.log("Phoenix UI is not accessible", "WARN")
        
        # Test Verba API accessibility
        success, stdout, stderr = self.run_command([
            "curl", "-f", "-s", "http://localhost:8000"
        ], timeout=30)
        
        if success:
            self.log("Verba API is accessible", "SUCCESS")
        else:
            self.log("Verba API is not accessible", "ERROR")
            return False
        
        # Test Weaviate accessibility
        success, stdout, stderr = self.run_command([
            "curl", "-f", "-s", "http://localhost:8080/v1/.well-known/ready"
        ], timeout=30)
        
        if success:
            self.log("Weaviate is accessible", "SUCCESS")
        else:
            self.log("Weaviate is not accessible", "ERROR")
            return False
        
        # Check service logs for errors
        self.log("Checking service logs for errors...")
        
        for service in self.required_services:
            success, stdout, stderr = self.run_command([
                "docker-compose", 
                "-f", self.base_compose_file, 
                "-f", self.phoenix_compose_file,
                "logs", "--tail", "50", service
            ], timeout=30)
            
            if success:
                # Look for error patterns in logs
                error_patterns = ["ERROR", "FATAL", "Exception", "Traceback"]
                log_lines = stdout.lower()
                
                errors_found = []
                for pattern in error_patterns:
                    if pattern.lower() in log_lines:
                        errors_found.append(pattern)
                
                if errors_found:
                    self.log(f"{service} logs contain potential errors: {errors_found}", "WARN")
                else:
                    self.log(f"{service} logs look clean", "SUCCESS")
        
        return True
    
    def generate_test_report(self, test_results: Dict[str, bool], integration_success: bool) -> None:
        """Generate a comprehensive test report."""
        self.log("Generating test report...")
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 80)
        print("🧪 FULL DEPLOYMENT TEST REPORT")
        print("=" * 80)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🔧 Integration Verification: {'✅ PASSED' if integration_success else '❌ FAILED'}")
        
        print(f"\n📋 Individual Test Results:")
        for test_file, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {test_file}: {status}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_file, result in test_results.items():
                if not result:
                    print(f"   - {test_file}")
        
        print(f"\n🐳 Docker Services Status:")
        success, stdout, stderr = self.run_command([
            "docker-compose", 
            "-f", self.base_compose_file, 
            "-f", self.phoenix_compose_file,
            "ps"
        ], timeout=30)
        
        if success:
            print(stdout)
        
        print("\n" + "=" * 80)
        
        if passed_tests == total_tests and integration_success:
            print("🎉 ALL TESTS PASSED! Deployment is fully functional.")
            print("\n📝 Verified Components:")
            print("   ✅ Docker Compose deployment")
            print("   ✅ Phoenix observability service")
            print("   ✅ Weaviate vector database")
            print("   ✅ Verba RAG application")
            print("   ✅ OpenTelemetry tracing integration")
            print("   ✅ Error handling and resilience")
            print("   ✅ End-to-end RAG pipeline")
        else:
            print("❌ SOME TESTS FAILED! Check the report above for details.")
            print("\n🔧 Troubleshooting:")
            print("   1. Check Docker logs: docker-compose logs <service-name>")
            print("   2. Verify port availability: 6006 (Phoenix), 8000 (Verba), 8080 (Weaviate)")
            print("   3. Ensure sufficient Docker resources (memory, CPU)")
            print("   4. Check network connectivity between services")
    
    @contextmanager
    def deployment_context(self, cleanup: bool = True):
        """Context manager for deployment lifecycle."""
        try:
            # Start deployment
            if not self.start_full_deployment():
                raise Exception("Failed to start deployment")
            
            yield
            
        finally:
            if cleanup:
                self.log("Cleaning up deployment...")
                self.cleanup_existing_deployment()
    
    def run_full_test_suite(self, cleanup: bool = True) -> bool:
        """Run the complete test suite against the full deployment."""
        self.log("Starting full deployment test suite...")
        
        if not self.check_docker_availability():
            return False
        
        # Initial cleanup
        self.cleanup_existing_deployment()
        
        try:
            with self.deployment_context(cleanup=cleanup):
                # Run integration verification
                integration_success = self.run_integration_verification()
                
                # Run all tests in deployment
                test_results = self.run_all_tests_in_deployment()
                
                # Generate report
                self.generate_test_report(test_results, integration_success)
                
                # Determine overall success
                all_tests_passed = all(test_results.values())
                overall_success = all_tests_passed and integration_success
                
                return overall_success
                
        except Exception as e:
            self.log(f"Test suite execution failed: {e}", "ERROR")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Full Deployment Test Runner for Verba")
    parser.add_argument("--cleanup-only", action="store_true", 
                       help="Only cleanup existing deployment and exit")
    parser.add_argument("--no-cleanup", action="store_true",
                       help="Don't cleanup deployment after tests (for debugging)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    runner = FullDeploymentTestRunner(verbose=args.verbose)
    
    if args.cleanup_only:
        runner.log("Cleanup-only mode: removing existing deployment...")
        success = runner.cleanup_existing_deployment()
        return 0 if success else 1
    
    # Run full test suite
    success = runner.run_full_test_suite(cleanup=not args.no_cleanup)
    
    if success:
        runner.log("🎉 Full deployment test suite completed successfully!", "SUCCESS")
        return 0
    else:
        runner.log("❌ Full deployment test suite failed!", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())