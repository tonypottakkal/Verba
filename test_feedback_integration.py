#!/usr/bin/env python3
"""
Test script for feedback API endpoint and span creation functionality.
"""

import sys
import os
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

# Add the goldenverba package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_feedback_payload_validation():
    """Test FeedbackPayload validation."""
    from goldenverba.server.types import FeedbackPayload, Credentials
    
    # Test valid payload
    credentials = Credentials(deployment="Local", url="http://localhost:8080", key="")
    
    valid_payload = FeedbackPayload(
        trace_id="test-trace-123",
        rating=4.5,
        feedback_tag="helpful",
        comments="This was very helpful!",
        credentials=credentials
    )
    
    assert valid_payload.trace_id == "test-trace-123"
    assert valid_payload.rating == 4.5
    assert valid_payload.feedback_tag == "helpful"
    assert valid_payload.comments == "This was very helpful!"
    print("✓ FeedbackPayload validation test passed")


def test_feedback_span_creation():
    """Test feedback span creation functionality."""
    # Mock the OpenTelemetry components to avoid dependency issues
    with patch('goldenverba.observability.get_tracer') as mock_get_tracer:
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)
        mock_get_tracer.return_value = mock_tracer
        
        # Import observability functions directly
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
        from goldenverba.observability import record_feedback, create_feedback_span
        
        # Test basic feedback recording
        result = record_feedback(
            trace_id="test-trace-123",
            rating=4.0,
            feedback_tag="helpful",
            comments="Great response!"
        )
        
        assert result == True
        assert mock_tracer.start_as_current_span.called
        print("✓ Basic feedback recording test passed")
        
        # Test enhanced feedback span creation
        result = create_feedback_span(
            trace_id="test-trace-456",
            rating=2.0,
            feedback_tag="inaccurate",
            comments="The answer was not helpful",
            user_session_id="session-789"
        )
        
        assert result == True
        print("✓ Enhanced feedback span creation test passed")


async def test_feedback_api_endpoint():
    """Test the feedback API endpoint functionality."""
    from goldenverba.server.types import FeedbackPayload, Credentials
    
    # Mock the client manager and observability functions
    with patch('goldenverba.server.api.client_manager') as mock_client_manager, \
         patch('goldenverba.observability.record_feedback') as mock_record_feedback, \
         patch('goldenverba.observability.create_feedback_span') as mock_create_feedback_span:
        
        # Setup mocks
        mock_client_manager.connect = AsyncMock(return_value=Mock())
        mock_record_feedback.return_value = True
        mock_create_feedback_span.return_value = True
        
        from goldenverba.server.api import submit_feedback
        
        # Create test payload
        credentials = Credentials(deployment="Local", url="http://localhost:8080", key="")
        payload = FeedbackPayload(
            trace_id="test-trace-789",
            rating=3.5,
            feedback_tag="neutral",
            comments="It was okay",
            credentials=credentials
        )
        
        # Test the endpoint
        response = await submit_feedback(payload)
        
        # Verify the response
        assert response.status_code == 200
        response_data = json.loads(response.body)
        assert response_data["feedback_recorded"] == True
        assert response_data["enhanced_correlation"] == True
        assert response_data["trace_id"] == "test-trace-789"
        
        print("✓ Feedback API endpoint test passed")


def test_rating_validation():
    """Test rating validation in feedback payload."""
    from goldenverba.server.types import FeedbackPayload, Credentials
    from pydantic import ValidationError
    
    credentials = Credentials(deployment="Local", url="http://localhost:8080", key="")
    
    # Test valid ratings
    for rating in [1.0, 2.5, 3.0, 4.5, 5.0]:
        payload = FeedbackPayload(
            trace_id="test-trace",
            rating=rating,
            credentials=credentials
        )
        assert payload.rating == rating
    
    print("✓ Rating validation test passed")


def main():
    """Run all tests."""
    print("Running feedback integration tests...")
    
    try:
        test_feedback_payload_validation()
        test_feedback_span_creation()
        asyncio.run(test_feedback_api_endpoint())
        test_rating_validation()
        
        print("\n✅ All feedback integration tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())