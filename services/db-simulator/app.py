import asyncio
import random
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

OTEL_ENDPOINT = "http://otel-collector.mesh-apps.svc.cluster.local:4317"

resource = Resource.create(
    {"service.name": "db-simulator", "deployment.environment": "mesh-apps"})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("db-simulator")

log_provider = LoggerProvider(resource=resource)
log_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(
        endpoint=OTEL_ENDPOINT, insecure=True))
)
otel_handler = LoggingHandler(
    level=logging.DEBUG, logger_provider=log_provider)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db-simulator")
logger.addHandler(otel_handler)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

PRODUCTS = [
    {"id": 1, "name": "Widget A", "price": 9.99},
    {"id": 2, "name": "Widget B", "price": 19.99},
    {"id": 3, "name": "Widget C", "price": 4.99},
]


@app.get("/")
async def query():
    with tracer.start_as_current_span("db-query") as span:
        latency = random.uniform(0.01, 0.2)
        span.set_attribute("db.latency_ms", round(latency * 1000, 2))

        await asyncio.sleep(latency)

        if random.random() < 0.5:
            span.set_attribute("db.error", True)
            span.set_attribute("db.error_type", "connection_failure")
            logger.error("Simulated DB connection failure!")
            return JSONResponse(
                status_code=500,
                content={"service": "db-simulator",
                         "error": "DB connection failed"}
            )

        product = random.choice(PRODUCTS)
        span.set_attribute("db.product_id", product["id"])
        logger.info(f"DB query completed in {latency:.3f}s", extra={
                    "product_id": product["id"]})

        return {
            "service": "db-simulator",
            "latency_ms": round(latency * 1000, 2),
            "data": product
        }


@app.get("/health")
async def health():
    return {"status": "ok"}
