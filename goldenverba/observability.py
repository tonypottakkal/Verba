"""
OpenTelemetry observability integration for Verba RAG pipeline.

This module provides comprehensive tracing capabilities for monitoring
RAG operations, experiment tracking, and user feedback correlation.
"""
import os
import hashlib
import logging
import time
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


class CircuitBreaker:
    """
    Circuit breaker for trace export resilience.
    Prevents continuous failures from disrupting the application.
    """
    
    def __init__(self, failure_threshold: int = None, recovery_timeout: int = None):
        # Allow configuration via environment variables
        self.failure_threshold = failure_threshold or int(os.getenv("OTEL_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        self.recovery_timeout = recovery_timeout or int(os.getenv("OTEL_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info("Circuit breaker initialized with failure_threshold=%d, recovery_timeout=%d", 
                   self.failure_threshold, self.recovery_timeout)
    
    def call(self, func, *args, **kwargs):
        """Execute a function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                logger.debug("Circuit breaker is OPEN, skipping trace export")
                return None
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            logger.warning("Circuit breaker recorded failure: %s", str(e))
            return None
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker opened after %d failures", self.failure_count)
    
    def reset(self):
        """Reset the circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker reset to CLOSED state")


class ResilientSpanProcessor(BatchSpanProcessor):
    """
    A resilient span processor that handles export failures gracefully.
    """
    
    def __init__(self, span_exporter, circuit_breaker: CircuitBreaker = None, **kwargs):
        super().__init__(span_exporter, **kwargs)
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.original_export = span_exporter.export
        
        # Wrap the exporter's export method with circuit breaker
        def resilient_export(spans):
            return self.circuit_breaker.call(self.original_export, spans)
        
        span_exporter.export = resilient_export
    
    def on_end(self, span):
        """Override to add additional error handling."""
        try:
            super().on_end(span)
        except Exception as e:
            logger.warning("Failed to process span: %s", str(e))
            # Continue without disrupting the application


# Global circuit breaker instance
_circuit_breaker = CircuitBreaker()


def is_tracing_healthy() -> bool:
    """
    Check if the tracing system is healthy and operational.
    
    Returns:
        bool: True if tracing is healthy, False otherwise
    """
    global _INITIALIZED, _circuit_breaker
    
    if not _INITIALIZED:
        return False
    
    if _circuit_breaker.state == "OPEN":
        return False
    
    return True


def get_tracing_status() -> Dict[str, Any]:
    """
    Get detailed status information about the tracing system.
    
    Returns:
        Dict containing tracing system status
    """
    global _INITIALIZED, _circuit_breaker
    
    return {
        "initialized": _INITIALIZED,
        "circuit_breaker_state": _circuit_breaker.state,
        "circuit_breaker_failure_count": _circuit_breaker.failure_count,
        "circuit_breaker_last_failure": _circuit_breaker.last_failure_time,
        "healthy": is_tracing_healthy()
    }


def reset_tracing_errors():
    """
    Reset the circuit breaker and clear any error states.
    Useful for manual recovery or testing.
    """
    global _circuit_breaker
    
    _circuit_breaker.reset()
    logger.info("Tracing error state reset manually")


def shutdown_tracing():
    """
    Safely shutdown the tracing system and flush any pending spans.
    """
    global _tracer, _INITIALIZED
    
    if not _INITIALIZED:
        logger.info("Tracing not initialized, nothing to shutdown")
        return
    
    try:
        # Get the tracer provider and force flush
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, 'force_flush'):
            tracer_provider.force_flush(timeout_millis=5000)
            logger.info("Tracing spans flushed successfully")
        
        # Shutdown the tracer provider
        if hasattr(tracer_provider, 'shutdown'):
            tracer_provider.shutdown()
            logger.info("Tracing system shutdown successfully")
        
        _INITIALIZED = False
        _tracer = None
        
    except Exception as e:
        logger.error("Error during tracing shutdown: %s", e)


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

    # Check if tracing is disabled via environment variable
    if os.getenv("OTEL_TRACING_DISABLED", "false").lower() == "true":
        logger.info("Tracing disabled via OTEL_TRACING_DISABLED environment variable")
        return False

    try:
        # Get configuration from environment variables
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://phoenix:4317")
        service_name = os.getenv("OTEL_SERVICE_NAME", "verba")
        service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")

        # Create resource with service information
        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "service.instance.id": hashlib.md5(f"{service_name}-{time.time()}".encode()).hexdigest()[:8]
        })

        # Set up tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # Configure OTLP exporter with timeout and retry settings
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                insecure=True,  # Use insecure connection for internal Docker network
                timeout=int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10"))  # 10 second timeout
            )
        except Exception as exporter_error:
            logger.error("Failed to create OTLP exporter: %s", exporter_error)
            return False

        # Add resilient batch span processor with circuit breaker
        try:
            # Configure batch processor settings
            max_queue_size = int(os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048"))
            max_export_batch_size = int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512"))
            export_timeout_millis = int(os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "30000"))
            schedule_delay_millis = int(os.getenv("OTEL_BSP_SCHEDULE_DELAY", "5000"))
            
            span_processor = ResilientSpanProcessor(
                otlp_exporter, 
                _circuit_breaker,
                max_queue_size=max_queue_size,
                max_export_batch_size=max_export_batch_size,
                export_timeout_millis=export_timeout_millis,
                schedule_delay_millis=schedule_delay_millis
            )
            tracer_provider.add_span_processor(span_processor)
            logger.info("Resilient span processor configured with queue_size=%d, batch_size=%d", 
                       max_queue_size, max_export_batch_size)
        except Exception as processor_error:
            logger.error("Failed to configure span processor: %s", processor_error)
            return False

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

        logger.info("OpenTelemetry tracing initialized successfully with service: %s, endpoint: %s",
                   service_name, endpoint)
        return True

    except Exception as e:
        logger.error("Failed to initialize tracing: %s", e)
        # Reset state on failure
        _INITIALIZED = False
        _tracer = None
        return False


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance for consistent span creation.
    Provides graceful degradation if tracing is not available.

    Returns:
        trace.Tracer: The configured tracer instance or a no-op tracer
    """
    global _tracer

    if _tracer is None:
        # Check if tracing is disabled
        if os.getenv("OTEL_TRACING_DISABLED", "false").lower() == "true":
            logger.debug("Tracing disabled, returning no-op tracer")
            return trace.NoOpTracer()
        
        # Check circuit breaker state
        if not is_tracing_healthy():
            logger.debug("Tracing unhealthy, returning no-op tracer")
            return trace.NoOpTracer()
        
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
    Creates feedback spans that can be correlated with original request traces in Phoenix.

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

        # Create feedback span with proper naming for Phoenix correlation
        with current_tracer.start_as_current_span("user.feedback") as span:
            # Core feedback attributes
            span.set_attribute("user.rating", rating)
            span.set_attribute("feedback.trace_id", trace_id)
            span.set_attribute("feedback.type", "user_rating")
            
            # Add timestamp for correlation
            import time
            span.set_attribute("feedback.timestamp", int(time.time()))
            
            # Categorize rating for easier filtering in Phoenix
            if rating >= 4.0:
                rating_category = "positive"
            elif rating >= 3.0:
                rating_category = "neutral"
            else:
                rating_category = "negative"
            span.set_attribute("feedback.rating_category", rating_category)

            # Optional feedback attributes
            if feedback_tag:
                span.set_attribute("user.feedback_tag", feedback_tag)

            if comments:
                span.set_attribute("user.comments", comments)
                # Add comment length for analytics
                span.set_attribute("feedback.comment_length", len(comments))

            # Add correlation attributes for Phoenix filtering
            span.set_attribute("feedback.correlated", True)
            span.set_attribute("feedback.source", "api_endpoint")
            
            # Mark span as successful
            span.set_attribute("feedback.success", True)

            logger.info("Feedback recorded for trace %s: rating=%s, category=%s", 
                       trace_id, rating, rating_category)
            return True

    except Exception as e:
        logger.error("Failed to record feedback: %s", e)
        
        # Create error span for failed feedback recording
        try:
            current_tracer = get_tracer()
            with current_tracer.start_as_current_span("user.feedback.error") as error_span:
                error_span.set_attribute("feedback.trace_id", trace_id)
                error_span.set_attribute("feedback.success", False)
                handle_span_error(error_span, e)
        except Exception:
            # Silently fail if we can't even create error span
            pass
        
        return False


def create_feedback_span(trace_id: str, rating: float, feedback_tag: Optional[str] = None,
                        comments: Optional[str] = None, user_session_id: Optional[str] = None) -> bool:
    """
    Create a feedback span with enhanced correlation attributes for Phoenix.
    This function creates spans that are specifically designed to work well with Phoenix's
    feedback correlation features.

    Args:
        trace_id: The trace ID to link feedback to
        rating: User rating (1-5 scale)
        feedback_tag: Optional categorical feedback tag
        comments: Optional user comments
        user_session_id: Optional user session identifier

    Returns:
        bool: True if feedback span was created successfully
    """
    try:
        current_tracer = get_tracer()

        # Create feedback span with Phoenix-optimized attributes
        with current_tracer.start_as_current_span("feedback.user_rating") as span:
            # Phoenix-specific feedback attributes
            span.set_attribute("feedback.trace_id", trace_id)
            span.set_attribute("user.rating", rating)
            span.set_attribute("feedback.type", "user_rating")
            
            # Add session correlation if available
            if user_session_id:
                span.set_attribute("user.session_id", user_session_id)
            
            # Timestamp for temporal correlation
            import time
            span.set_attribute("feedback.timestamp", int(time.time()))
            
            # Rating categorization for Phoenix filtering
            if rating >= 4.0:
                rating_category = "positive"
                satisfaction_level = "satisfied"
            elif rating >= 3.0:
                rating_category = "neutral"
                satisfaction_level = "neutral"
            else:
                rating_category = "negative"
                satisfaction_level = "dissatisfied"
                
            span.set_attribute("feedback.rating_category", rating_category)
            span.set_attribute("user.satisfaction_level", satisfaction_level)

            # Optional feedback details
            if feedback_tag:
                span.set_attribute("user.feedback_tag", feedback_tag)
                span.set_attribute("feedback.has_tag", True)
            else:
                span.set_attribute("feedback.has_tag", False)

            if comments:
                span.set_attribute("user.comments", comments)
                span.set_attribute("feedback.has_comments", True)
                span.set_attribute("feedback.comment_length", len(comments))
                
                # Simple sentiment analysis based on keywords
                positive_keywords = ["good", "great", "excellent", "helpful", "accurate", "useful"]
                negative_keywords = ["bad", "poor", "wrong", "unhelpful", "inaccurate", "useless"]
                
                comments_lower = comments.lower()
                positive_count = sum(1 for word in positive_keywords if word in comments_lower)
                negative_count = sum(1 for word in negative_keywords if word in comments_lower)
                
                if positive_count > negative_count:
                    sentiment = "positive"
                elif negative_count > positive_count:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
                    
                span.set_attribute("feedback.comment_sentiment", sentiment)
            else:
                span.set_attribute("feedback.has_comments", False)

            # Phoenix correlation attributes
            span.set_attribute("feedback.correlated", True)
            span.set_attribute("feedback.source", "verba_api")
            span.set_attribute("feedback.version", "1.0")
            
            # Success indicator
            span.set_attribute("feedback.recorded_successfully", True)

            logger.info("Enhanced feedback span created for trace %s: rating=%s, category=%s", 
                       trace_id, rating, rating_category)
            return True

    except Exception as e:
        logger.error("Failed to create feedback span: %s", e)
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
        
        # Add stack trace for debugging
        import traceback
        stack_trace = traceback.format_exc()
        if stack_trace and stack_trace != "NoneType: None\n":
            span.set_attribute("error.stack", stack_trace)
        
        # Record the exception with OpenTelemetry
        span.record_exception(error)
        
        logger.error("Span error recorded: %s - %s", type(error).__name__, str(error))
    except Exception as e:
        logger.warning("Failed to record span error: %s", e)


def create_error_span(tracer: trace.Tracer, operation_name: str, error: Exception) -> None:
    """
    Create a dedicated error span for exceptions that occur outside of existing spans.
    
    Args:
        tracer: The tracer instance
        operation_name: Name of the operation where the error occurred
        error: The exception that occurred
    """
    try:
        with tracer.start_as_current_span(f"error.{operation_name}") as error_span:
            handle_span_error(error_span, error)
            error_span.set_attribute("error.operation", operation_name)
            error_span.set_attribute("error.severity", "error")
    except Exception as e:
        logger.warning("Failed to create error span: %s", e)


def safe_span_operation(span: trace.Span, operation_name: str, operation_func, *args, **kwargs):
    """
    Safely execute an operation within a span, handling any errors that occur.
    
    Args:
        span: The span to execute the operation within
        operation_name: Name of the operation for error reporting
        operation_func: The function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The result of the operation, or None if an error occurred
    """
    try:
        result = operation_func(*args, **kwargs)
        span.set_attribute(f"{operation_name}.success", True)
        return result
    except Exception as e:
        handle_span_error(span, e)
        span.set_attribute(f"{operation_name}.success", False)
        logger.error("Operation %s failed: %s", operation_name, str(e))
        raise  # Re-raise the exception to maintain original behavior


# Backwards compatibility
tracer = get_tracer()