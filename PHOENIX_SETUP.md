# Phoenix Observability Setup Guide

This guide explains how to set up Arize Phoenix observability for Verba to enable comprehensive RAG pipeline monitoring and tracing.

## Overview

The Phoenix integration provides:
- End-to-end RAG pipeline tracing
- Performance monitoring and analysis
- Request debugging capabilities
- Quality monitoring hooks
- Experiment tracking support

## Quick Start

### 1. Start Services with Phoenix

```bash
# Start all services including Phoenix
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d

# Or start Phoenix separately first
docker-compose -f docker-compose.phoenix.yml up -d phoenix
docker-compose -f docker-compose.yml up -d
```

### 2. Verify Setup

```bash
# Run the verification script
python verify_phoenix_setup.py
```

### 3. Access Phoenix UI

Open your browser and navigate to: http://localhost:6006

## Configuration

### Environment Variables

The following OpenTelemetry environment variables are automatically configured when using `docker-compose.phoenix.yml`:

```bash
OTEL_SERVICE_NAME=verba
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=none
OTEL_LOGS_EXPORTER=none
OTEL_RESOURCE_ATTRIBUTES=service.name=verba,service.version=1.0.0
```

### Network Configuration

Phoenix runs on the same `ollama-docker` network as Verba and Weaviate, enabling:
- Internal service communication via container names
- OTLP trace export from Verba to Phoenix
- Preserved connectivity to external Ollama service

### Ports

- **6006**: Phoenix UI (web interface)
- **4317**: OTLP gRPC ingestion (internal network only)

## Verification

### Manual Verification Steps

1. **Check Phoenix UI**: Visit http://localhost:6006
2. **Verify OTLP Port**: Ensure port 4317 is accessible within Docker network
3. **Test Trace Export**: Make a query to Verba and check for traces in Phoenix
4. **Network Connectivity**: Verify all services can communicate

### Automated Verification

Use the provided verification script:

```bash
python verify_phoenix_setup.py
```

This script checks:
- Docker network existence
- Phoenix UI accessibility
- OTLP gRPC port availability

## Troubleshooting

### Phoenix UI Not Accessible

```bash
# Check if Phoenix container is running
docker ps | grep phoenix

# Check Phoenix logs
docker logs phoenix

# Restart Phoenix service
docker-compose -f docker-compose.phoenix.yml restart phoenix
```

### No Traces Appearing

1. Verify Verba has observability dependencies installed
2. Check Verba logs for OpenTelemetry initialization
3. Ensure OTLP environment variables are set correctly
4. Verify network connectivity between containers

### Port Conflicts

If port 6006 or 4317 are already in use:

1. Stop conflicting services
2. Or modify ports in `docker-compose.phoenix.yml`
3. Update environment variables accordingly

## Next Steps

After successful setup:

1. **Install Observability Dependencies**: Ensure Verba container includes required packages
2. **Implement Tracing**: Add OpenTelemetry instrumentation to Verba code
3. **Configure Experiments**: Set up A/B testing and experiment tracking
4. **Add Feedback**: Implement user feedback correlation system

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ollama-docker network                   │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Verba     │    │  Weaviate   │    │   Phoenix   │  │
│  │   :8000     │◄──►│    :8080    │    │    :6006    │  │
│  │             │    │             │    │    :4317    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                                      ▲        │
│         └──────── OTLP gRPC ──────────────────┘        │
└─────────────────────────────────────────────────────────┘
                            │
                    ┌─────────────┐
                    │   Ollama    │
                    │ (host:11434)│
                    └─────────────┘
```

## Requirements Satisfied

This setup satisfies the following requirements:

- **1.1**: Phoenix service container accessible on port 6006
- **1.2**: OTLP gRPC ingestion on port 4317 within container network
- **1.3**: Verba connects to Phoenix at http://phoenix:4317 for trace export
- **1.5**: Phoenix UI access at http://localhost:6006

The existing Ollama connectivity at http://host.docker.internal:11434 is preserved (Requirement 1.4).