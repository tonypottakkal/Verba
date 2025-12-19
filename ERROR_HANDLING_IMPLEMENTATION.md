# Error Handling and Resilience Implementation

## Overview

This document describes the comprehensive error handling and trace export resilience features implemented for the Verba observability system.

## Task 6.1: Comprehensive Error Tracing

### Enhanced Error Handling Functions

#### `handle_span_error(span, error)`
- Marks spans with error status and detailed error information
- Attaches `error.type`, `error.message`, and `error.stack` attributes
- Records exceptions using OpenTelemetry's `record_exception()` method
- Includes comprehensive logging for debugging
- Gracefully handles failures without disrupting application flow

#### `create_error_span(tracer, operation_name, error)`
- Creates dedicated error spans for exceptions outside existing spans
- Useful for tracking errors that occur between operations
- Includes operation name and error severity attributes

#### `safe_span_operation(span, operation_name, operation_func, *args, **kwargs)`
- Safely executes operations within spans with automatic error handling
- Tracks success/failure status
- Re-raises exceptions to maintain original behavior

### Component-Level Error Handling

#### EmbeddingManager.vectorize_query()
Enhanced with:
- Input validation (empty content, whitespace-only content)
- Embedder availability checks with detailed error messages
- Configuration validation
- Vectorization error handling with detailed error types
- Result validation (empty results, invalid format)
- Comprehensive error attributes: `embedding.error_type`, `embedding.error_details`
- Fallback behavior when observability is unavailable

#### RetrieverManager.retrieve()
Enhanced with:
- Query and vector validation
- Retriever availability checks
- Configuration error handling
- Retrieval operation error handling with detailed error types
- Result validation (null results)
- Comprehensive error attributes: `rag.error_type`, `rag.error_details`
- Fallback behavior when observability is unavailable

#### GeneratorManager.generate_stream()
Enhanced with:
- Input validation (query, context)
- Generator availability checks
- Stream error tracking with counters
- Individual result processing error handling
- Error loop prevention (max 20 errors)
- Comprehensive error attributes: `generation.error_type`, `generation.stream_error_count`
- Fallback behavior when observability is unavailable

### VerbaManager Error Handling

#### retrieve_chunks()
Enhanced with:
- Suggestion error handling (non-blocking)
- Embedding error handling with detailed error messages
- Retrieval error handling with detailed error messages
- Error stage tracking: `rag.error_stage`
- Comprehensive error logging

#### generate_stream_answer()
Enhanced with:
- Stream error counting and tracking
- Individual stream result error handling
- Error loop prevention
- Error stage tracking: `rag.error_stage`
- Comprehensive error logging

## Task 6.3: Trace Export Resilience

### Circuit Breaker Implementation

#### CircuitBreaker Class
- **States**: CLOSED, OPEN, HALF_OPEN
- **Configurable thresholds**:
  - `failure_threshold`: Number of failures before opening (default: 5, env: `OTEL_CIRCUIT_BREAKER_FAILURE_THRESHOLD`)
  - `recovery_timeout`: Seconds before attempting recovery (default: 60, env: `OTEL_CIRCUIT_BREAKER_RECOVERY_TIMEOUT`)
- **Automatic state transitions**:
  - CLOSED → OPEN: After threshold failures
  - OPEN → HALF_OPEN: After recovery timeout
  - HALF_OPEN → CLOSED: On successful operation
- **Graceful degradation**: Returns None instead of failing when circuit is open

#### ResilientSpanProcessor Class
- Extends `BatchSpanProcessor` with circuit breaker protection
- Wraps span exporter's export method with resilience
- Handles export failures without disrupting application
- Configurable batch processing parameters:
  - `max_queue_size` (env: `OTEL_BSP_MAX_QUEUE_SIZE`, default: 2048)
  - `max_export_batch_size` (env: `OTEL_BSP_MAX_EXPORT_BATCH_SIZE`, default: 512)
  - `export_timeout_millis` (env: `OTEL_BSP_EXPORT_TIMEOUT`, default: 30000)
  - `schedule_delay_millis` (env: `OTEL_BSP_SCHEDULE_DELAY`, default: 5000)

### Enhanced setup_tracing()

New features:
- **Disable tracing**: `OTEL_TRACING_DISABLED=true` environment variable
- **Service instance ID**: Unique identifier for each service instance
- **Configurable timeouts**: `OTEL_EXPORTER_OTLP_TIMEOUT` (default: 10 seconds)
- **Resilient span processor**: Automatic integration with circuit breaker
- **Comprehensive error handling**: Graceful failure at each initialization step
- **State reset on failure**: Ensures clean state after initialization failures

### Health Monitoring Functions

#### `is_tracing_healthy()`
- Returns boolean indicating tracing system health
- Checks initialization status and circuit breaker state

#### `get_tracing_status()`
- Returns detailed status dictionary:
  - `initialized`: Whether tracing is initialized
  - `circuit_breaker_state`: Current circuit breaker state
  - `circuit_breaker_failure_count`: Number of failures
  - `circuit_breaker_last_failure`: Timestamp of last failure
  - `healthy`: Overall health status

#### `reset_tracing_errors()`
- Manually reset circuit breaker
- Clear error states
- Useful for recovery and testing

#### `shutdown_tracing()`
- Safely shutdown tracing system
- Flush pending spans (5 second timeout)
- Clean up resources
- Reset global state

### Enhanced get_tracer()

New features:
- **Graceful degradation**: Returns no-op tracer when tracing is disabled or unhealthy
- **Health checks**: Verifies circuit breaker state before returning tracer
- **Environment variable support**: Respects `OTEL_TRACING_DISABLED`

## Environment Variables

### Circuit Breaker Configuration
- `OTEL_CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Number of failures before opening (default: 5)
- `OTEL_CIRCUIT_BREAKER_RECOVERY_TIMEOUT`: Seconds before recovery attempt (default: 60)

### Tracing Configuration
- `OTEL_TRACING_DISABLED`: Disable tracing entirely (default: false)
- `OTEL_SERVICE_VERSION`: Service version for resource attributes (default: 1.0.0)
- `OTEL_EXPORTER_OTLP_TIMEOUT`: OTLP exporter timeout in seconds (default: 10)

### Batch Span Processor Configuration
- `OTEL_BSP_MAX_QUEUE_SIZE`: Maximum queue size (default: 2048)
- `OTEL_BSP_MAX_EXPORT_BATCH_SIZE`: Maximum batch size (default: 512)
- `OTEL_BSP_EXPORT_TIMEOUT`: Export timeout in milliseconds (default: 30000)
- `OTEL_BSP_SCHEDULE_DELAY`: Schedule delay in milliseconds (default: 5000)

## Error Attributes

### Standard Error Attributes
- `error.type`: Exception class name
- `error.message`: Exception message
- `error.stack`: Full stack trace

### Component-Specific Error Attributes
- `embedding.error_type`: Type of embedding error (invalid_input, embedder_not_found, config_error, vectorization_failed, empty_result, invalid_result_format)
- `embedding.error_details`: Detailed error information
- `rag.error_type`: Type of RAG error (invalid_query, invalid_vector, retriever_not_found, config_error, retrieval_failed, null_result)
- `rag.error_details`: Detailed error information
- `rag.error_stage`: Stage where error occurred (query_processing, generation_setup, generation)
- `generation.error_type`: Type of generation error (generator_not_found, stream_failed)
- `generation.error_details`: Detailed error information
- `generation.stream_error_count`: Number of stream errors encountered

### Success Tracking
All operations include a `*.success` attribute (boolean) to indicate success or failure:
- `embedding.success`
- `rag.success`
- `generation.success`
- `weaviate.success`

## Testing

### Test Script: test_error_handling.py
Comprehensive test suite covering:
- Circuit breaker functionality
- Error tracing
- Tracing status and health checks
- Component error handling

### Syntax Validation
All modified files pass Python syntax validation:
- `goldenverba/observability.py`
- `goldenverba/components/managers.py`
- `goldenverba/verba_manager.py`

### Integration Tests
Existing integration tests pass:
- `test_syntax_check.py`: All checks passed (3/3)

## Benefits

1. **Application Resilience**: Tracing failures don't disrupt application functionality
2. **Automatic Recovery**: Circuit breaker automatically attempts recovery
3. **Detailed Error Information**: Comprehensive error attributes for debugging
4. **Graceful Degradation**: System continues operating when tracing is unavailable
5. **Configurable Behavior**: Environment variables allow fine-tuning
6. **Health Monitoring**: Real-time visibility into tracing system health
7. **Production Ready**: Handles edge cases and error conditions robustly

## Requirements Validation

### Requirement 9.1 ✓
WHEN exceptions occur during processing THEN the system SHALL attach error.type and error.message attributes to relevant spans
- Implemented in `handle_span_error()` with additional `error.stack` attribute

### Requirement 9.2 ✓
WHEN retrieval fails THEN the system SHALL mark rag.retrieve spans with error status and exception details
- Implemented in `RetrieverManager.retrieve()` with comprehensive error handling

### Requirement 9.3 ✓
WHEN generation fails THEN the system SHALL mark rag.generate spans with error status and model error information
- Implemented in `GeneratorManager.generate_stream()` with stream error tracking

### Requirement 9.4 ✓
WHEN trace export fails THEN the system SHALL log export errors without disrupting application functionality
- Implemented via `CircuitBreaker` and `ResilientSpanProcessor`
- Graceful degradation with no-op tracer when unhealthy

## Future Enhancements

1. **Metrics Export**: Add metrics for circuit breaker state changes and error rates
2. **Alerting Integration**: Integrate with alerting systems for circuit breaker state changes
3. **Dynamic Configuration**: Support runtime configuration updates
4. **Error Rate Limiting**: Add rate limiting for error logging to prevent log flooding
5. **Retry Strategies**: Implement exponential backoff for trace export retries
