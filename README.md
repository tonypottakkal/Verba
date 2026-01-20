# Verba with RAG Observability

## The Golden RAGtriever - Enhanced with OpenTelemetry & Arize Phoenix ✨

[![Weaviate](https://img.shields.io/static/v1?label=powered%20by&message=Weaviate%20%E2%9D%A4&color=green&style=flat-square)](https://weaviate.io/)
[![OpenTelemetry](https://img.shields.io/static/v1?label=observability&message=OpenTelemetry&color=blue&style=flat-square)](https://opentelemetry.io/)
[![Phoenix](https://img.shields.io/static/v1?label=monitoring&message=Arize%20Phoenix&color=orange&style=flat-square)](https://phoenix.arize.com/)
[![PyPi downloads](https://static.pepy.tech/personalized-badge/goldenverba?period=total&units=international_system&left_color=grey&right_color=orange&left_text=pip%20downloads)](https://pypi.org/project/goldenverba/) 
[![Docker support](https://img.shields.io/badge/Docker_support-%E2%9C%93-4c1?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/get-started/)

> **🚀 Enhanced Fork**: This is an enhanced version of the original [Verba: The Golden RAGtriever](https://github.com/weaviate/Verba) with comprehensive **RAG observability** powered by **OpenTelemetry** and **Arize Phoenix**. For the original documentation, see [ORIGINAL_README.md](./ORIGINAL_README.md).

---

## 🔍 What's New: RAG Observability

This enhanced version adds **production-grade observability** to the Verba RAG pipeline:

### **🎯 Key Observability Features**

| Feature | Status | Description |
|---------|--------|-------------|
| **End-to-End Tracing** | ✅ | Complete RAG pipeline visibility with OpenTelemetry |
| **Phoenix Integration** | ✅ | Real-time monitoring and analysis with Arize Phoenix |
| **Error Resilience** | ✅ | Circuit breaker pattern prevents observability failures |
| **User Feedback Correlation** | ✅ | Link user ratings to specific traces for quality analysis |
| **A/B Testing Support** | ✅ | Experiment tracking with deterministic variant assignment |
| **Performance Monitoring** | ✅ | KPI tracking for latency, throughput, and success rates |
| **Graceful Degradation** | ✅ | Application continues working when observability fails |

### **📊 Observability Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                  RAG Pipeline Tracing                    │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ rag.query   │───►│ rag.retrieve│───►│ rag.generate│  │
│  │ • Query     │    │ • Embedding │    │ • LLM       │  │
│  │ • Session   │    │ • Search    │    │ • Streaming │  │
│  │ • A/B Test  │    │ • Context   │    │ • Feedback  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                    │                    │     │
│         └────────────────────┼────────────────────┘     │
│                              ▼                          │
│                    ┌─────────────────┐                  │
│                    │ Phoenix UI      │                  │
│                    │ localhost:6006  │                  │
│                    └─────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start with Observability

### **Option 1: Docker with Phoenix (Recommended)**

```bash
# Clone this enhanced version
git clone https://github.com/your-username/Verba.git
cd Verba

# Start all services including Phoenix observability
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d

# Access services
# Verba: http://localhost:8000
# Phoenix: http://localhost:6006
# Weaviate: http://localhost:8080
```

### **Option 2: Local Development**

```bash
# Install with observability dependencies
pip install -e ".[observability]"

# Set up Phoenix (separate terminal)
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

# Start Verba with observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 verba start
```

### **Option 3: Observability Disabled**

```bash
# Run without observability (original Verba behavior)
OTEL_TRACING_DISABLED=true verba start
```

---

## 📈 Observability Features

### **🔍 Real-Time Monitoring**

- **RAG Pipeline Visibility**: See every step from query to response
- **Performance Metrics**: Track latency, throughput, and error rates
- **Model Comparison**: Compare different LLM and embedding models
- **Resource Usage**: Monitor token consumption and API costs

### **🎯 Quality Analysis**

- **User Feedback Integration**: Rate responses and correlate with traces
- **Error Tracking**: Detailed error analysis with stack traces
- **A/B Testing**: Compare different RAG configurations
- **Quality Trends**: Track improvement over time

### **🛡️ Production Resilience**

- **Circuit Breaker**: Prevents observability failures from affecting users
- **Graceful Degradation**: App works even when Phoenix is down
- **Configurable Thresholds**: Tune failure detection and recovery
- **Health Monitoring**: Real-time observability system status

---

## 🔧 Observability Configuration

### **Environment Variables**

```bash
# Core Observability
OTEL_SERVICE_NAME=verba
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
OTEL_TRACING_DISABLED=false

# Circuit Breaker (Resilience)
OTEL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
OTEL_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Batch Processing
OTEL_BSP_MAX_QUEUE_SIZE=2048
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
OTEL_BSP_EXPORT_TIMEOUT=30000
```

### **Feedback API**

Submit user feedback linked to traces:

```bash
curl -X POST http://localhost:8000/api/submit_feedback \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "your-trace-id",
    "rating": 4.5,
    "feedback_tag": "helpful",
    "comments": "Great response!",
    "credentials": {
      "deployment": "Local",
      "url": "http://localhost:8080",
      "key": ""
    }
  }'
```

---

## 📚 Enhanced Documentation

### **🔍 Observability Guides**

- **[Phoenix Setup Guide](./PHOENIX_SETUP.md)** - Complete setup and configuration
- **[Error Handling Implementation](./ERROR_HANDLING_IMPLEMENTATION.md)** - Resilience patterns
- **[Feedback API Usage](./FEEDBACK_API_USAGE.md)** - User feedback integration
- **[Testing Guide](./TESTING_GUIDE.md)** - Property-based testing approach

### **📖 Original Documentation**

- **[Original README](./ORIGINAL_README.md)** - Complete original Verba documentation
- **[Codebase Guide](./VERBA_CODEBASE_GUIDE.md)** - Technical architecture overview
- **[UI Implementation Guide](./VERBA_UI_AND_IMPLEMENTATION_GUIDE.md)** - Frontend details

---

## 🧪 Testing

This enhanced version includes comprehensive testing:

```bash
# Run observability integration tests
python test_observability_integration.py

# Run property-based tests (100+ scenarios)
python test_observability_property.py

# Run error handling tests
python test_error_handling.py

# Run feedback integration tests
python test_feedback_integration.py
```

---

## 🎯 What Is Verba?

Verba is a fully-customizable personal assistant utilizing [Retrieval Augmented Generation (RAG)](https://weaviate.io/rag#:~:text=RAG%20with%20Weaviate,accuracy%20of%20AI%2Dgenerated%20content.) for querying and interacting with your data. This enhanced version adds **production-grade observability** to help you:

- **Monitor RAG Performance**: Track every step from query to response
- **Analyze User Satisfaction**: Correlate feedback with system behavior  
- **Debug Issues**: Detailed error tracking and analysis
- **Optimize Quality**: A/B test different configurations
- **Scale Confidently**: Production-ready resilience patterns

---

## ✨ Core Features (Enhanced)

| 🤖 **Model Support** | **Observability** | **Description** |
|---------------------|------------------|-----------------|
| OpenAI (GPT-4, etc.) | ✅ Full Tracing | Complete pipeline visibility |
| Anthropic (Claude) | ✅ Full Tracing | Error tracking and performance |
| Cohere (Command R+) | ✅ Full Tracing | User feedback correlation |
| Ollama (Local) | ✅ Full Tracing | A/B testing support |
| Groq (LPU) | ✅ Full Tracing | Circuit breaker protection |

| 📊 **Observability Features** | **Status** | **Description** |
|------------------------------|------------|-----------------|
| End-to-End Tracing | ✅ | OpenTelemetry integration |
| Phoenix Dashboard | ✅ | Real-time monitoring UI |
| User Feedback API | ✅ | Quality correlation |
| Error Resilience | ✅ | Circuit breaker pattern |
| A/B Testing | ✅ | Experiment tracking |
| Performance KPIs | ✅ | Latency and throughput |

---

## 🚀 Getting Started

### **Prerequisites**

- Python ≥3.10.0, <3.13.0
- Docker (for Phoenix and Weaviate)
- Git

### **Installation Options**

#### **1. Full Observability Setup**

```bash
# Clone enhanced version
git clone https://github.com/your-username/Verba.git
cd Verba

# Start with Phoenix observability
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d

# Access applications
echo "Verba: http://localhost:8000"
echo "Phoenix: http://localhost:6006" 
echo "Weaviate: http://localhost:8080"
```

#### **2. Local Development**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with observability
pip install -e ".[observability]"

# Start Phoenix (separate terminal)
docker run -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest

# Configure and start Verba
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
verba start
```

#### **3. Original Verba (No Observability)**

```bash
# Disable observability for original behavior
export OTEL_TRACING_DISABLED=true
pip install goldenverba
verba start
```

---

## 🔑 API Keys & Environment Variables

All original Verba environment variables are supported, plus new observability options:

### **Observability Configuration**

```bash
# OpenTelemetry Configuration
OTEL_SERVICE_NAME=verba
OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_TRACING_DISABLED=false

# Circuit Breaker Settings
OTEL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
OTEL_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Batch Processing
OTEL_BSP_MAX_QUEUE_SIZE=2048
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
```

### **Original Verba Variables**

All original environment variables are preserved. See [ORIGINAL_README.md](./ORIGINAL_README.md) for the complete list including:

- `WEAVIATE_URL_VERBA` / `WEAVIATE_API_KEY_VERBA`
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `COHERE_API_KEY`
- `OLLAMA_URL` / `GROQ_API_KEY`
- And many more...

---

## 🎮 Usage Examples

### **1. Monitor RAG Performance**

```python
# Your queries are automatically traced
# View in Phoenix at http://localhost:6006

# Filter traces by:
# - User session
# - Model type  
# - Performance metrics
# - Error status
```

### **2. Submit User Feedback**

```javascript
// Frontend integration
await fetch('/api/submit_feedback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    trace_id: 'trace-abc-123',
    rating: 4.5,
    feedback_tag: 'helpful',
    comments: 'Great answer!',
    credentials: { /* your weaviate config */ }
  })
});
```

### **3. A/B Testing**

```bash
# Traces automatically include experiment variants
# Based on deterministic session hashing
# View results in Phoenix dashboard
```

---

## 🛠️ Development

### **Project Structure**

```
Verba/
├── goldenverba/
│   ├── observability.py          # 🆕 OpenTelemetry integration
│   ├── verba_manager.py          # 🔄 Enhanced with tracing
│   ├── components/
│   │   └── managers.py           # 🔄 Enhanced with error handling
│   └── server/
│       └── api.py                # 🔄 Enhanced with feedback API
├── docker-compose.phoenix.yml    # 🆕 Phoenix observability
├── PHOENIX_SETUP.md              # 🆕 Setup guide
├── ERROR_HANDLING_IMPLEMENTATION.md # 🆕 Resilience patterns
├── FEEDBACK_API_USAGE.md         # 🆕 Feedback integration
├── test_observability_*.py       # 🆕 Comprehensive testing
└── ORIGINAL_README.md            # 📄 Original documentation
```

### **Running Tests**

```bash
# Integration tests
python test_observability_integration.py

# Property-based tests (100+ scenarios)
python test_observability_property.py

# Error handling tests
python test_error_handling.py

# All tests
./test.sh
```

---

## 🤝 Contributing

Contributions are welcome! This enhanced version maintains compatibility with the original Verba while adding observability features.

### **Areas for Contribution**

- **Observability**: Additional metrics, custom dashboards
- **Testing**: More property-based test scenarios
- **Documentation**: Usage examples, best practices
- **Integrations**: Additional observability backends
- **Performance**: Optimization and benchmarking

### **Development Setup**

```bash
# Fork and clone
git clone https://github.com/your-username/Verba.git
cd Verba

# Install development dependencies
pip install -e ".[dev,observability]"

# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.phoenix.yml up -d

# Run tests
python -m pytest test_observability_*.py
```

---

## 📄 License & Attribution

This enhanced version maintains the same license as the original Verba project. 

**Original Project**: [Weaviate/Verba](https://github.com/weaviate/Verba)  
**Enhanced By**: [Your Name/Organization]  
**License**: [Same as original]

---

## 🆘 Support & Issues

### **Observability Issues**

- Check Phoenix is running: `docker ps | grep phoenix`
- Verify OTLP endpoint: `curl http://localhost:4317`
- Review circuit breaker status in logs
- See [ERROR_HANDLING_IMPLEMENTATION.md](./ERROR_HANDLING_IMPLEMENTATION.md)

### **Original Verba Issues**

For issues with core Verba functionality, refer to:
- [ORIGINAL_README.md](./ORIGINAL_README.md) 
- [Original Verba Repository](https://github.com/weaviate/Verba)

### **Getting Help**

1. **Check Documentation**: Start with relevant guide above
2. **Review Logs**: Look for observability initialization messages
3. **Test Connectivity**: Verify Phoenix and Weaviate connections
4. **Open Issue**: Include observability status and logs

---

## 🎯 Roadmap

### **Planned Enhancements**

- [ ] **Custom Metrics**: Business-specific KPIs
- [ ] **Advanced Analytics**: ML-powered insights
- [ ] **Multi-tenant Observability**: User-specific dashboards
- [ ] **Cost Tracking**: Token usage and API costs
- [ ] **Alerting**: Proactive issue detection
- [ ] **Export Integrations**: Prometheus, Grafana, etc.

### **Compatibility**

- ✅ **Backward Compatible**: Works with existing Verba setups
- ✅ **Optional Observability**: Can be disabled entirely
- ✅ **Original APIs**: All existing endpoints preserved
- ✅ **Environment Variables**: Original config still works

---

**🚀 Ready to get started?** Choose your installation method above and start monitoring your RAG pipeline in minutes!