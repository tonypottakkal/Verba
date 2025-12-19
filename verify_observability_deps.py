#!/usr/bin/env python3
"""
Verification script for observability dependencies.
This script verifies that all required OpenTelemetry and Phoenix packages
can be imported without ModuleNotFoundError.
"""

import sys
from typing import List, Tuple


def verify_import(module_name: str, description: str) -> Tuple[bool, str]:
    """Verify that a module can be imported successfully."""
    try:
        __import__(module_name)
        return True, f"✅ {description}: {module_name}"
    except ModuleNotFoundError as e:
        return False, f"❌ {description}: {module_name} - {str(e)}"
    except Exception as e:
        return False, f"⚠️  {description}: {module_name} - Unexpected error: {str(e)}"


def main():
    """Verify all observability dependencies."""
    print("🔍 Verifying observability dependencies...")
    print("=" * 60)
    
    # Required dependencies from task requirements 3.1-3.5
    dependencies = [
        ("phoenix.otel", "Arize Phoenix OpenTelemetry integration"),
        ("opentelemetry.sdk", "OpenTelemetry SDK"),
        ("opentelemetry.exporter.otlp", "OpenTelemetry OTLP exporter"),
        ("openinference.instrumentation.langchain", "OpenInference LangChain instrumentation"),
        ("opentelemetry.instrumentation.requests", "OpenTelemetry HTTP requests instrumentation (optional)"),
    ]
    
    print("\n📦 Checking package imports...")
    
    all_passed = True
    results: List[Tuple[bool, str]] = []
    
    for module_name, description in dependencies:
        success, message = verify_import(module_name, description)
        results.append((success, message))
        print(f"   {message}")
        
        if not success:
            all_passed = False
    
    # Additional verification: Check if we can create basic OTel components
    print("\n🔧 Checking OpenTelemetry functionality...")
    
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        
        # Try to create basic components (without actually connecting)
        tracer_provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
        
        print("   ✅ OpenTelemetry components can be instantiated")
        
    except Exception as e:
        print(f"   ❌ Failed to create OpenTelemetry components: {str(e)}")
        all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All observability dependencies verified successfully!")
        print("\n📝 Dependencies ready for:")
        print("   • OpenTelemetry trace export to Phoenix")
        print("   • LangChain automatic instrumentation")
        print("   • HTTP request tracing (optional)")
        return 0
    else:
        print("⚠️  Some dependencies failed verification.")
        print("\n🔧 Troubleshooting:")
        print("   1. Rebuild Docker image: docker build -t verba .")
        print("   2. Check pip install logs for errors")
        print("   3. Verify Python version compatibility (3.11+)")
        return 1


if __name__ == "__main__":
    sys.exit(main())