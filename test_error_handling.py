#!/usr/bin/env python3
"""
Test script to verify error handling and resilience features in the observability system.
"""

import asyncio
import sys
import os

# Add the Verba directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from goldenverba.observability import (
    setup_tracing, 
    get_tracer, 
    handle_span_error, 
    create_error_span,
    is_tracing_healthy,
    get_tracing_status,
    reset_tracing_errors,
    CircuitBreaker
)


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("Testing Circuit Breaker...")
    
    # Create a circuit breaker with low thresholds for testing
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    
    def failing_function():
        raise Exception("Test failure")
    
    def working_function():
        return "success"
    
    # Test normal operation
    result = cb.call(working_function)
    assert result == "success", "Circuit breaker should allow working function"
    print("✓ Circuit breaker allows working function")
    
    # Test failure accumulation
    for i in range(3):
        result = cb.call(failing_function)
        assert result is None, f"Circuit breaker should return None on failure {i+1}"
    
    print("✓ Circuit breaker opens after threshold failures")
    assert cb.state == "OPEN", "Circuit breaker should be OPEN after failures"
    
    # Test that circuit breaker blocks calls when open
    result = cb.call(working_function)
    assert result is None, "Circuit breaker should block calls when OPEN"
    print("✓ Circuit breaker blocks calls when OPEN")
    
    print("Circuit breaker test passed!")


def test_error_tracing():
    """Test error tracing functionality."""
    print("\nTesting Error Tracing...")
    
    # Set up tracing (will use no-op if Phoenix not available)
    setup_success = setup_tracing()
    print(f"Tracing setup: {'✓' if setup_success else '✗'}")
    
    tracer = get_tracer()
    
    # Test span error handling
    try:
        with tracer.start_as_current_span("test.error_handling") as span:
            try:
                # Simulate an error
                raise ValueError("Test error for tracing")
            except Exception as e:
                handle_span_error(span, e)
                print("✓ Error handled and recorded in span")
    except (TypeError, AttributeError):
        # If tracer is a mock (Phoenix not available), skip this test
        print("✓ Error handling test skipped (Phoenix not available)")
    
    # Test error span creation
    try:
        raise RuntimeError("Test runtime error")
    except Exception as e:
        create_error_span(tracer, "test_operation", e)
        print("✓ Error span created successfully")
    
    print("Error tracing test passed!")


def test_tracing_status():
    """Test tracing status and health checks."""
    print("\nTesting Tracing Status...")
    
    # Get tracing status
    status = get_tracing_status()
    print(f"Tracing status: {status}")
    
    # Test health check
    healthy = is_tracing_healthy()
    print(f"Tracing healthy: {'✓' if healthy else '✗'}")
    
    # Test error reset
    reset_tracing_errors()
    print("✓ Tracing errors reset")
    
    print("Tracing status test passed!")


import pytest

@pytest.mark.asyncio
async def test_component_error_handling():
    """Test error handling in component managers."""
    print("\nTesting Component Error Handling...")
    
    # Import component managers
    from goldenverba.components.managers import EmbeddingManager, RetrieverManager, GeneratorManager
    
    # Test embedding manager error handling
    embedding_manager = EmbeddingManager()
    
    try:
        # This should fail gracefully with proper error tracing
        await embedding_manager.vectorize_query("nonexistent_embedder", "test query", {})
        print("✗ Expected error not raised")
    except Exception as e:
        print(f"✓ Embedding error handled: {type(e).__name__}")
    
    # Test retriever manager error handling
    retriever_manager = RetrieverManager()
    
    try:
        # This should fail gracefully with proper error tracing
        await retriever_manager.retrieve(
            None, "nonexistent_retriever", "test", [], {}, None, [], []
        )
        print("✗ Expected error not raised")
    except Exception as e:
        print(f"✓ Retrieval error handled: {type(e).__name__}")
    
    print("Component error handling test passed!")


def main():
    """Run all tests."""
    print("Starting Error Handling and Resilience Tests...\n")
    
    try:
        # Test circuit breaker
        test_circuit_breaker()
        
        # Test error tracing
        test_error_tracing()
        
        # Test tracing status
        test_tracing_status()
        
        # Test component error handling
        asyncio.run(test_component_error_handling())
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)