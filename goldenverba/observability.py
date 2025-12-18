"""
OpenTelemetry observability integration for Verba RAG pipeline.

This module provides comprehensive tracing capabilities for monitoring
RAG operations, experiment tracking, and user feedback correlation.
"""
import os
import hashlib
import logging
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_INITIALIZED = False

logger = logging.getLogger(__name__)


def setup_tracing() -> bool:
    """
    Configure OTLP export to Phoenix with comprehensive error handling.
    Make sure this runs BEFORE creating your retriever/chain/LLM client.

    Returns:
        bool: True if tracing setup was successful, False otherwise
    """
    global _tracer, _INITIALIZED

    if _INITIALIZED:
        logger.info("Tracing already initialized")
        return True

    try:
        # Get configuration from environment variables
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://phoenix:4317")
        service_name = os.getenv("OTEL_SERVICE_NAME", "verba")

        # Create resource with service information
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0"
        })

        # Set up tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=True  # Use insecure connection for internal Docker network
        )

        # Add batch span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Register Phoenix instrumentation
        try:
            from phoenix.otel import register
            register(endpoint=endpoint, protocol="grpc")
            logger.info("Phoenix OTEL registered with endpoint: %s", endpoint)
        except ImportError:
            logger.warning("Phoenix OTEL not available, using standard OTLP export only")
        except Exception as e:
            logger.warning("Phoenix OTEL registration failed: %s", e)

        # Optional LangChain instrumentation
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            LangChainInstrumentor().instrument()
            logger.info("LangChain instrumentation enabled")
        except ImportError:
            logger.info("LangChain instrumentation not available")
        except Exception as e:
            logger.warning("LangChain instrumentation failed: %s", e)

        # Initialize global tracer
        _tracer = trace.get_tracer(__name__)
        _INITIALIZED = True

        logger.info("OpenTelemetry tracing initialized successfully with service: %s",
                   service_name)
        return True

    except Exception as e:
        logger.error("Failed to initialize tracing: %s", e)
        return False


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance for consistent span creation.

    Returns:
        trace.Tracer: The configured tracer instance
    """
    global _tracer

    if _tracer is None:
        # Fallback to default tracer if setup_tracing wasn't called
        logger.warning("Tracer not initialized, using default tracer")
        _tracer = trace.get_tracer(__name__)

    return _tracer


def create_experiment_context(user_session_id: str,
                            experiment_name: str = "verba_rag_experiment_001") -> Dict[str, str]:
    """
    Generate experiment context for A/B testing with deterministic variant assignment.

    Args:
        user_session_id: Unique identifier for the user session
        experiment_name: Name of the experiment

    Returns:
        Dict containing experiment attributes
    """
    # Use deterministic hashing for consistent variant assignment
    hash_input = f"{experiment_name}:{user_session_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    variant = "A" if hash_value % 2 == 0 else "B"

    return {
        "exp.name": experiment_name,
        "exp.variant": variant,
        "user.session_id": user_session_id
    }


def record_feedback(trace_id: str, rating: float, feedback_tag: Optional[str] = None,
                   comments: Optional[str] = None) -> bool:
    """
    Record user feedback linked to a specific trace.

    Args:
        trace_id: The trace ID to link feedback to
        rating: User rating (e.g., 1-5 scale)
        feedback_tag: Optional categorical feedback tag
        comments: Optional user comments

    Returns:
        bool: True if feedback was recorded successfully
    """
    try:
        current_tracer = get_tracer()

        with current_tracer.start_as_current_span("user.feedback") as span:
            span.set_attribute("user.rating", rating)
            span.set_attribute("feedback.trace_id", trace_id)

            if feedback_tag:
                span.set_attribute("user.feedback_tag", feedback_tag)

            if comments:
                span.set_attribute("user.comments", comments)

            logger.info("Feedback recorded for trace %s: rating=%s", trace_id, rating)
            return True

    except Exception as e:
        logger.error("Failed to record feedback: %s", e)
        return False


def attach_rag_attributes(span: trace.Span, attributes: Dict[str, Any]) -> None:
    """
    Attach RAG-specific attributes to a span with proper type handling.

    Args:
        span: The span to attach attributes to
        attributes: Dictionary of attributes to attach
    """
    try:
        for key, value in attributes.items():
            if value is not None:
                # Convert values to appropriate types for OpenTelemetry
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))
    except Exception as e:
        logger.warning("Failed to attach attributes: %s", e)


def handle_span_error(span: trace.Span, error: Exception) -> None:
    """
    Mark a span with error information without disrupting application flow.

    Args:
        span: The span to mark with error
        error: The exception that occurred
    """
    try:
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
        span.set_attribute("error.type", type(error).__name__)
        span.set_attribute("error.message", str(error))
        span.record_exception(error)
    except Exception as e:
        logger.warning("Failed to record span error: %s", e)


# Backwards compatibility
tracer = get_tracer()