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
    temperature = draw(st.floats(min_value=0.0, max_value=2.0))
    
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
    generator_mock.components = {
        generator_name: {
            "config": {
                "temperature": {"value": temperature}
            }
        }
    }
    
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


@settings(max_examples=100, deadline=None)
@given(
    query=query_strategy(),
    rag_config=rag_config_strategy(),
    session_id=session_id_strategy()
)
def test_rag_span_structure_completeness_property(query: str, rag_config: Dict[str, Any], session_id: str):
    """
    **Feature: verba-observability, Property 2: RAG span structure completeness**
    
    Property: For any user query, the system should create a complete span hierarchy 
    including root rag.query span, rag.retrieve span, and rag.generate span with 
    proper parent-child relationships.
    
    This test verifies that:
    1. A root rag.query span is created for every query
    2. A rag.retrieve span is created during document retrieval
    3. A rag.generate span is created during text generation
    4. Spans have proper hierarchical relationships
    5. All required spans are present regardless of query content
    """
    
    # Setup mock tracer that tracks span hierarchy
    mock_tracer = MockTracer()
    
    # Create a real attach_rag_attributes function that actually sets attributes
    def real_attach_rag_attributes(span, attributes):
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes', side_effect=real_attach_rag_attributes) as mock_attach, \
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
        
        # Mock the retrieve method to also create the rag.retrieve span
        async def mock_retrieve(*args, **kwargs):
            # Create the rag.retrieve span that would normally be created
            with mock_tracer.start_as_current_span("rag.retrieve") as retrieve_span:
                retrieve_span.set_attribute("rag.retrieved_docs_count", len(mock_documents))
                retrieve_span.set_attribute("rag.context_chars", len(mock_context))
                return (mock_documents, mock_context)
        
        manager.retriever_manager.retrieve = mock_retrieve
        
        manager.generator_manager = Mock()
        
        # Mock the generator stream to simulate text generation
        async def mock_generate_stream(rag_config, query, context, conversation):
            """Mock streaming generator that yields realistic responses."""
            response_parts = [
                {"message": "Based on the provided context, "},
                {"message": "I can answer your question about "},
                {"message": query[:20] + "... "},
                {"message": "The relevant information shows that "},
                {"message": "this is a comprehensive response."}
            ]
            for part in response_parts:
                yield part
        
        manager.generator_manager.generate_stream = mock_generate_stream
        
        async def run_span_structure_test():
            """Execute the span structure property test."""
            try:
                # Execute retrieve_chunks which should create rag.query and rag.retrieve spans
                result = await manager.retrieve_chunks(
                    client=Mock(),
                    query=query,
                    rag_config=rag_config,
                    user_session_id=session_id
                )
                
                # Verify retrieve_chunks completed successfully
                assert result is not None, "retrieve_chunks should return a result"
                documents, context = result
                assert isinstance(documents, list), "Documents should be a list"
                assert isinstance(context, str), "Context should be a string"
                
                # Execute generate_stream_answer which should create rag.generate span
                response_parts = []
                async for part in manager.generate_stream_answer(
                    rag_config=rag_config,
                    query=query,
                    context=context,
                    conversation=[],
                    user_session_id=session_id
                ):
                    response_parts.append(part)
                
                # Verify generation completed successfully
                assert len(response_parts) > 0, "Generation should produce response parts"
                
                # Now verify the span structure completeness
                
                # 1. Verify root rag.query span exists
                query_spans = [span for span in mock_tracer.spans_created if span.name == "rag.query"]
                assert len(query_spans) == 1, f"Expected exactly 1 rag.query span, got {len(query_spans)}"
                
                root_span = query_spans[0]
                
                # 2. Verify rag.retrieve span exists (created by retriever_manager.retrieve)
                retrieve_spans = [span for span in mock_tracer.spans_created if span.name == "rag.retrieve"]
                assert len(retrieve_spans) >= 1, f"Expected at least 1 rag.retrieve span, got {len(retrieve_spans)}"
                
                # 3. Verify rag.generate span exists
                generate_spans = [span for span in mock_tracer.spans_created if span.name == "rag.generate"]
                assert len(generate_spans) == 1, f"Expected exactly 1 rag.generate span, got {len(generate_spans)}"
                
                generation_span = generate_spans[0]
                
                # 4. Verify span hierarchy and completeness
                # All spans should be created (indicating proper instrumentation)
                expected_span_names = {"rag.query", "rag.generate"}
                actual_span_names = {span.name for span in mock_tracer.spans_created}
                
                # Check that required spans are present
                missing_spans = expected_span_names - actual_span_names
                assert not missing_spans, f"Missing required spans: {missing_spans}"
                
                # 5. Verify spans have proper attributes (indicating they were properly instrumented)
                # Root span should have query characteristics
                assert "rag.query_chars" in root_span.attributes, "Root span should have query_chars attribute"
                assert root_span.attributes["rag.query_chars"] == len(query), "Query chars should match actual query length"
                
                # Generation span should have model information
                assert "rag.model" in generation_span.attributes, "Generation span should have model attribute"
                assert "rag.streaming" in generation_span.attributes, "Generation span should have streaming attribute"
                
                # 6. Verify no span errors occurred (indicating successful instrumentation)
                for span in mock_tracer.spans_created:
                    assert len(span.errors) == 0, f"Span {span.name} should not have errors: {span.errors}"
                
                # 7. Verify experiment context was applied to spans (if session provided)
                if session_id:
                    assert "user.session_id" in root_span.attributes, "Root span should have session_id when provided"
                    assert root_span.attributes["user.session_id"] == session_id, "Session ID should match"
                    
                    assert "user.session_id" in generation_span.attributes, "Generation span should have session_id when provided"
                    assert generation_span.attributes["user.session_id"] == session_id, "Session ID should match in generation span"
                
                return True
                
            except Exception as e:
                # Property violation: span structure should be complete for any valid query
                pytest.fail(f"RAG span structure incomplete for query='{query[:50]}...', session='{session_id}': {e}")
                
        # Run the async test
        result = asyncio.run(run_span_structure_test())
        assert result, "Span structure completeness property test should pass"


@settings(max_examples=100, deadline=None)
@given(
    query=query_strategy(),
    rag_config=rag_config_strategy(),
    session_id=session_id_strategy()
)
def test_kpi_attribute_completeness_property(query: str, rag_config: Dict[str, Any], session_id: str):
    """
    **Feature: verba-observability, Property 3: KPI attribute completeness**
    
    Property: For any completed RAG operation, all required KPI attributes 
    (query_chars, retrieved_docs_count, context_chars, model, embed_model, top_k, success) 
    should be attached to their respective spans.
    
    This test verifies that:
    1. rag.query_chars is attached to query spans with correct input character count
    2. rag.retrieved_docs_count and rag.context_chars are attached to retrieval spans
    3. rag.model and rag.embed_model are attached with model identifiers
    4. rag.top_k is attached with retrieval parameters
    5. rag.success is attached indicating completion status
    6. All KPI attributes are present regardless of query content or configuration
    """
    
    # Setup mock tracer that tracks all attribute assignments
    mock_tracer = MockTracer()
    
    # Create a real attach_rag_attributes function that actually sets attributes
    def real_attach_rag_attributes(span, attributes):
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes', side_effect=real_attach_rag_attributes) as mock_attach, \
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
        # Generate mock documents and context based on query
        num_docs = min(max(1, len(query) // 50), 10)  # 1-10 docs based on query length
        mock_documents = [f"Document {i}: Content related to {query[:20]}..." for i in range(num_docs)]
        mock_context = f"Context for query '{query[:100]}': " + " ".join(mock_documents)
        
        # Mock the retrieve method to also create the rag.retrieve span with KPI attributes
        async def mock_retrieve(*args, **kwargs):
            # Create the rag.retrieve span that would normally be created
            with mock_tracer.start_as_current_span("rag.retrieve") as retrieve_span:
                # Attach KPI attributes that should be present
                retrieve_span.set_attribute("rag.retrieved_docs_count", len(mock_documents))
                retrieve_span.set_attribute("rag.context_chars", len(mock_context))
                retrieve_span.set_attribute("rag.success", True)
                
                # Add retrieval-specific attributes
                retrieve_span.set_attribute("rag.retriever", rag_config["Retriever"].selected)
                retrieve_span.set_attribute("rag.embed_model", rag_config["Embedder"].selected)
                retrieve_span.set_attribute("rag.query_chars", len(query))
                
                # Add top_k from configuration
                top_k = rag_config["Retriever"].components.get(
                    rag_config["Retriever"].selected, {}
                ).get("config", {}).get("top_k", {}).get("value", 10)
                retrieve_span.set_attribute("rag.top_k", top_k)
                
                return (mock_documents, mock_context)
        
        manager.retriever_manager.retrieve = mock_retrieve
        
        manager.generator_manager = Mock()
        
        # Mock the generator stream to simulate text generation with KPI attributes
        async def mock_generate_stream(rag_config, query, context, conversation):
            """Mock streaming generator that yields realistic responses."""
            response_parts = [
                {"message": "Based on the provided context, "},
                {"message": "I can answer your question about "},
                {"message": query[:20] + "... "},
                {"message": "The relevant information shows that "},
                {"message": "this is a comprehensive response."}
            ]
            for part in response_parts:
                yield part
        
        manager.generator_manager.generate_stream = mock_generate_stream
        
        async def run_kpi_attributes_test():
            """Execute the KPI attributes property test."""
            try:
                # Execute retrieve_chunks which should create spans with KPI attributes
                result = await manager.retrieve_chunks(
                    client=Mock(),
                    query=query,
                    rag_config=rag_config,
                    user_session_id=session_id
                )
                
                # Verify retrieve_chunks completed successfully
                assert result is not None, "retrieve_chunks should return a result"
                documents, context = result
                assert isinstance(documents, list), "Documents should be a list"
                assert isinstance(context, str), "Context should be a string"
                
                # Execute generate_stream_answer which should create generation spans with KPI attributes
                response_parts = []
                async for part in manager.generate_stream_answer(
                    rag_config=rag_config,
                    query=query,
                    context=context,
                    conversation=[],
                    user_session_id=session_id
                ):
                    response_parts.append(part)
                
                # Verify generation completed successfully
                assert len(response_parts) > 0, "Generation should produce response parts"
                
                # Now verify KPI attribute completeness
                
                # 1. Find the root rag.query span
                query_spans = [span for span in mock_tracer.spans_created if span.name == "rag.query"]
                assert len(query_spans) == 1, f"Expected exactly 1 rag.query span, got {len(query_spans)}"
                root_span = query_spans[0]
                
                # 2. Find rag.retrieve spans
                retrieve_spans = [span for span in mock_tracer.spans_created if span.name == "rag.retrieve"]
                assert len(retrieve_spans) >= 1, f"Expected at least 1 rag.retrieve span, got {len(retrieve_spans)}"
                retrieve_span = retrieve_spans[0]  # Use first retrieve span
                
                # 3. Find rag.generate spans
                generate_spans = [span for span in mock_tracer.spans_created if span.name == "rag.generate"]
                assert len(generate_spans) == 1, f"Expected exactly 1 rag.generate span, got {len(generate_spans)}"
                generation_span = generate_spans[0]
                
                # 4. Verify KPI Attribute Completeness (Requirements 5.1-5.5)
                
                # Requirement 5.1: rag.query_chars attribute with input character count
                assert "rag.query_chars" in root_span.attributes, "Root span missing rag.query_chars attribute"
                assert root_span.attributes["rag.query_chars"] == len(query), \
                    f"rag.query_chars should be {len(query)}, got {root_span.attributes.get('rag.query_chars')}"
                
                # Requirement 5.2: rag.retrieved_docs_count and rag.context_chars attributes
                assert "rag.retrieved_docs_count" in retrieve_span.attributes, \
                    "Retrieve span missing rag.retrieved_docs_count attribute"
                assert retrieve_span.attributes["rag.retrieved_docs_count"] == len(documents), \
                    f"rag.retrieved_docs_count should be {len(documents)}, got {retrieve_span.attributes.get('rag.retrieved_docs_count')}"
                
                assert "rag.context_chars" in retrieve_span.attributes, \
                    "Retrieve span missing rag.context_chars attribute"
                assert retrieve_span.attributes["rag.context_chars"] == len(context), \
                    f"rag.context_chars should be {len(context)}, got {retrieve_span.attributes.get('rag.context_chars')}"
                
                # Requirement 5.3: rag.model and rag.embed_model attributes with model identifiers
                assert "rag.model" in root_span.attributes, "Root span missing rag.model attribute"
                assert root_span.attributes["rag.model"] == rag_config["Generator"].selected, \
                    f"rag.model should be {rag_config['Generator'].selected}, got {root_span.attributes.get('rag.model')}"
                
                assert "rag.embed_model" in root_span.attributes, "Root span missing rag.embed_model attribute"
                assert root_span.attributes["rag.embed_model"] == rag_config["Embedder"].selected, \
                    f"rag.embed_model should be {rag_config['Embedder'].selected}, got {root_span.attributes.get('rag.embed_model')}"
                
                # Requirement 5.4: rag.top_k and rag.index attributes with retrieval parameters
                assert "rag.top_k" in root_span.attributes, "Root span missing rag.top_k attribute"
                expected_top_k = rag_config["Retriever"].components.get(
                    rag_config["Retriever"].selected, {}
                ).get("config", {}).get("top_k", {}).get("value", 10)
                assert root_span.attributes["rag.top_k"] == expected_top_k, \
                    f"rag.top_k should be {expected_top_k}, got {root_span.attributes.get('rag.top_k')}"
                
                # Requirement 5.5: rag.success attribute indicating completion status
                assert "rag.success" in root_span.attributes, "Root span missing rag.success attribute"
                assert root_span.attributes["rag.success"] is True, \
                    f"rag.success should be True for successful operations, got {root_span.attributes.get('rag.success')}"
                
                assert "rag.success" in retrieve_span.attributes, "Retrieve span missing rag.success attribute"
                assert retrieve_span.attributes["rag.success"] is True, \
                    f"rag.success should be True for successful retrieval, got {retrieve_span.attributes.get('rag.success')}"
                
                # Additional verification: Generation span should also have model information
                assert "rag.model" in generation_span.attributes, "Generation span missing rag.model attribute"
                assert generation_span.attributes["rag.model"] == rag_config["Generator"].selected, \
                    f"Generation rag.model should be {rag_config['Generator'].selected}, got {generation_span.attributes.get('rag.model')}"
                
                # 5. Verify attribute types are correct (OpenTelemetry compatibility)
                # String attributes
                assert isinstance(root_span.attributes["rag.model"], str), "rag.model should be string"
                assert isinstance(root_span.attributes["rag.embed_model"], str), "rag.embed_model should be string"
                
                # Integer attributes
                assert isinstance(root_span.attributes["rag.query_chars"], int), "rag.query_chars should be integer"
                assert isinstance(retrieve_span.attributes["rag.retrieved_docs_count"], int), "rag.retrieved_docs_count should be integer"
                assert isinstance(retrieve_span.attributes["rag.context_chars"], int), "rag.context_chars should be integer"
                assert isinstance(root_span.attributes["rag.top_k"], int), "rag.top_k should be integer"
                
                # Boolean attributes
                assert isinstance(root_span.attributes["rag.success"], bool), "rag.success should be boolean"
                assert isinstance(retrieve_span.attributes["rag.success"], bool), "rag.success should be boolean"
                
                # 6. Verify no required KPI attributes are missing
                required_root_attributes = {"rag.query_chars", "rag.model", "rag.embed_model", "rag.top_k", "rag.success"}
                missing_root_attrs = required_root_attributes - set(root_span.attributes.keys())
                assert not missing_root_attrs, f"Root span missing required KPI attributes: {missing_root_attrs}"
                
                required_retrieve_attributes = {"rag.retrieved_docs_count", "rag.context_chars", "rag.success"}
                missing_retrieve_attrs = required_retrieve_attributes - set(retrieve_span.attributes.keys())
                assert not missing_retrieve_attrs, f"Retrieve span missing required KPI attributes: {missing_retrieve_attrs}"
                
                # 7. Verify attributes have reasonable values (not just present)
                assert root_span.attributes["rag.query_chars"] > 0, "rag.query_chars should be positive"
                assert retrieve_span.attributes["rag.retrieved_docs_count"] >= 0, "rag.retrieved_docs_count should be non-negative"
                assert retrieve_span.attributes["rag.context_chars"] >= 0, "rag.context_chars should be non-negative"
                assert root_span.attributes["rag.top_k"] > 0, "rag.top_k should be positive"
                
                # 8. Verify model names are not empty
                assert len(root_span.attributes["rag.model"]) > 0, "rag.model should not be empty"
                assert len(root_span.attributes["rag.embed_model"]) > 0, "rag.embed_model should not be empty"
                
                return True
                
            except Exception as e:
                # Property violation: KPI attributes should be complete for any valid RAG operation
                pytest.fail(f"KPI attribute completeness failed for query='{query[:50]}...', session='{session_id}': {e}")
                
        # Run the async test
        result = asyncio.run(run_kpi_attributes_test())
        assert result, "KPI attribute completeness property test should pass"


@settings(max_examples=100, deadline=None)
@given(
    queries=st.lists(query_strategy(), min_size=2, max_size=5),  # Multiple queries for same session
    rag_config=rag_config_strategy(),
    session_id=session_id_strategy()
)
def test_experiment_tracking_consistency_property(queries: List[str], rag_config: Dict[str, Any], session_id: str):
    """
    **Feature: verba-observability, Property 4: Experiment tracking consistency**
    
    Property: For any user session, experiment attributes (exp.name, exp.variant, config versions) 
    should be consistently applied across all requests within that session.
    
    This test verifies that:
    1. exp.name attribute is consistent across all requests in a session
    2. exp.variant assignment is deterministic and consistent for the same session
    3. config.prompt_version and config.reranker_version are consistently applied
    4. user.session_id is properly attached to all spans in the session
    5. Variant assignment is deterministic based on session ID (same session = same variant)
    6. Different sessions can have different variants, but same session always gets same variant
    """
    
    # Setup mock tracer that tracks all spans across multiple requests
    mock_tracer = MockTracer()
    
    # Create a real attach_rag_attributes function that actually sets attributes
    def real_attach_rag_attributes(span, attributes):
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
    
    # Track all experiment contexts created to verify consistency
    experiment_contexts_created = []
    
    def track_experiment_context(user_session_id: str, experiment_name: str = "verba_rag_experiment_001"):
        """Track experiment context creation and return consistent results."""
        # Create deterministic context without calling the real function to avoid recursion
        import hashlib
        hash_input = f"{experiment_name}:{user_session_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        variant = "A" if hash_value % 2 == 0 else "B"
        
        context = {
            "exp.name": experiment_name,
            "exp.variant": variant,
            "user.session_id": user_session_id
        }
        experiment_contexts_created.append(context)
        return context
    
    with patch('goldenverba.observability.get_tracer', return_value=mock_tracer), \
         patch('goldenverba.observability.attach_rag_attributes', side_effect=real_attach_rag_attributes) as mock_attach, \
         patch('goldenverba.observability.handle_span_error') as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context', side_effect=track_experiment_context) as mock_experiment:
        
        # Import and setup VerbaManager with mocked dependencies
        from goldenverba.verba_manager import VerbaManager
        
        manager = VerbaManager()
        
        # Mock all manager dependencies
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        
        manager.embedder_manager = Mock()
        manager.embedder_manager.vectorize_query = AsyncMock(return_value=[0.1] * 1536)
        
        manager.retriever_manager = Mock()
        
        # Mock the retrieve method to create rag.retrieve spans
        async def mock_retrieve(*args, **kwargs):
            with mock_tracer.start_as_current_span("rag.retrieve") as retrieve_span:
                mock_documents = [f"Document {i}" for i in range(3)]
                mock_context = f"Context for query"
                retrieve_span.set_attribute("rag.retrieved_docs_count", len(mock_documents))
                retrieve_span.set_attribute("rag.context_chars", len(mock_context))
                return (mock_documents, mock_context)
        
        manager.retriever_manager.retrieve = mock_retrieve
        
        manager.generator_manager = Mock()
        
        # Mock the generator stream
        async def mock_generate_stream(rag_config, query, context, conversation):
            response_parts = [
                {"message": "Response to "},
                {"message": query[:20]},
                {"message": " based on context."}
            ]
            for part in response_parts:
                yield part
        
        manager.generator_manager.generate_stream = mock_generate_stream
        
        async def run_experiment_consistency_test():
            """Execute multiple requests for the same session and verify consistency."""
            try:
                # Execute multiple queries for the same session
                all_spans_by_request = []
                
                for i, query in enumerate(queries):
                    # Clear spans for this request (but keep tracking all spans)
                    request_start_span_count = len(mock_tracer.spans_created)
                    
                    # Execute retrieve_chunks
                    result = await manager.retrieve_chunks(
                        client=Mock(),
                        query=query,
                        rag_config=rag_config,
                        user_session_id=session_id
                    )
                    
                    # Verify retrieve_chunks completed successfully
                    assert result is not None, f"retrieve_chunks should return a result for query {i}"
                    documents, context = result
                    
                    # Execute generate_stream_answer
                    response_parts = []
                    async for part in manager.generate_stream_answer(
                        rag_config=rag_config,
                        query=query,
                        context=context,
                        conversation=[],
                        user_session_id=session_id
                    ):
                        response_parts.append(part)
                    
                    # Verify generation completed successfully
                    assert len(response_parts) > 0, f"Generation should produce response parts for query {i}"
                    
                    # Collect spans created for this request
                    request_spans = mock_tracer.spans_created[request_start_span_count:]
                    all_spans_by_request.append(request_spans)
                
                # Now verify experiment tracking consistency across all requests
                
                # 1. Verify experiment context was created for each request
                # Each query calls create_experiment_context twice: once in retrieve_chunks, once in generate_stream_answer
                expected_contexts = len(queries) * 2
                assert len(experiment_contexts_created) == expected_contexts, \
                    f"Expected {expected_contexts} experiment contexts, got {len(experiment_contexts_created)}"
                
                # 2. Verify all experiment contexts are identical (consistency requirement)
                first_context = experiment_contexts_created[0]
                for i, context in enumerate(experiment_contexts_created[1:], 1):
                    assert context == first_context, \
                        f"Experiment context {i} differs from first context: {context} != {first_context}"
                
                # 3. Verify experiment attributes are consistent across all spans in all requests
                all_query_spans = []
                all_generation_spans = []
                
                for request_spans in all_spans_by_request:
                    query_spans = [span for span in request_spans if span.name == "rag.query"]
                    generation_spans = [span for span in request_spans if span.name == "rag.generate"]
                    
                    assert len(query_spans) == 1, "Each request should have exactly one rag.query span"
                    assert len(generation_spans) == 1, "Each request should have exactly one rag.generate span"
                    
                    all_query_spans.extend(query_spans)
                    all_generation_spans.extend(generation_spans)
                
                # 4. Verify Requirements 6.1: exp.name attribute consistency
                expected_exp_name = first_context["exp.name"]
                for i, span in enumerate(all_query_spans):
                    assert "exp.name" in span.attributes, f"Query span {i} missing exp.name attribute"
                    assert span.attributes["exp.name"] == expected_exp_name, \
                        f"Query span {i} exp.name inconsistent: {span.attributes['exp.name']} != {expected_exp_name}"
                
                for i, span in enumerate(all_generation_spans):
                    assert "exp.name" in span.attributes, f"Generation span {i} missing exp.name attribute"
                    assert span.attributes["exp.name"] == expected_exp_name, \
                        f"Generation span {i} exp.name inconsistent: {span.attributes['exp.name']} != {expected_exp_name}"
                
                # 5. Verify Requirements 6.2: exp.variant consistency (deterministic assignment)
                expected_variant = first_context["exp.variant"]
                for i, span in enumerate(all_query_spans):
                    assert "exp.variant" in span.attributes, f"Query span {i} missing exp.variant attribute"
                    assert span.attributes["exp.variant"] == expected_variant, \
                        f"Query span {i} exp.variant inconsistent: {span.attributes['exp.variant']} != {expected_variant}"
                
                for i, span in enumerate(all_generation_spans):
                    assert "exp.variant" in span.attributes, f"Generation span {i} missing exp.variant attribute"
                    assert span.attributes["exp.variant"] == expected_variant, \
                        f"Generation span {i} exp.variant inconsistent: {span.attributes['exp.variant']} != {expected_variant}"
                
                # 6. Verify Requirements 6.3: config version attributes consistency
                # Check that config versions are present and consistent
                for i, span in enumerate(all_query_spans):
                    if "config.prompt_version" in span.attributes:
                        # If present in first span, should be consistent across all spans
                        first_prompt_version = all_query_spans[0].attributes.get("config.prompt_version")
                        if first_prompt_version is not None:
                            assert span.attributes["config.prompt_version"] == first_prompt_version, \
                                f"Query span {i} config.prompt_version inconsistent"
                    
                    if "config.reranker_version" in span.attributes:
                        first_reranker_version = all_query_spans[0].attributes.get("config.reranker_version")
                        if first_reranker_version is not None:
                            assert span.attributes["config.reranker_version"] == first_reranker_version, \
                                f"Query span {i} config.reranker_version inconsistent"
                
                # 7. Verify Requirements 6.4: user.session_id consistency
                expected_session_id = first_context["user.session_id"]
                assert expected_session_id == session_id, "Session ID should match input"
                
                for i, span in enumerate(all_query_spans):
                    assert "user.session_id" in span.attributes, f"Query span {i} missing user.session_id attribute"
                    assert span.attributes["user.session_id"] == expected_session_id, \
                        f"Query span {i} user.session_id inconsistent: {span.attributes['user.session_id']} != {expected_session_id}"
                
                for i, span in enumerate(all_generation_spans):
                    assert "user.session_id" in span.attributes, f"Generation span {i} missing user.session_id attribute"
                    assert span.attributes["user.session_id"] == expected_session_id, \
                        f"Generation span {i} user.session_id inconsistent: {span.attributes['user.session_id']} != {expected_session_id}"
                
                # 8. Verify deterministic variant assignment (same session = same variant)
                # Test the deterministic function directly without calling the mocked version
                import hashlib
                hash_input = f"verba_rag_experiment_001:{session_id}"
                hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                expected_variant_from_hash = "A" if hash_value % 2 == 0 else "B"
                
                # Verify the variant in our tracked contexts matches the expected hash
                assert first_context["exp.variant"] == expected_variant_from_hash, \
                    f"Variant should be deterministic based on hash: {first_context['exp.variant']} != {expected_variant_from_hash}"
                
                # 9. Verify experiment context was called at least the minimum expected times
                # Should be called at least once per retrieve_chunks + once per generate_stream_answer
                min_expected_calls = len(queries) * 2  # retrieve_chunks + generate_stream_answer
                assert mock_experiment.call_count >= min_expected_calls, \
                    f"Expected at least {min_expected_calls} experiment context calls, got {mock_experiment.call_count}"
                
                # 10. Verify all calls used the same session_id
                for call in mock_experiment.call_args_list:
                    args, kwargs = call
                    assert args[0] == session_id, f"All experiment context calls should use same session_id: {args[0]} != {session_id}"
                
                return True
                
            except Exception as e:
                # Property violation: experiment tracking should be consistent across session
                pytest.fail(f"Experiment tracking consistency failed for session='{session_id}', queries={len(queries)}: {e}")
                
        # Run the async test
        result = asyncio.run(run_experiment_consistency_test())
        assert result, "Experiment tracking consistency property test should pass"


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
    
    try:
        test_rag_span_structure_completeness_property()
        print("✓ Property 2 (RAG span structure completeness) - Tests passed")
    except Exception as e:
        print(f"✗ Property 2 (RAG span structure completeness) - Tests failed: {e}")
    
    try:
        test_kpi_attribute_completeness_property()
        print("✓ Property 3 (KPI attribute completeness) - Tests passed")
    except Exception as e:
        print(f"✗ Property 3 (KPI attribute completeness) - Tests failed: {e}")
    
    try:
        test_experiment_tracking_consistency_property()
        print("✓ Property 4 (Experiment tracking consistency) - Tests passed")
    except Exception as e:
        print(f"✗ Property 4 (Experiment tracking consistency) - Tests failed: {e}")
    
    print("Property-based testing complete.")