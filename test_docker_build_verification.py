#!/usr/bin/env python3
"""
Docker build verification tests.

This module tests that the Dockerfile includes all required observability packages
and that the build process would succeed.

Requirements tested: 3.1, 3.2, 3.3, 3.4, 3.5
"""
import os
import re
import unittest
from typing import List, Set


class TestDockerBuildVerification(unittest.TestCase):
    """Test suite for Docker build verification."""
    
    def setUp(self):
        """Set up test environment."""
        self.dockerfile_path = os.path.join(os.path.dirname(__file__), 'Dockerfile')
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        self.assertTrue(os.path.exists(self.dockerfile_path), 
                       "Dockerfile should exist in the Verba directory")
    
    def test_dockerfile_includes_observability_packages(self):
        """
        Test that Dockerfile includes all required observability packages.
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        required_packages = {
            'arize-phoenix-otel',
            'opentelemetry-sdk',
            'opentelemetry-exporter-otlp',
            'openinference-instrumentation-langchain',
            'opentelemetry-instrumentation-requests'
        }
        
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Find all pip install commands
        pip_install_pattern = r'RUN\s+pip\s+install[^\\]*(?:\\[^\\]*)*'
        pip_commands = re.findall(pip_install_pattern, dockerfile_content, re.MULTILINE)
        
        # Extract all package names from pip install commands
        installed_packages = set()
        for command in pip_commands:
            # Remove RUN pip install and extract package names
            packages_line = re.sub(r'RUN\s+pip\s+install\s+[^a-zA-Z-]*', '', command)
            # Split by whitespace and backslashes, filter out flags
            packages = re.split(r'[\s\\]+', packages_line)
            for package in packages:
                package = package.strip()
                if package and not package.startswith('-'):
                    installed_packages.add(package)
        
        # Check that all required packages are included
        for package in required_packages:
            with self.subTest(package=package):
                self.assertIn(package, installed_packages,
                             f"Package {package} should be installed in Dockerfile")
    
    def test_dockerfile_python_version(self):
        """
        Test that Dockerfile uses compatible Python version.
        Requirements: 3.1, 3.2
        """
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Check for Python version in FROM statement
        from_pattern = r'FROM\s+python:(\d+\.\d+)'
        match = re.search(from_pattern, dockerfile_content)
        
        self.assertIsNotNone(match, "Dockerfile should specify Python version")
        
        python_version = match.group(1)
        major, minor = map(int, python_version.split('.'))
        
        # OpenTelemetry requires Python 3.8+, but we recommend 3.11+
        self.assertGreaterEqual(major, 3, "Python major version should be 3 or higher")
        self.assertGreaterEqual(minor, 8, "Python minor version should be 8 or higher for OpenTelemetry")
    
    def test_dockerfile_package_installation_order(self):
        """
        Test that observability packages are installed after base packages.
        Requirements: 3.1, 3.2, 3.3
        """
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_lines = f.readlines()
        
        # Find the line numbers of different pip install commands
        base_install_line = None
        observability_install_line = None
        
        for i, line in enumerate(dockerfile_lines):
            if 'pip install' in line and '.' in line:
                # This is likely the base package installation
                base_install_line = i
            elif 'pip install' in line and 'arize-phoenix-otel' in line:
                # This is the observability packages installation
                observability_install_line = i
        
        if base_install_line is not None and observability_install_line is not None:
            self.assertLess(base_install_line, observability_install_line,
                           "Base packages should be installed before observability packages")
    
    def test_dockerfile_no_cache_flag(self):
        """
        Test that observability packages use --no-cache-dir flag.
        Requirements: 3.4, 3.5
        """
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Find the observability packages installation command (multiline)
        # Look for the pip install command that includes arize-phoenix-otel
        observability_pattern = r'RUN\s+pip\s+install\s+--no-cache-dir[^R]*arize-phoenix-otel'
        match = re.search(observability_pattern, dockerfile_content, re.MULTILINE | re.DOTALL)
        
        self.assertIsNotNone(match, "Should find observability packages installation with --no-cache-dir")
        
        install_command = match.group(0)
        self.assertIn('--no-cache-dir', install_command,
                     "Observability packages should use --no-cache-dir flag")
        self.assertIn('arize-phoenix-otel', install_command,
                     "Should install arize-phoenix-otel package")
    
    def test_dockerfile_exposes_correct_port(self):
        """
        Test that Dockerfile exposes the correct port for Verba.
        Requirements: 3.1
        """
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Check for EXPOSE statement
        expose_pattern = r'EXPOSE\s+(\d+)'
        match = re.search(expose_pattern, dockerfile_content)
        
        self.assertIsNotNone(match, "Dockerfile should expose a port")
        
        exposed_port = int(match.group(1))
        self.assertEqual(exposed_port, 8000, "Dockerfile should expose port 8000")
    
    def test_dockerfile_cmd_configuration(self):
        """
        Test that Dockerfile CMD is properly configured.
        Requirements: 3.1
        """
        with open(self.dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Check for CMD statement
        cmd_pattern = r'CMD\s+\[(.*?)\]'
        match = re.search(cmd_pattern, dockerfile_content)
        
        self.assertIsNotNone(match, "Dockerfile should have CMD statement")
        
        cmd_content = match.group(1)
        
        # Should contain verba start command
        self.assertIn('"verba"', cmd_content, "CMD should start verba")
        self.assertIn('"start"', cmd_content, "CMD should use start command")
        self.assertIn('"--port"', cmd_content, "CMD should specify port")
        self.assertIn('"8000"', cmd_content, "CMD should use port 8000")
        self.assertIn('"--host"', cmd_content, "CMD should specify host")
        self.assertIn('"0.0.0.0"', cmd_content, "CMD should bind to all interfaces")


class TestDockerComposeConfiguration(unittest.TestCase):
    """Test Docker Compose configuration for observability."""
    
    def setUp(self):
        """Set up test environment."""
        self.docker_compose_path = os.path.join(os.path.dirname(__file__), 'docker-compose.phoenix.yml')
    
    def test_docker_compose_phoenix_file_exists(self):
        """Test that docker-compose.phoenix.yml exists."""
        self.assertTrue(os.path.exists(self.docker_compose_path),
                       "docker-compose.phoenix.yml should exist")
    
    def test_docker_compose_includes_phoenix_service(self):
        """
        Test that docker-compose includes Phoenix service configuration.
        Requirements: 3.1, 3.4
        """
        if not os.path.exists(self.docker_compose_path):
            self.skipTest("docker-compose.phoenix.yml not found")
        
        with open(self.docker_compose_path, 'r') as f:
            compose_content = f.read()
        
        # Check for Phoenix service
        self.assertIn('phoenix:', compose_content, "Should include Phoenix service")
        
        # Check for Phoenix image
        self.assertIn('arizephoenix/phoenix', compose_content, 
                     "Should use official Phoenix image")
        
        # Check for port mappings
        self.assertIn('6006:6006', compose_content, "Should expose Phoenix UI port")
        self.assertIn('4317:4317', compose_content, "Should expose OTLP gRPC port")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)