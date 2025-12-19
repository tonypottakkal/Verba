#!/usr/bin/env python3
"""
Test script to verify observability integration in VerbaManager.
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

def test_retrieve_chunks_tracing():
    """Test that retrieve_chunks creates proper tracing spans."""
    print("Testing retrieve_chunks tracing integration...")
    
    # Mock the observability functions
    with patch('goldenverba.observability.get_tracer') as mock_get_tracer, \
         patch('goldenverba.observability.attach_rag_attributes') as mock_attach, \
         patch('goldenverba.observability.handle_span_error') as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context') as mock_experiment:
        
        # Setup mocks
        mock_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)
        mock_get_tracer.return_value = mock_tracer
        
        mock_experiment.return_value = {
            "exp.name": "verba_rag_experiment_001",
            "exp.variant": "A",
            "user.session_id": "test_session"
        }
        
        # Import and test
        from goldenverba.verba_manager import VerbaManager
        
        # Create a mock VerbaManager with mocked dependencies
        manager = VerbaManager()
        manager.weaviate_manager = Mock()
        manager.weaviate_manager.add_suggestion = AsyncMock()
        manager.embedder_manager = Mock()
        manager.embedder_manager.vectorize_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        manager.retriever_manager = Mock()
        manager.retriever_manager.retrieve = AsyncMock(return_value=(["doc1"], "context"))
        
        # Test data
        rag_config = {
            "Retriever": Mock(selected="test_retriever", components={}),
            "Embedder": Mock(selected="test_embedder"),
            "Generator": Mock(selected="test_generator")
        }
        
        async def run_test():
            try:
                result = await manager.retrieve_chunks(
                    client=Mock(),
                    query="test query",
                    rag_config=rag_config,
                    user_session_id="test_session"
                )
                
                # Verify tracer was called
                mock_get_tracer.assert_called_once()
                mock_tracer.start_as_current_span.assert_called_once_with("rag.query")
                
                # Verify attributes were attached
                assert mock_attach.call_count >= 2  # Should be called for initial and result attributes
                
                # Verify experiment context was created
                mock_experiment.assert_called_once_with("test_session")
                
                print("✓ retrieve_chunks tracing test passed")
                return True
                
            except Exception as e:
                print(f"✗ retrieve_chunks tracing test failed: {e}")
                return False
        
        return asyncio.run(run_test())

def test_generate_stream_answer_tracing():
    """Test that generate_stream_answer creates proper tracing spans."""
    print("Testing generate_stream_answer tracing integration...")
    
    with patch('goldenverba.observability.get_tracer') as mock_get_tracer, \
         patch('goldenverba.observability.attach_rag_attributes') as mock_attach, \
         patch('goldenverba.observability.handle_span_error') as mock_handle_error, \
         patch('goldenverba.observability.create_experiment_context') as mock_experiment:
        
        # Setup mocks
        mock_span = Mock()
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)
        mock_get_tracer.return_value = mock_tracer
        
        mock_experiment.return_value = {
            "exp.name": "verba_rag_experiment_001",
            "exp.variant": "B",
            "user.session_id": "test_session"
        }
        
        from goldenverba.verba_manager import VerbaManager
        
        manager = VerbaManager()
        manager.generator_manager = Mock()
        
        # Mock async generator
        async def mock_generate_stream(*args, **kwargs):
            yield {"message": "Hello", "finish_reason": "continue"}
            yield {"message": " World", "finish_reason": "stop"}
        
        manager.generator_manager.generate_stream = mock_generate_stream
        
        rag_config = {
            "Generator": Mock(selected="test_generator", components={}),
            "Retriever": Mock(selected="test_retriever")
        }
        
        async def run_test():
            try:
                result_messages = []
                async for chunk in manager.generate_stream_answer(
                    rag_config=rag_config,
                    query="test query",
                    context="test context",
                    conversation=[],
                    user_session_id="test_session"
                ):
                    result_messages.append(chunk["message"])
                
                # Verify tracer was called
                mock_get_tracer.assert_called_once()
                mock_tracer.start_as_current_span.assert_called_once_with("rag.generate")
                
                # Verify attributes were attached
                assert mock_attach.call_count >= 2  # Initial and final attributes
                
                # Verify experiment context was created
                mock_experiment.assert_called_once_with("test_session")
                
                # Verify streaming worked
                assert result_messages == ["Hello", " World"]
                
                print("✓ generate_stream_answer tracing test passed")
                return True
                
            except Exception as e:
                print(f"✗ generate_stream_answer tracing test failed: {e}")
                return False
        
        return asyncio.run(run_test())

def main():
    """Run all tests."""
    print("Running observability integration tests...\n")
    
    tests = [
        test_retrieve_chunks_tracing,
        test_generate_stream_answer_tracing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())