#!/usr/bin/env python3
"""
Run Property 7 test with limited examples for faster execution.
"""
import sys
import os

# Set hypothesis settings before importing
os.environ['HYPOTHESIS_MAX_EXAMPLES'] = '5'
os.environ['HYPOTHESIS_DEADLINE'] = 'None'

# Add the goldenverba package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'goldenverba'))

# Mock OpenTelemetry modules before importing
from unittest.mock import Mock
sys.modules['opentelemetry'] = Mock()
sys.modules['opentelemetry.trace'] = Mock()
sys.modules['opentelemetry.sdk'] = Mock()
sys.modules['opentelemetry.sdk.trace'] = Mock()
sys.modules['opentelemetry.sdk.trace.export'] = Mock()
sys.modules['opentelemetry.exporter'] = Mock()
sys.modules['opentelemetry.exporter.otlp'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc'] = Mock()
sys.modules['opentelemetry.exporter.otlp.proto.grpc.trace_exporter'] = Mock()
sys.modules['opentelemetry.sdk.resources'] = Mock()
sys.modules['phoenix'] = Mock()
sys.modules['phoenix.otel'] = Mock()
sys.modules['openinference'] = Mock()
sys.modules['openinference.instrumentation'] = Mock()
sys.modules['openinference.instrumentation.langchain'] = Mock()

# Now import and run the test
from test_observability_property import test_error_tracing_completeness_property
from hypothesis import settings

print("Running Property 7: Error tracing completeness test with 5 examples...")
print("=" * 70)

try:
    # Run the test with limited examples
    test_error_tracing_completeness_property()
    print("\n" + "=" * 70)
    print("✓ Property 7 test PASSED!")
    print("=" * 70)
    sys.exit(0)
except Exception as e:
    print("\n" + "=" * 70)
    print(f"✗ Property 7 test FAILED: {e}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
