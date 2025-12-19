#!/usr/bin/env python3
"""
Simple test for error tracing property to verify the implementation works.
"""
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add the goldenverba package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'goldenverba'))

# Mock OpenTelemetry modules before importing
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


class MockSpan:
    """Mock span that tracks all operations for verification."""
    
    def __init__(self, name: str):
        self.name = name
        self.attributes = {}
        self.status = None
        self.errors = []
        self.exceptions = []
        self.is_recording = True
        
    def set_attribute(self, key: str, value):
        """Record attribute setting."""
        self.attributes[key] = value
        
    def set_status(self, status):
        """Record status setting."""
        self.status = status
        
    def record_exception(self, exception):
        """Record exception."""
        self.exceptions.append(exception)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.errors.append((exc_type, exc_val, exc_tb))
        return False


class MockTracer:
    """Mock tracer that tracks span creation."""
    
    def __init__(self):
        self.spans_created = []
        self.current_span = None
        
    def start_as_current_span(self, name: str):
        """Create and track a new span."""
        span = MockSpan(name)
        self.spans_created.append(span)
        self.current_span = span
        return span


def test_error_tracing_simple():
    """
    Simple test for Property 7: Error tracing completeness
    
    Tests that when an exception occurs, the system properly traces it with
    error.type and error.message attributes.
    """
    print("Testing Property 7: Error tracing completeness...")
    
    # Setup mock tracer
    mock_tracer = MockTracer()
    
    # Create a real attach_rag_attributes function
    def real_attach_rag_attributes(span, attributes):
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
    
    # Create a real handle_span_error function
    def real_handle_span_error(span, error):
        """Real implementation of handle_span_error for testing."""
        try:
            span.status = "ERROR"
            span.set_attribute("error.type", type(error).__name__)
            span.set_attribute("error.message", str(error))
            span.record_exception(error)
        except Exception:
            pass
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes', side_effect=real_attach_rag_attributes), \
         patch('goldenverba.observability.handle_span_error', side_effect=real_handle_span_error) as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context') as mock_experiment:
        
        mock_experiment.return_value = {
            "exp.name": "test_experiment",
            "exp.variant": "A",
            "user.session_id": "test_session"
        }
        
        # Import VerbaManager
        from goldenverba.verba_manager import VerbaManager
        
        manager = VerbaManager()
        
        # Mock dependencies to raise an error
        test_error = ValueError("Test error for tracing")
        
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        manager.embedder_manager = Mock()
        manager.embedder_manager.vectorize_query = AsyncMock(side_effect=test_error)
        manager.retriever_manager = Mock()
        manager.generator_manager = Mock()
        
        # Test the error tracing
        import asyncio
        
        async def run_test():
            try:
                # This should trigger an error in embedding
                await manager.retrieve_chunks(
                    client=Mock(),
                    query="test query",
                    rag_config={
                        "Retriever": Mock(selected="TestRetriever"),
                        "Embedder": Mock(selected="TestEmbedder"),
                        "Generator": Mock(selected="TestGenerator")
                    },
                    user_session_id="test_session"
                )
            except Exception:
                # Expected - the error should be handled gracefully
                pass
            
            # Verify error tracing
            print(f"Spans created: {len(mock_tracer.spans_created)}")
            print(f"handle_span_error called: {mock_handle_error.call_count} times")
            
            # Check for error spans
            error_spans = []
            for span in mock_tracer.spans_created:
                if "error.type" in span.attributes or span.status == "ERROR":
                    error_spans.append(span)
                    print(f"Error span: {span.name}")
                    print(f"  error.type: {span.attributes.get('error.type')}")
                    print(f"  error.message: {span.attributes.get('error.message')}")
                    print(f"  status: {span.status}")
            
            # Verify requirements
            assert len(mock_tracer.spans_created) > 0, "Spans should be created"
            assert mock_handle_error.call_count > 0, "handle_span_error should be called"
            assert len(error_spans) > 0, "At least one error span should exist"
            
            # Check error attributes
            for error_span in error_spans:
                if "error.type" in error_span.attributes:
                    assert error_span.attributes["error.type"] == "ValueError"
                    assert "Test error for tracing" in error_span.attributes["error.message"]
                    assert error_span.status == "ERROR"
            
            print("✓ Property 7 test passed!")
            return True
        
        result = asyncio.run(run_test())
        return result


if __name__ == "__main__":
    try:
        test_error_tracing_simple()
        print("✓ Error tracing property test completed successfully")
    except Exception as e:
        print(f"✗ Error tracing property test failed: {e}")
        import traceback
        traceback.print_exc()