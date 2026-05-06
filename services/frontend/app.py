import httpx
import logging
from fastapi import FastAPI, Request
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
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

OTEL_ENDPOINT = "http://otel-collector.mesh-apps.svc.cluster.local:4317"

resource = Resource.create(
    {"service.name": "frontend", "deployment.environment": "mesh-apps"})

# Traces
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
trace.set_tracer_provider(tracer_provider)

# Logs
log_provider = LoggerProvider(resource=resource)
log_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(
        endpoint=OTEL_ENDPOINT, insecure=True))
)
otel_handler = LoggingHandler(
    level=logging.DEBUG, logger_provider=log_provider)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frontend")
logger.addHandler(otel_handler)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

ISTIO_HEADERS = [
    "x-request-id", "x-b3-traceid", "x-b3-spanid",
    "x-b3-parentspanid", "x-b3-sampled", "x-b3-flags", "x-forwarded-for",
]


@app.get("/")
async def home(request: Request):
    headers = {h: request.headers[h]
               for h in ISTIO_HEADERS if h in request.headers}

    span = trace.get_current_span()
    span.set_attribute("http.request.id", headers.get("x-request-id", ""))

    logger.info("Frontend received request, calling backend...")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "http://backend.mesh-apps.svc.cluster.local",
                headers=headers
            )
            backend_data = response.json()
    except Exception as e:
        logger.error(f"Backend call failed: {e}", extra={
                     "upstream": "backend"})
        span.record_exception(e)
        return JSONResponse(status_code=500, content={"service": "frontend", "error": str(e)})

    return {"service": "frontend", "message": "I am the Frontend", "backend": backend_data}


@app.get("/health")
async def health():
    return {"status": "ok"}
