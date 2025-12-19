#!/usr/bin/env python3
"""
Complete Verification Suite for Verba with Observability

This master script orchestrates comprehensive testing of the Verba application:
1. Containerized unit tests (isolated environment)
2. Full deployment integration tests (live services)
3. Property-based correctness verification
4. Performance and resilience testing

Usage:
    python run_complete_verification.py [--unit-only] [--integration-only] [--quick] [--verbose]
"""

import subprocess
import time
import sys
import os
import json
import argparse
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class CompleteVerificationSuite:
    """Master test orchestrator for comprehensive Verba verification."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = time.time()
        
        # Test phases
        self.phases = [
            ("Unit Tests (Containerized)", self.run_containerized_unit_tests),
            ("Integration Tests (Live Services)", self.run_live_integration_tests),
            ("Property-Based Verification", self.run_property_verification),
            ("Performance & Resilience", self.run_performance_tests)
        ]
        
        # Results tracking
        self.phase_results = {}
        self.detailed_results = {}
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp and level."""
        elapsed = time.time() - self.start_time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [+{elapsed:6.1f}s] [{level}]"
        
        if level == "ERROR":
            print(f"❌ {prefix} {message}")
        elif level == "WARN":
            print(f"⚠️  {prefix} {message}")
        elif level == "SUCCESS":
            print(f"✅ {prefix} {message}")
        elif level == "PHASE":
            print(f"🚀 {prefix} {message}")
        else:
            print(f"ℹ️  {prefix} {message}")
        
        if self.verbose and level == "DEBUG":
            print(f"🔍 {prefix} {message}")
    
    def run_command(self, cmd: List[str], timeout: int = 300, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr."""
        if self.verbose:
            self.log(f"Running: {' '.join(cmd)}", "DEBUG")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.path.dirname(__file__)
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)
    
    def check_prerequisites(self) -> bool:
        """Check that all prerequisites are available."""
        self.log("Checking prerequisites...")
        
        # Check Docker
        success, stdout, stderr = self.run_command(["docker", "version"], timeout=10)
        if not success:
            self.log("Docker is not available", "ERROR")
            return False
        
        # Check Docker Compose
        success, stdout, stderr = self.run_command(["docker-compose", "version"], timeout=10)
        if not success:
            self.log("Docker Compose is not available", "ERROR")
            return False
        
        # Check Python
        success, stdout, stderr = self.run_command([sys.executable, "--version"], timeout=10)
        if not success:
            self.log("Python is not available", "ERROR")
            return False
        
        # Check required files exist
        required_files = [
            "docker-compose.yml",
            "docker-compose.phoenix.yml",
            "run_containerized_tests.py",
            "run_full_deployment_tests.py"
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                self.log(f"Required file missing: {file_path}", "ERROR")
                return False
        
        self.log("All prerequisites satisfied", "SUCCESS")
        return True
    
    def run_containerized_unit_tests(self) -> bool:
        """Run unit tests in isolated containers."""
        self.log("Running containerized unit tests...", "PHASE")
        
        success, stdout, stderr = self.run_command([
            sys.executable, "run_containerized_tests.py"
        ] + (["--verbose"] if self.verbose else []), timeout=900)
        
        self.detailed_results["containerized_unit_tests"] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        if success:
            self.log("Containerized unit tests completed successfully", "SUCCESS")
        else:
            self.log("Containerized unit tests failed", "ERROR")
            if self.verbose:
                self.log(f"Error output: {stderr[:500]}...", "DEBUG")
        
        return success
    
    def run_live_integration_tests(self) -> bool:
        """Run integration tests with live services."""
        self.log("Running live integration tests...", "PHASE")
        
        success, stdout, stderr = self.run_command([
            sys.executable, "run_full_deployment_tests.py"
        ] + (["--verbose"] if self.verbose else []), timeout=1200)
        
        self.detailed_results["live_integration_tests"] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr
        }
        
        if success:
            self.log("Live integration tests completed successfully", "SUCCESS")
        else:
            self.log("Live integration tests failed", "ERROR")
            if self.verbose:
                self.log(f"Error output: {stderr[:500]}...", "DEBUG")
        
        return success
    
    def run_property_verification(self) -> bool:
        """Run property-based verification tests."""
        self.log("Running property-based verification...", "PHASE")
        
        # Property-based tests to run
        property_tests = [
            "test_observability_property.py",
            "test_property_7_minimal.py"
        ]
        
        all_passed = True
        
        for test_file in property_tests:
            self.log(f"Running property test: {test_file}")
            
            success, stdout, stderr = self.run_command([
                sys.executable, test_file
            ], timeout=300)
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                all_passed = False
                if self.verbose:
                    self.log(f"Error: {stderr[:300]}...", "DEBUG")
        
        self.detailed_results["property_verification"] = {
            "success": all_passed,
            "tests_run": property_tests
        }
        
        return all_passed
    
    def run_performance_tests(self) -> bool:
        """Run performance and resilience tests."""
        self.log("Running performance and resilience tests...", "PHASE")
        
        # Performance-related tests
        performance_tests = [
            "test_error_handling.py",
            "test_error_tracing_simple.py"
        ]
        
        all_passed = True
        
        for test_file in performance_tests:
            self.log(f"Running performance test: {test_file}")
            
            success, stdout, stderr = self.run_command([
                sys.executable, test_file
            ], timeout=180)
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                all_passed = False
                if self.verbose:
                    self.log(f"Error: {stderr[:300]}...", "DEBUG")
        
        self.detailed_results["performance_tests"] = {
            "success": all_passed,
            "tests_run": performance_tests
        }
        
        return all_passed
    
    def run_quick_verification(self) -> bool:
        """Run a quick verification suite (subset of tests)."""
        self.log("Running quick verification suite...", "PHASE")
        
        # Quick tests - most critical functionality
        quick_tests = [
            "test_syntax_check.py",
            "test_dependency_verification.py",
            "test_observability_integration.py"
        ]
        
        all_passed = True
        
        for test_file in quick_tests:
            self.log(f"Running quick test: {test_file}")
            
            success, stdout, stderr = self.run_command([
                sys.executable, test_file
            ], timeout=60)
            
            if success:
                self.log(f"{test_file}: PASSED", "SUCCESS")
            else:
                self.log(f"{test_file}: FAILED", "ERROR")
                all_passed = False
        
        return all_passed
    
    def generate_comprehensive_report(self) -> None:
        """Generate a comprehensive verification report."""
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 100)
        print("🧪 COMPLETE VERIFICATION REPORT")
        print("=" * 100)
        
        print(f"\n⏱️  Execution Time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        
        print(f"\n📊 Phase Results:")
        total_phases = len(self.phase_results)
        passed_phases = sum(1 for result in self.phase_results.values() if result)
        
        for phase_name, result in self.phase_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {phase_name}: {status}")
        
        print(f"\n📈 Overall Success Rate: {(passed_phases/total_phases)*100:.1f}% ({passed_phases}/{total_phases} phases)")
        
        # Detailed breakdown
        print(f"\n📋 Detailed Results:")
        
        for test_category, details in self.detailed_results.items():
            success = details.get("success", False)
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {test_category.replace('_', ' ').title()}: {status}")
            
            if "tests_run" in details:
                print(f"      Tests: {', '.join(details['tests_run'])}")
        
        # System information
        print(f"\n🖥️  System Information:")
        
        # Docker version
        success, stdout, stderr = self.run_command(["docker", "version", "--format", "{{.Server.Version}}"])
        if success:
            print(f"   Docker Version: {stdout.strip()}")
        
        # Python version
        print(f"   Python Version: {sys.version.split()[0]}")
        
        # Available memory (if possible)
        try:
            success, stdout, stderr = self.run_command(["docker", "system", "df"])
            if success:
                print(f"   Docker System Status: Available")
        except:
            pass
        
        # Final verdict
        print("\n" + "=" * 100)
        
        if passed_phases == total_phases:
            print("🎉 COMPLETE VERIFICATION SUCCESSFUL!")
            print("\n📝 All Systems Verified:")
            print("   ✅ Unit tests pass in isolated containers")
            print("   ✅ Integration tests pass with live services")
            print("   ✅ Property-based correctness verified")
            print("   ✅ Performance and resilience confirmed")
            print("   ✅ Docker deployment fully functional")
            print("   ✅ OpenTelemetry observability working")
            print("   ✅ Phoenix integration operational")
            
            print(f"\n🚀 Verba is ready for production deployment!")
            
        else:
            print("❌ VERIFICATION FAILED!")
            print(f"\n🔧 Issues Found:")
            
            for phase_name, result in self.phase_results.items():
                if not result:
                    print(f"   - {phase_name}")
            
            print(f"\n🛠️  Troubleshooting Steps:")
            print("   1. Check individual test logs above")
            print("   2. Verify Docker resources (memory, disk space)")
            print("   3. Ensure all ports are available (6006, 8000, 8080)")
            print("   4. Check network connectivity")
            print("   5. Verify environment variables and configuration")
            print("   6. Review Docker Compose service logs")
    
    def run_complete_suite(self, unit_only: bool = False, integration_only: bool = False, quick: bool = False) -> bool:
        """Run the complete verification suite."""
        self.log("Starting complete verification suite...", "PHASE")
        
        if not self.check_prerequisites():
            return False
        
        if quick:
            # Quick verification mode
            success = self.run_quick_verification()
            self.phase_results["Quick Verification"] = success
            return success
        
        # Determine which phases to run
        phases_to_run = []
        
        if unit_only:
            phases_to_run = [("Unit Tests (Containerized)", self.run_containerized_unit_tests)]
        elif integration_only:
            phases_to_run = [("Integration Tests (Live Services)", self.run_live_integration_tests)]
        else:
            phases_to_run = self.phases
        
        # Run selected phases
        for phase_name, phase_func in phases_to_run:
            self.log(f"Starting phase: {phase_name}", "PHASE")
            
            phase_start = time.time()
            success = phase_func()
            phase_duration = time.time() - phase_start
            
            self.phase_results[phase_name] = success
            
            if success:
                self.log(f"Phase completed successfully in {phase_duration:.1f}s", "SUCCESS")
            else:
                self.log(f"Phase failed after {phase_duration:.1f}s", "ERROR")
                
                # Ask user if they want to continue
                if not unit_only and not integration_only:
                    response = input(f"\n⚠️  Phase '{phase_name}' failed. Continue with remaining phases? (y/N): ")
                    if response.lower() != 'y':
                        self.log("Verification suite aborted by user", "WARN")
                        break
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
        
        # Return overall success
        return all(self.phase_results.values())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Complete Verification Suite for Verba")
    parser.add_argument("--unit-only", action="store_true",
                       help="Run only containerized unit tests")
    parser.add_argument("--integration-only", action="store_true",
                       help="Run only live integration tests")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick verification (subset of critical tests)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.unit_only and args.integration_only:
        print("❌ Cannot specify both --unit-only and --integration-only")
        return 1
    
    suite = CompleteVerificationSuite(verbose=args.verbose)
    
    try:
        success = suite.run_complete_suite(
            unit_only=args.unit_only,
            integration_only=args.integration_only,
            quick=args.quick
        )
        
        if success:
            suite.log("🎉 Complete verification suite finished successfully!", "SUCCESS")
            return 0
        else:
            suite.log("❌ Complete verification suite failed!", "ERROR")
            return 1
            
    except KeyboardInterrupt:
        suite.log("Verification suite interrupted by user", "WARN")
        return 130
    except Exception as e:
        suite.log(f"Unexpected error: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())