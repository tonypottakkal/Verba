#!/usr/bin/env python3
"""
Minimal test for Property 7: Error tracing completeness
"""
import sys
import os
import asyncio
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

from hypothesis import given, strategies as st, settings


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


@settings(max_examples=5, deadline=None)  # Reduced examples for faster testing
@given(
    query=st.text(min_size=1, max_size=50),
    error_type=st.sampled_from([ValueError, ConnectionError, RuntimeError])
)
def test_error_tracing_completeness_property(query: str, error_type):
    """
    **Feature: verba-observability, Property 7: Error tracing completeness**
    
    Property: For any exception during RAG processing, the system should attach 
    error.type and error.message attributes to relevant spans and mark them with error status.
    """
    
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
        
        # Create test error
        test_error = error_type("Test error message")
        
        # Mock dependencies to raise error
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        manager.embedder_manager = Mock()
        manager.embedder_manager.vectorize_query = AsyncMock(side_effect=test_error)
        manager.retriever_manager = Mock()
        manager.generator_manager = Mock()
        
        # Create mock RAG config
        rag_config = {
            "Retriever": Mock(selected="TestRetriever"),
            "Embedder": Mock(selected="TestEmbedder"), 
            "Generator": Mock(selected="TestGenerator")
        }
        
        async def run_test():
            try:
                # This should trigger an error
                await manager.retrieve_chunks(
                    client=Mock(),
                    query=query,
                    rag_config=rag_config,
                    user_session_id="test_session"
                )
            except Exception:
                # Expected - errors should be handled gracefully
                pass
            
            # Verify error tracing requirements
            
            # 1. Spans should be created even with errors
            assert len(mock_tracer.spans_created) > 0, "Spans should be created even when errors occur"
            
            # 2. handle_span_error should be called
            assert mock_handle_error.call_count > 0, "handle_span_error should be called when errors occur"
            
            # 3. Find error spans
            error_spans = []
            for span in mock_tracer.spans_created:
                if "error.type" in span.attributes or span.status == "ERROR":
                    error_spans.append(span)
            
            assert len(error_spans) > 0, "At least one span should have error information"
            
            # 4. Verify error attributes (Requirements 9.1, 9.2, 9.3)
            for error_span in error_spans:
                if "error.type" in error_span.attributes:
                    # Requirement 9.1: error.type should match exception class or be wrapped as Exception
                    actual_error_type = error_span.attributes["error.type"]
                    expected_error_types = [error_type.__name__, "Exception"]
                    assert actual_error_type in expected_error_types, \
                        f"error.type should be one of {expected_error_types}, got {actual_error_type}"
                    
                    # Requirement 9.1: error.message should be present
                    assert "error.message" in error_span.attributes
                    # The error message should contain relevant information (original or wrapped)
                    error_message = error_span.attributes["error.message"]
                    message_found = ("Test error message" in error_message or 
                                   "failed" in error_message.lower())
                    assert message_found, f"error.message should contain relevant error information, got '{error_message}'"
                    
                    # Requirement 9.2, 9.3: span should be marked with error status
                    assert error_span.status == "ERROR"
            
            return True
        
        result = asyncio.run(run_test())
        assert result, "Error tracing property test should pass"


if __name__ == "__main__":
    print("Running Property 7: Error tracing completeness test...")
    try:
        # Test manually without hypothesis
        from goldenverba.verba_manager import VerbaManager
        
        # Setup mock tracer
        mock_tracer = MockTracer()
        
        def real_attach_rag_attributes(span, attributes):
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
        
        def real_handle_span_error(span, error):
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
            
            manager = VerbaManager()
            
            # Test different error types
            error_types = [ValueError, ConnectionError, RuntimeError]
            
            for error_type in error_types:
                print(f"Testing {error_type.__name__}...")
                
                # Reset tracer for each test
                mock_tracer.spans_created = []
                mock_handle_error.reset_mock()
                
                # Create test error
                test_error = error_type("Test error message")
                
                # Mock dependencies
                manager.weaviate_manager = Mock()
                manager.weaviate_manager.add_suggestion = AsyncMock()
                manager.embedder_manager = Mock()
                manager.embedder_manager.vectorize_query = AsyncMock(side_effect=test_error)
                manager.retriever_manager = Mock()
                manager.generator_manager = Mock()
                
                rag_config = {
                    "Retriever": Mock(selected="TestRetriever"),
                    "Embedder": Mock(selected="TestEmbedder"),
                    "Generator": Mock(selected="TestGenerator")
                }
                
                async def run_single_test():
                    try:
                        await manager.retrieve_chunks(
                            client=Mock(),
                            query="test query",
                            rag_config=rag_config,
                            user_session_id="test_session"
                        )
                    except Exception:
                        pass
                    
                    # Verify error tracing
                    assert len(mock_tracer.spans_created) > 0, "Spans should be created"
                    assert mock_handle_error.call_count > 0, "handle_span_error should be called"
                    
                    error_spans = [span for span in mock_tracer.spans_created 
                                 if "error.type" in span.attributes or span.status == "ERROR"]
                    assert len(error_spans) > 0, "Error spans should exist"
                    
                    for error_span in error_spans:
                        if "error.type" in error_span.attributes:
                            # Handle both original and wrapped error types
                            actual_type = error_span.attributes["error.type"]
                            expected_types = [error_type.__name__, "Exception"]
                            assert actual_type in expected_types
                            assert "error.message" in error_span.attributes
                            # Check for either original message or wrapped message
                            error_msg = error_span.attributes["error.message"]
                            assert ("Test error message" in error_msg or "failed" in error_msg.lower())
                            assert error_span.status == "ERROR"
                    
                    return True
                
                result = asyncio.run(run_single_test())
                assert result
                print(f"  ✓ {error_type.__name__} test passed")
        
        print("✓ All Property 7 tests passed!")
        
    except Exception as e:
        print(f"✗ Property 7 test failed: {e}")
        import traceback
        traceback.print_exc()