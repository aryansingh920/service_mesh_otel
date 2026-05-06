# ============================================================
# otel_setup.py
# Import this at the top of your backend/db-simulator service
# Works with FastAPI, Flask, gRPC-based Python services
# ============================================================

import os
import logging
import json
from datetime import datetime

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # swap for Flask if needed
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient, GrpcInstrumentorServer

# ── Config ──────────────────────────────────────────────────
OTEL_ENDPOINT   = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT",
                             "http://otel-collector.mesh-apps.svc.cluster.local:4317")
SERVICE         = os.getenv("OTEL_SERVICE_NAME", "backend")
VERSION         = os.getenv("SERVICE_VERSION", "1.0.0")
ENVIRONMENT     = os.getenv("DEPLOYMENT_ENV", "mesh-apps")

resource = Resource.create({
    SERVICE_NAME: SERVICE,
    SERVICE_VERSION: VERSION,
    "deployment.environment": ENVIRONMENT,
    "mesh.namespace": "mesh-apps",
    "mesh.provider": "istio",
})

# ── Traces ───────────────────────────────────────────────────
trace_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(SERVICE)

# ── Metrics ──────────────────────────────────────────────────
metric_exporter = OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True)
metric_reader   = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10_000)
meter_provider  = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(SERVICE)

# Custom metrics your services can use
request_counter   = meter.create_counter("http.requests.total", unit="1", description="Total HTTP requests")
error_counter     = meter.create_counter("http.errors.total",   unit="1", description="Total HTTP errors")
latency_histogram = meter.create_histogram("http.request.duration", unit="ms", description="Request latency")

# ── Logs ─────────────────────────────────────────────────────
log_exporter    = OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True)
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
set_logger_provider(logger_provider)

# Bridge Python's stdlib logging → OTel
otel_handler = LoggingHandler(level=logging.DEBUG, logger_provider=logger_provider)

# ── Structured JSON logger ────────────────────────────────────
class StructuredLogger:
    """Use this instead of print() or logging in your services."""

    def __init__(self, service_name: str):
        self._logger = logging.getLogger(service_name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(otel_handler)
        # Also log to stdout for kubectl logs
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)
        self._service = service_name

    def _emit(self, level: str, message: str, **kwargs):
        record = {
            "level": level,
            "message": message,
            "service": self._service,
            "environment": ENVIRONMENT,
            "ts": datetime.utcnow().isoformat() + "Z",
            **kwargs,
        }
        # Attach current span context so logs are correlated to traces
        span = trace.get_current_span()
        ctx  = span.get_span_context()
        if ctx.is_valid:
            record["trace_id"] = format(ctx.trace_id, "032x")
            record["span_id"]  = format(ctx.span_id, "016x")

        getattr(self._logger, level)(json.dumps(record))

    def info(self, msg, **kw):  self._emit("info",  msg, **kw)
    def warn(self, msg, **kw):  self._emit("warning", msg, **kw)
    def error(self, msg, **kw): self._emit("error", msg, **kw)
    def debug(self, msg, **kw): self._emit("debug", msg, **kw)


def setup_instrumentation(app=None):
    """Call once at startup. Pass your FastAPI/Flask app if you have one."""
    RequestsInstrumentor().instrument()
    GrpcInstrumentorClient().instrument()
    GrpcInstrumentorServer().instrument()
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    return StructuredLogger(SERVICE)


# ── Usage example ──────────────────────────────────────────
# from otel_setup import setup_instrumentation, tracer, request_counter, latency_histogram
#
# app = FastAPI()
# log = setup_instrumentation(app)
#
# @app.get("/api/data")
# async def get_data():
#     with tracer.start_as_current_span("fetch-from-db") as span:
#         span.set_attribute("db.system", "postgresql")
#         start = time.time()
#         result = await db.fetch(...)
#         latency_histogram.record((time.time() - start) * 1000)
#         request_counter.add(1, {"route": "/api/data", "method": "GET"})
#         log.info("fetched data", rows=len(result))
#         return result
