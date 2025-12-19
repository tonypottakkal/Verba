# Phoenix Integration Usage Examples

This document provides practical examples of using Verba with Phoenix observability.

## Starting Services

### Option 1: Start All Services Together
```bash
# Start Verba, Weaviate, and Phoenix together
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d

# Check service status
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml ps
```

### Option 2: Start Services Separately
```bash
# Start Phoenix first
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d phoenix

# Wait for Phoenix to be healthy
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml ps phoenix

# Start remaining services
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d
```

## Verification

### Quick Health Check
```bash
# Run the verification script
python verify_phoenix_setup.py
```

### Manual Verification
```bash
# Check Phoenix UI
curl -f http://localhost:6006

# Check OTLP gRPC port (should show connection refused from outside, which is expected)
telnet localhost 4317

# Check container logs
docker logs phoenix
docker logs verba-verba-1
```

## Accessing Services

- **Verba UI**: http://localhost:8000
- **Phoenix UI**: http://localhost:6006
- **Weaviate**: http://localhost:8080

## Environment Variables

The following OpenTelemetry variables are automatically set when using the Phoenix compose file:

```bash
OTEL_SERVICE_NAME=verba
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=none
OTEL_LOGS_EXPORTER=none
OTEL_RESOURCE_ATTRIBUTES=service.name=verba,service.version=1.0.0
```

## Troubleshooting

### Phoenix Container Unhealthy
```bash
# Check Phoenix logs
docker logs phoenix

# Restart Phoenix
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml restart phoenix
```

### No Traces in Phoenix
1. Ensure Verba has observability dependencies installed
2. Check Verba logs for OpenTelemetry initialization messages
3. Verify network connectivity between containers
4. Make test queries to Verba and check Phoenix UI

### Port Conflicts
If ports 6006 or 4317 are in use:
1. Stop conflicting services
2. Or modify `docker-compose.phoenix.yml` to use different ports
3. Update environment variables accordingly

## Next Steps

After successful setup:
1. Install observability dependencies in Verba container
2. Implement OpenTelemetry instrumentation in Verba code
3. Test trace generation by making queries to Verba
4. Configure experiment tracking and feedback correlation