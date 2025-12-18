# Verba Feedback API Usage Guide

## Overview

The Verba feedback system allows users to submit ratings and comments that are correlated with specific RAG traces in Phoenix. This enables quality analysis and performance correlation between user satisfaction and system behavior.

## API Endpoint

### POST /api/submit_feedback

Submit user feedback linked to a specific trace ID.

#### Request Payload

```json
{
  "trace_id": "string",           // Required: The trace ID to link feedback to
  "rating": 4.5,                  // Required: Rating between 1.0 and 5.0
  "feedback_tag": "helpful",      // Optional: Categorical feedback tag
  "comments": "Great response!",  // Optional: User comments
  "credentials": {                // Required: Weaviate credentials
    "deployment": "Local",
    "url": "http://localhost:8080",
    "key": ""
  }
}
```

#### Response

**Success (200):**
```json
{
  "feedback_recorded": true,
  "enhanced_correlation": true,
  "trace_id": "trace-123",
  "message": "Feedback successfully recorded and linked to trace with enhanced correlation"
}
```

**Error (400/500):**
```json
{
  "error": "Rating must be between 1.0 and 5.0",
  "feedback_recorded": false
}
```

## Feedback Attributes in Phoenix

The feedback system creates spans with the following attributes for Phoenix analysis:

### Core Attributes
- `user.rating`: The numerical rating (1.0-5.0)
- `feedback.trace_id`: The original trace ID being rated
- `feedback.rating_category`: "positive", "neutral", or "negative"
- `user.satisfaction_level`: "satisfied", "neutral", or "dissatisfied"

### Optional Attributes
- `user.feedback_tag`: Categorical tag (e.g., "helpful", "inaccurate")
- `user.comments`: Free-text user comments
- `feedback.comment_sentiment`: Simple sentiment analysis of comments
- `user.session_id`: User session identifier (if available)

### Correlation Attributes
- `feedback.correlated`: Always true for linked feedback
- `feedback.source`: "verba_api"
- `feedback.timestamp`: Unix timestamp of feedback submission
- `feedback.recorded_successfully`: Success indicator

## Usage Examples

### JavaScript/Frontend Example

```javascript
async function submitFeedback(traceId, rating, tag, comments) {
  const response = await fetch('/api/submit_feedback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      trace_id: traceId,
      rating: rating,
      feedback_tag: tag,
      comments: comments,
      credentials: {
        deployment: "Local",
        url: "http://localhost:8080",
        key: ""
      }
    })
  });
  
  const result = await response.json();
  console.log('Feedback submitted:', result);
}

// Usage
submitFeedback("trace-abc-123", 4.5, "helpful", "Great answer!");
```

### Python Example

```python
import requests

def submit_feedback(trace_id, rating, feedback_tag=None, comments=None):
    payload = {
        "trace_id": trace_id,
        "rating": rating,
        "feedback_tag": feedback_tag,
        "comments": comments,
        "credentials": {
            "deployment": "Local",
            "url": "http://localhost:8080",
            "key": ""
        }
    }
    
    response = requests.post(
        "http://localhost:8000/api/submit_feedback",
        json=payload
    )
    
    return response.json()

# Usage
result = submit_feedback("trace-xyz-456", 3.0, "neutral", "It was okay")
print(result)
```

## Phoenix Analysis

Once feedback is submitted, you can analyze it in Phoenix by:

1. **Filtering by Rating Category:**
   - Filter traces by `feedback.rating_category = "negative"` to find problematic interactions
   - Use `user.satisfaction_level = "dissatisfied"` for detailed analysis

2. **Correlating Performance with Satisfaction:**
   - Compare trace timing with `user.rating` to identify performance issues
   - Analyze `feedback.comment_sentiment` trends

3. **Session Analysis:**
   - Group feedback by `user.session_id` to understand user journey satisfaction
   - Track rating patterns across multiple interactions

4. **Quality Monitoring:**
   - Set up alerts for low average ratings
   - Monitor `feedback.rating_category` distribution over time

## Integration with RAG Pipeline

The feedback system automatically correlates with existing RAG traces that contain:
- `rag.query` spans (root query operations)
- `rag.retrieve` spans (document retrieval)
- `rag.generate` spans (text generation)

This allows you to identify which parts of the RAG pipeline correlate with user satisfaction.