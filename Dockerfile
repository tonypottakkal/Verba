FROM python:3.11
WORKDIR /Verba
COPY . /Verba
RUN pip install '.'
RUN pip install pandas
# --- Observability / Phoenix / OpenTelemetry ---
RUN pip install --no-cache-dir \
    arize-phoenix-otel \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    openinference-instrumentation-langchain \
    opentelemetry-instrumentation-requests

EXPOSE 8000
CMD ["verba", "start","--port","8000","--host","0.0.0.0"]
