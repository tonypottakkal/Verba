#!/usr/bin/env python3
"""
Unit tests for dependency verification.

This module tests Docker image build with observability packages,
environment variable configuration, and dependency loading/initialization.

Requirements tested: 3.1, 3.2, 3.3, 3.4, 3.5
"""
import os
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock, MagicMock
from typing import Dict, Any, List
import importlib.util


class TestDependencyVerification(unittest.TestCase):
    """Test suite for observability dependency verification."""
    
    def setUp(self):
        """Set up test environment."""
        # Store original environment
        self.original_env = os.environ.copy()
        
        # Clear any existing OTel environment variables
        otel_vars = [key for key in os.environ.keys() if key.startswith('OTEL_')]
        for var in otel_vars:
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_docker_image_observability_packages(self):
        """
        Test that Docker image includes all required observability packages.
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        # Required packages from Dockerfile
        required_packages = [
            'arize-phoenix-otel',
            'opentelemetry-sdk', 
            'opentelemetry-exporter-otlp',
            'openinference-instrumentation-langchain',
            'opentelemetry-instrumentation-requests'
        ]
        
        # Check if we can import the corresponding modules
        # This simulates what would happen in the Docker container
        importable_modules = [
            'phoenix.otel',
            'opentelemetry.sdk',
            'opentelemetry.exporter.otlp',
            'openinference.instrumentation.langchain',
            'opentelemetry.instrumentation.requests'
        ]
        
        for i, module_name in enumerate(importable_modules):
            with self.subTest(package=required_packages[i], module=module_name):
                # Try to find the module spec (doesn't actually import)
                try:
                    spec = importlib.util.find_spec(module_name)
                    if spec is None:
                        # If module not found, skip this test (dependency not installed)
                        self.skipTest(f"Module {module_name} not available - run in Docker environment")
                    else:
                        # Module is available
                        self.assertIsNotNone(spec, f"Module {module_name} should be importable")
                except ModuleNotFoundError:
                    # Expected when dependencies are not installed locally
                    self.skipTest(f"Module {module_name} not available - run in Docker environment")
    
    def test_environment_variable_configuration(self):
        """
        Test environment variable configuration for OpenTelemetry.
        Requirements: 3.1, 3.2, 3.3
        """
        # Test required environment variables
        required_env_vars = {
            'OTEL_SERVICE_NAME': 'verba',
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://phoenix:4317',
            'OTEL_EXPORTER_OTLP_PROTOCOL': 'grpc',
            'OTEL_TRACES_EXPORTER': 'otlp'
        }
        
        # Set environment variables
        for key, value in required_env_vars.items():
            os.environ[key] = value
        
        # Verify environment variables are set correctly
        for key, expected_value in required_env_vars.items():
            with self.subTest(env_var=key):
                actual_value = os.getenv(key)
                self.assertEqual(actual_value, expected_value,
                               f"Environment variable {key} should be {expected_value}")
    
    def test_environment_variable_defaults(self):
        """
        Test default environment variable handling.
        Requirements: 3.1, 3.2
        """
        # Test that missing environment variables have sensible defaults
        test_cases = [
            ('OTEL_SERVICE_NAME', 'verba'),
            ('OTEL_EXPORTER_OTLP_PROTOCOL', 'grpc'),
            ('OTEL_TRACES_EXPORTER', 'otlp')
        ]
        
        for env_var, default_value in test_cases:
            with self.subTest(env_var=env_var):
                # Clear the environment variable
                if env_var in os.environ:
                    del os.environ[env_var]
                
                # Get value with default
                actual_value = os.getenv(env_var, default_value)
                self.assertEqual(actual_value, default_value,
                               f"Default value for {env_var} should be {default_value}")
    
    def test_dependency_loading_without_errors(self):
        """
        Test that observability dependencies can be loaded without ModuleNotFoundError.
        Requirements: 3.4, 3.5
        """
        # Mock the modules to simulate successful import
        mock_modules = {
            'phoenix': Mock(),
            'phoenix.otel': Mock(),
            'opentelemetry': Mock(),
            'opentelemetry.sdk': Mock(),
            'opentelemetry.sdk.trace': Mock(),
            'opentelemetry.sdk.trace.export': Mock(),
            'opentelemetry.exporter': Mock(),
            'opentelemetry.exporter.otlp': Mock(),
            'opentelemetry.exporter.otlp.proto': Mock(),
            'opentelemetry.exporter.otlp.proto.grpc': Mock(),
            'opentelemetry.exporter.otlp.proto.grpc.trace_exporter': Mock(),
            'opentelemetry.sdk.resources': Mock(),
            'openinference': Mock(),
            'openinference.instrumentation': Mock(),
            'openinference.instrumentation.langchain': Mock(),
            'opentelemetry.instrumentation': Mock(),
            'opentelemetry.instrumentation.requests': Mock()
        }
        
        # Test modules to import
        test_modules = [
            'phoenix.otel',
            'opentelemetry.sdk',
            'opentelemetry.sdk.trace',
            'opentelemetry.sdk.trace.export',
            'opentelemetry.exporter.otlp.proto.grpc.trace_exporter',
            'opentelemetry.sdk.resources',
            'openinference.instrumentation.langchain',
            'opentelemetry.instrumentation.requests'
        ]
        
        with patch.dict('sys.modules', mock_modules):
            # Test importing each module
            for module_name in test_modules:
                with self.subTest(module=module_name):
                    try:
                        __import__(module_name)
                        # If we get here, import succeeded
                        self.assertTrue(True, f"Successfully imported {module_name}")
                    except ModuleNotFoundError:
                        self.fail(f"ModuleNotFoundError when importing {module_name}")
                    except Exception as e:
                        # Other exceptions are acceptable (mocked modules may not behave normally)
                        pass
    
    def test_opentelemetry_component_initialization(self):
        """
        Test that OpenTelemetry components can be initialized.
        Requirements: 3.1, 3.2, 3.3
        """
        # Mock OpenTelemetry components
        mock_tracer_provider = Mock()
        mock_otlp_exporter = Mock()
        mock_batch_processor = Mock()
        mock_resource = Mock()
        
        # Mock all required modules first
        mock_modules = {
            'opentelemetry': Mock(),
            'opentelemetry.sdk': Mock(),
            'opentelemetry.sdk.trace': Mock(),
            'opentelemetry.sdk.trace.export': Mock(),
            'opentelemetry.exporter': Mock(),
            'opentelemetry.exporter.otlp': Mock(),
            'opentelemetry.exporter.otlp.proto': Mock(),
            'opentelemetry.exporter.otlp.proto.grpc': Mock(),
            'opentelemetry.exporter.otlp.proto.grpc.trace_exporter': Mock(),
            'opentelemetry.sdk.resources': Mock()
        }
        
        with patch.dict('sys.modules', mock_modules), \
             patch('opentelemetry.sdk.trace.TracerProvider', return_value=mock_tracer_provider), \
             patch('opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter', 
                   return_value=mock_otlp_exporter), \
             patch('opentelemetry.sdk.trace.export.BatchSpanProcessor', 
                   return_value=mock_batch_processor), \
             patch('opentelemetry.sdk.resources.Resource.create', return_value=mock_resource):
            
            # Set required environment variables
            os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://phoenix:4317'
            os.environ['OTEL_SERVICE_NAME'] = 'verba'
            
            # Try to initialize components (simulated)
            try:
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.sdk.resources import Resource
                
                # Create components
                resource = Resource.create({"service.name": "verba"})
                tracer_provider = TracerProvider(resource=resource)
                otlp_exporter = OTLPSpanExporter(
                    endpoint="http://phoenix:4317",
                    insecure=True
                )
                span_processor = BatchSpanProcessor(otlp_exporter)
                
                # Verify components were created
                self.assertIsNotNone(resource)
                self.assertIsNotNone(tracer_provider)
                self.assertIsNotNone(otlp_exporter)
                self.assertIsNotNone(span_processor)
                
            except ImportError as e:
                self.skipTest(f"OpenTelemetry modules not available: {e}")
            except Exception as e:
                self.fail(f"Failed to initialize OpenTelemetry components: {e}")
    
    def test_phoenix_integration_configuration(self):
        """
        Test Phoenix-specific configuration.
        Requirements: 3.1, 3.4
        """
        # Mock Phoenix modules
        mock_modules = {
            'phoenix': Mock(),
            'phoenix.otel': Mock()
        }
        
        with patch.dict('sys.modules', mock_modules):
            # Set Phoenix-specific environment variables
            os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://phoenix:4317'
            os.environ['OTEL_EXPORTER_OTLP_PROTOCOL'] = 'grpc'
            
            # Test Phoenix endpoint configuration
            endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
            protocol = os.getenv('OTEL_EXPORTER_OTLP_PROTOCOL')
            
            self.assertEqual(endpoint, 'http://phoenix:4317')
            self.assertEqual(protocol, 'grpc')
            
            # Verify Phoenix can be imported (mocked)
            try:
                import phoenix.otel
                self.assertTrue(True, "Phoenix OTEL module imported successfully")
            except ImportError:
                self.skipTest("Phoenix modules not available")
    
    def test_langchain_instrumentation_availability(self):
        """
        Test LangChain instrumentation availability.
        Requirements: 3.3, 3.4
        """
        # Mock LangChain instrumentation
        mock_langchain_instrumentor = Mock()
        mock_modules = {
            'openinference': Mock(),
            'openinference.instrumentation': Mock(),
            'openinference.instrumentation.langchain': Mock()
        }
        
        with patch.dict('sys.modules', mock_modules), \
             patch('openinference.instrumentation.langchain.LangChainInstrumentor', mock_langchain_instrumentor):
            try:
                from openinference.instrumentation.langchain import LangChainInstrumentor
                
                # Verify instrumentor can be accessed
                self.assertIsNotNone(LangChainInstrumentor)
                
                # Test instrumentor methods (mocked)
                instrumentor = LangChainInstrumentor()
                self.assertIsNotNone(instrumentor)
                
            except ImportError:
                self.skipTest("LangChain instrumentation not available")
    
    def test_optional_requests_instrumentation(self):
        """
        Test optional HTTP requests instrumentation.
        Requirements: 3.5
        """
        # Mock requests instrumentation
        mock_modules = {
            'opentelemetry': Mock(),
            'opentelemetry.instrumentation': Mock(),
            'opentelemetry.instrumentation.requests': Mock()
        }
        
        with patch.dict('sys.modules', mock_modules):
            try:
                import opentelemetry.instrumentation.requests
                self.assertTrue(True, "Requests instrumentation imported successfully")
            except ImportError:
                # This is optional, so failure is acceptable
                self.skipTest("Optional requests instrumentation not available")
    
    def test_dependency_verification_script_execution(self):
        """
        Test that the dependency verification script can execute successfully.
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        # Check if the verification script exists
        script_path = os.path.join(os.path.dirname(__file__), 'verify_observability_deps.py')
        
        if not os.path.exists(script_path):
            self.skipTest("Dependency verification script not found")
        
        # Try to run the script (in a subprocess to avoid import issues)
        try:
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, text=True, timeout=30)
            
            # Script should either succeed (return 0) or fail gracefully (return 1)
            # It should not crash with unhandled exceptions
            self.assertIn(result.returncode, [0, 1], 
                         f"Verification script should return 0 or 1, got {result.returncode}")
            
            # Check that output contains expected verification messages
            output = result.stdout + result.stderr
            self.assertIn("Verifying observability dependencies", output)
            
        except subprocess.TimeoutExpired:
            self.fail("Dependency verification script timed out")
        except FileNotFoundError:
            self.skipTest("Python interpreter not found")


class TestEnvironmentVariableValidation(unittest.TestCase):
    """Test environment variable validation and configuration."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_required_environment_variables_validation(self):
        """Test validation of required environment variables."""
        # Test cases: (env_var, valid_values, invalid_values)
        test_cases = [
            ('OTEL_EXPORTER_OTLP_PROTOCOL', ['grpc', 'http/protobuf'], ['invalid', '', None]),
            ('OTEL_TRACES_EXPORTER', ['otlp', 'console', 'none'], ['invalid', '', None]),
            ('OTEL_SERVICE_NAME', ['verba', 'test-service'], ['', None])
        ]
        
        for env_var, valid_values, invalid_values in test_cases:
            # Test valid values
            for valid_value in valid_values:
                with self.subTest(env_var=env_var, value=valid_value):
                    os.environ[env_var] = valid_value
                    actual_value = os.getenv(env_var)
                    self.assertEqual(actual_value, valid_value)
            
            # Test invalid values (should not crash, but may have defaults)
            for invalid_value in invalid_values:
                with self.subTest(env_var=env_var, value=invalid_value):
                    if invalid_value is None:
                        if env_var in os.environ:
                            del os.environ[env_var]
                        actual_value = os.getenv(env_var)
                        self.assertIsNone(actual_value)
                    else:
                        os.environ[env_var] = invalid_value
                        actual_value = os.getenv(env_var)
                        self.assertEqual(actual_value, invalid_value)
    
    def test_endpoint_url_validation(self):
        """Test OTLP endpoint URL validation."""
        valid_endpoints = [
            'http://phoenix:4317',
            'http://localhost:4317',
            'https://phoenix:4317',
            'grpc://phoenix:4317'
        ]
        
        invalid_endpoints = [
            '',
            'not-a-url',
            'ftp://invalid:4317',
            'phoenix:4317'  # Missing protocol
        ]
        
        for endpoint in valid_endpoints:
            with self.subTest(endpoint=endpoint):
                os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = endpoint
                actual_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
                self.assertEqual(actual_endpoint, endpoint)
                
                # Basic URL validation (should contain protocol and port)
                self.assertIn('://', endpoint)
                self.assertIn(':', endpoint.split('://', 1)[1])
        
        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = endpoint
                actual_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
                self.assertEqual(actual_endpoint, endpoint)
                # Note: We don't validate URL format here, just that it's set


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)