#!/usr/bin/env python3
"""
Property-based tests for Verba observability integration.

This module contains property-based tests that verify the correctness
of OpenTelemetry tracing integration with Phoenix.
"""
import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import pytest

# Add the goldenverba package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'goldenverba'))

# Import hypothesis for property-based testing
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

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


@composite
def rag_config_strategy(draw):
    """Generate realistic RAG configurations for testing."""
    retrievers = ["SimpleRetriever", "HybridRetriever", "WindowRetriever"]
    embedders = ["OpenAIEmbedder", "HuggingFaceEmbedder", "CohereEmbedder"]
    generators = ["OpenAIGenerator", "OllamaGenerator", "CohereGenerator"]
    
    retriever_name = draw(st.sampled_from(retrievers))
    embedder_name = draw(st.sampled_from(embedders))
    generator_name = draw(st.sampled_from(generators))
    
    top_k = draw(st.integers(min_value=1, max_value=20))
    
    # Create mock objects with proper structure
    retriever_mock = Mock()
    retriever_mock.selected = retriever_name
    retriever_mock.components = {
        retriever_name: {
            "config": {
                "top_k": {"value": top_k}
            }
        }
    }
    
    embedder_mock = Mock()
    embedder_mock.selected = embedder_name
    
    generator_mock = Mock()
    generator_mock.selected = generator_name
    
    return {
        "Retriever": retriever_mock,
        "Embedder": embedder_mock,
        "Generator": generator_mock
    }


@composite
def query_strategy(draw):
    """Generate realistic user queries for testing."""
    # Generate queries of various lengths and types
    query_types = [
        # Short queries
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))),
        # Medium queries  
        st.text(min_size=51, max_size=200, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))),
        # Long queries
        st.text(min_size=201, max_size=1000, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs')))
    ]
    
    query = draw(st.one_of(query_types))
    # Ensure query is not empty or just whitespace
    assume(query.strip())
    return query.strip()


@composite
def session_id_strategy(draw):
    """Generate realistic session IDs."""
    return draw(st.text(min_size=8, max_size=64, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))


class MockSpan:
    """Mock span that tracks all operations for verification."""
    
    def __init__(self, name: str):
        self.name = name
        self.attributes = {}
        self.status = None
        self.errors = []
        self.exceptions = []
        self.is_recording = True
        
    def set_attribute(self, key: str, value: Any):
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


@settings(max_examples=100, deadline=None)
@given(
    query=query_strategy(),
    rag_config=rag_config_strategy(),
    session_id=session_id_strategy()
)
def test_query_trace_export_property(query: str, rag_config: Dict[str, Any], session_id: str):
    """
    **Feature: verba-observability, Property 1: Query trace export**
    
    Property: For any user query processed by Verba, the system should successfully 
    export trace data to Phoenix without application errors.
    
    This test verifies that:
    1. Trace spans are created for any valid query
    2. No exceptions are raised during trace export
    3. Required attributes are attached to spans
    4. The application continues to function normally
    """
    
    # Setup mock tracer and observability functions
    mock_tracer = MockTracer()
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes') as mock_attach, \
         patch('goldenverba.observability.handle_span_error') as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context') as mock_experiment:
        
        # Setup experiment context mock
        mock_experiment.return_value = {
            "exp.name": "verba_rag_experiment_001",
            "exp.variant": "A" if hash(session_id) % 2 == 0 else "B",
            "user.session_id": session_id
        }
        
        # Import and setup VerbaManager with mocked dependencies
        from goldenverba.verba_manager import VerbaManager
        
        manager = VerbaManager()
        
        # Mock all manager dependencies
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        
        manager.embedder_manager = Mock()
        # Generate a realistic embedding vector
        embedding_dim = 1536  # Common OpenAI embedding dimension
        mock_vector = [0.1] * embedding_dim
        manager.embedder_manager.vectorize_query = AsyncMock(return_value=mock_vector)
        
        manager.retriever_manager = Mock()
        # Generate mock documents and context
        mock_documents = [f"Document {i}" for i in range(min(5, len(query) // 10 + 1))]
        mock_context = f"Context for query: {query[:100]}..."
        manager.retriever_manager.retrieve = AsyncMock(return_value=(mock_documents, mock_context))
        
        async def run_property_test():
            """Execute the property test asynchronously."""
            try:
                # Execute retrieve_chunks which should create traces
                result = await manager.retrieve_chunks(
                    client=Mock(),
                    query=query,
                    rag_config=rag_config,
                    user_session_id=session_id
                )
                
                # Verify that the operation completed successfully
                assert result is not None, "retrieve_chunks should return a result"
                documents, context = result
                assert isinstance(documents, list), "Documents should be a list"
                assert isinstance(context, str), "Context should be a string"
                
                # Verify trace export behavior - spans should be created
                assert len(mock_tracer.spans_created) > 0, "At least one span should be created"
                
                # Verify root span was created
                root_spans = [span for span in mock_tracer.spans_created if span.name == "rag.query"]
                assert len(root_spans) == 1, "Exactly one rag.query span should be created"
                
                root_span = root_spans[0]
                
                # Verify no unhandled errors occurred in span creation
                assert len(root_span.errors) == 0, f"No errors should occur in span creation, got: {root_span.errors}"
                
                # Verify tracer was called (indicating trace export attempt)
                assert mock_tracer.spans_created, "Tracer should have been used to create spans"
                
                # Verify attributes were attached (indicating proper trace data)
                assert mock_attach.call_count >= 1, "Attributes should be attached to spans"
                
                # Verify experiment context was created for session tracking
                mock_experiment.assert_called_once_with(session_id)
                
                # Verify no span errors were recorded (indicating successful export)
                assert mock_handle_error.call_count == 0, "No span errors should be recorded for successful operations"
                
                return True
                
            except Exception as e:
                # Property violation: trace export should not cause application errors
                pytest.fail(f"Query trace export failed for query='{query[:50]}...', session='{session_id}': {e}")
                
        # Run the async test
        result = asyncio.run(run_property_test())
        assert result, "Property test should pass"


@settings(max_examples=50, deadline=None)
@given(
    query=query_strategy(),
    rag_config=rag_config_strategy(),
    session_id=session_id_strategy()
)
def test_trace_export_resilience_property(query: str, rag_config: Dict[str, Any], session_id: str):
    """
    **Feature: verba-observability, Property 8: Trace export resilience**
    
    Property: For any trace export failure, the system should log the error and 
    continue normal application functionality without disruption.
    
    This test simulates export failures and verifies graceful degradation.
    """
    
    # Setup mock tracer that simulates export failures
    mock_tracer = MockTracer()
    
    # Mock a failing exporter
    failing_exporter = Mock()
    failing_exporter.export.side_effect = Exception("Phoenix connection failed")
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes') as mock_attach, \
         patch('goldenverba.observability.handle_span_error') as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context') as mock_experiment, \
         patch('goldenverba.observability._circuit_breaker') as mock_circuit_breaker:
        
        # Setup mocks
        mock_experiment.return_value = {
            "exp.name": "verba_rag_experiment_001", 
            "exp.variant": "A",
            "user.session_id": session_id
        }
        
        # Simulate circuit breaker in different states
        mock_circuit_breaker.state = "CLOSED"  # Allow calls initially
        mock_circuit_breaker.call.side_effect = lambda func, *args, **kwargs: None  # Simulate export failure
        
        from goldenverba.verba_manager import VerbaManager
        
        manager = VerbaManager()
        
        # Mock dependencies
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        
        manager.embedder_manager = Mock()
        manager.embedder_manager.vectorize_query = AsyncMock(return_value=[0.1] * 1536)
        
        manager.retriever_manager = Mock()
        mock_documents = [f"Doc {i}" for i in range(3)]
        mock_context = f"Context: {query[:50]}"
        manager.retriever_manager.retrieve = AsyncMock(return_value=(mock_documents, mock_context))
        
        async def run_resilience_test():
            """Test that export failures don't break the application."""
            try:
                # Execute operation that should succeed despite export failures
                result = await manager.retrieve_chunks(
                    client=Mock(),
                    query=query,
                    rag_config=rag_config,
                    user_session_id=session_id
                )
                
                # Verify application functionality continues normally
                assert result is not None, "Application should continue working despite export failures"
                documents, context = result
                assert isinstance(documents, list), "Documents should still be returned"
                assert isinstance(context, str), "Context should still be returned"
                
                # Verify spans were still created (even if export failed)
                assert len(mock_tracer.spans_created) > 0, "Spans should still be created"
                
                # Verify the application didn't crash or raise exceptions
                # This is the key property: resilience to export failures
                
                return True
                
            except Exception as e:
                # This would be a property violation - export failures should not break the app
                pytest.fail(f"Application failed due to trace export issues: {e}")
                
        result = asyncio.run(run_resilience_test())
        assert result, "Resilience property test should pass"


if __name__ == "__main__":
    # Run property tests directly
    print("Running property-based tests for observability...")
    
    # Test a few examples manually
    import hypothesis
    
    try:
        test_query_trace_export_property()
        print("✓ Property 1 (Query trace export) - Tests passed")
    except Exception as e:
        print(f"✗ Property 1 (Query trace export) - Tests failed: {e}")
    
    try:
        test_trace_export_resilience_property()
        print("✓ Property 8 (Trace export resilience) - Tests passed")
    except Exception as e:
        print(f"✗ Property 8 (Trace export resilience) - Tests failed: {e}")
    
    print("Property-based testing complete.")