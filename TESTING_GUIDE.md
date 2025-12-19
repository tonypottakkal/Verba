# Verba Testing Guide

This guide explains how to run comprehensive tests for Verba with observability integration.

## Overview

The Verba testing suite provides three levels of verification:

1. **Containerized Unit Tests** - Run tests in isolated Docker containers
2. **Live Integration Tests** - Test with full Docker Compose deployment
3. **Complete Verification** - Comprehensive suite including property-based tests

## Quick Start

### Run Everything (Recommended)

```bash
# Complete verification suite - runs all tests
python run_complete_verification.py

# With verbose output
python run_complete_verification.py --verbose
```

### Quick Verification

```bash
# Fast verification of critical functionality
python run_complete_verification.py --quick
```

## Individual Test Runners

### 1. Containerized Unit Tests

Tests run in isolated Docker containers matching the production environment:

```bash
# Run all unit tests in containers
python run_containerized_tests.py

# Build test image only
python run_containerized_tests.py --build-only

# Run tests with existing image
python run_containerized_tests.py --test-only
```

**What it tests:**
- Dependency verification
- Observability integration
- Error handling
- Property-based correctness
- Syntax and import validation

### 2. Full Deployment Tests

Tests with live Docker Compose services (Verba + Weaviate + Phoenix):

```bash
# Run full deployment tests
python run_full_deployment_tests.py

# Cleanup existing deployment only
python run_full_deployment_tests.py --cleanup-only

# Keep deployment running after tests (for debugging)
python run_full_deployment_tests.py --no-cleanup
```

**What it tests:**
- Docker Compose integration
- Phoenix observability service
- Weaviate connectivity
- End-to-end RAG pipeline
- Service health and networking

### 3. Individual Test Files

Run specific test categories:

```bash
# Dependency verification
python test_dependency_verification.py

# Docker build verification
python test_docker_build_verification.py

# Observability integration
python test_observability_integration.py

# End-to-end tracing
python test_end_to_end_tracing_integration.py

# Property-based tests (with Hypothesis)
python test_observability_property.py
python test_property_7_minimal.py

# Error handling
python test_error_handling.py
python test_error_tracing_simple.py

# Feedback integration
python test_feedback_integration.py
```

## Test Categories

### Unit Tests
- **test_dependency_verification.py** - Verifies all required packages are installed
- **test_syntax_check.py** - Validates Python syntax and imports
- **test_observability_integration.py** - Tests OpenTelemetry integration

### Integration Tests
- **test_docker_compose_integration.py** - Docker Compose service integration
- **test_docker_build_verification.py** - Docker image build verification
- **test_end_to_end_tracing_integration.py** - Complete RAG pipeline tracing

### Property-Based Tests
- **test_observability_property.py** - Property-based correctness verification
- **test_property_7_minimal.py** - Minimal property test implementation

### Error Handling Tests
- **test_error_handling.py** - Comprehensive error scenario testing
- **test_error_tracing_simple.py** - Simple error tracing verification

### Feature Tests
- **test_feedback_integration.py** - User feedback correlation system

## Prerequisites

### Required Software
- Docker (with Docker Compose)
- Python 3.11+
- Available ports: 6006 (Phoenix), 8000 (Verba), 8080 (Weaviate)

### Required Files
- `docker-compose.yml` - Base Verba services
- `docker-compose.phoenix.yml` - Phoenix observability service
- `Dockerfile` - Verba application image

### System Requirements
- **Memory**: 4GB+ available for Docker
- **Disk**: 2GB+ free space for images and volumes
- **Network**: Internet access for image downloads

## Test Execution Options

### Complete Verification Suite

```bash
# Full suite (recommended for CI/CD)
python run_complete_verification.py

# Unit tests only (faster)
python run_complete_verification.py --unit-only

# Integration tests only (requires Docker Compose)
python run_complete_verification.py --integration-only

# Quick verification (critical tests only)
python run_complete_verification.py --quick

# Verbose output for debugging
python run_complete_verification.py --verbose
```

### Containerized Tests

```bash
# All containerized tests
python run_containerized_tests.py

# Build test image and run tests
python run_containerized_tests.py --verbose

# Build image only (for caching)
python run_containerized_tests.py --build-only
```

### Full Deployment Tests

```bash
# Complete deployment verification
python run_full_deployment_tests.py

# Keep services running for manual testing
python run_full_deployment_tests.py --no-cleanup

# Cleanup existing deployment
python run_full_deployment_tests.py --cleanup-only
```

## Understanding Test Results

### Success Indicators
- ✅ **PASSED** - Test completed successfully
- 🎉 **All tests passed** - Complete success
- 📝 **Verified components** - List of validated functionality

### Failure Indicators
- ❌ **FAILED** - Test failed
- ⚠️ **WARNING** - Non-critical issue
- 🔧 **Troubleshooting** - Suggested fixes

### Test Reports

Each test runner generates detailed reports showing:
- **Test Summary** - Pass/fail counts and success rate
- **Individual Results** - Status of each test file
- **System Information** - Docker version, Python version
- **Troubleshooting** - Suggested fixes for failures

## Troubleshooting

### Common Issues

#### Docker Not Available
```
❌ Docker is not available or not running
```
**Solution**: Start Docker Desktop or Docker daemon

#### Port Conflicts
```
❌ Port 6006 is not accessible
```
**Solution**: Stop services using required ports (6006, 8000, 8080)

#### Insufficient Resources
```
❌ Service failed to start: memory limit
```
**Solution**: Increase Docker memory allocation (4GB+ recommended)

#### Network Issues
```
❌ Failed to connect to Phoenix OTLP endpoint
```
**Solution**: Check Docker network configuration and firewall settings

### Debug Mode

Run tests with verbose output for detailed debugging:

```bash
python run_complete_verification.py --verbose
```

### Manual Service Inspection

Keep services running for manual inspection:

```bash
# Start services and keep them running
python run_full_deployment_tests.py --no-cleanup

# Check service status
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml ps

# View service logs
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml logs verba
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml logs phoenix
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml logs weaviate

# Access services
# Phoenix UI: http://localhost:6006
# Verba API: http://localhost:8000
# Weaviate: http://localhost:8080
```

### Cleanup

Clean up all test artifacts:

```bash
# Stop and remove all containers
python run_full_deployment_tests.py --cleanup-only

# Remove test images
docker rmi verba-test-runner

# Clean up Docker system
docker system prune -f
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Verba Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Complete Verification
        run: |
          cd Verba
          python run_complete_verification.py --verbose
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                dir('Verba') {
                    sh 'python run_complete_verification.py'
                }
            }
        }
    }
}
```

## Performance Expectations

### Execution Times (Approximate)

- **Quick Verification**: 2-3 minutes
- **Unit Tests Only**: 5-10 minutes
- **Integration Tests Only**: 10-15 minutes
- **Complete Suite**: 15-25 minutes

### Resource Usage

- **Memory**: 2-4GB during test execution
- **CPU**: Moderate usage during Docker builds
- **Disk**: 1-2GB for images and temporary files
- **Network**: Image downloads on first run

## Test Coverage

The test suite verifies:

### ✅ Core Functionality
- RAG pipeline (retrieval, generation)
- OpenTelemetry tracing integration
- Phoenix observability platform
- Weaviate vector database connectivity

### ✅ Observability Features
- Trace export to Phoenix
- Span creation and attributes
- Error tracing and resilience
- Experiment tracking
- User feedback correlation

### ✅ Deployment
- Docker image builds
- Docker Compose service orchestration
- Service health checks
- Network connectivity

### ✅ Correctness
- Property-based testing with Hypothesis
- Error handling scenarios
- Edge case validation
- Performance characteristics

This comprehensive testing approach ensures Verba is production-ready with full observability capabilities.