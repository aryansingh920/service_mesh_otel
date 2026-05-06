// ============================================================
// otel-instrumentation.js
// Drop this in your frontend/backend services as the entrypoint
// Run: node -r ./otel-instrumentation.js your-server.js
// ============================================================

const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { OTLPLogExporter } = require('@opentelemetry/exporter-logs-otlp-grpc');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-grpc');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { BatchLogRecordProcessor } = require('@opentelemetry/sdk-logs');
const { SimpleLogRecordProcessor } = require('@opentelemetry/sdk-logs');
const logsAPI = require('@opentelemetry/api-logs');

// ── OTEL Collector endpoint (points to collector in same namespace) ──
const OTEL_ENDPOINT = process.env.OTEL_EXPORTER_OTLP_ENDPOINT
    || 'http://otel-collector.mesh-apps.svc.cluster.local:4317';

// ── Service identity (override per-service via env) ──
const SERVICE_NAME = process.env.OTEL_SERVICE_NAME || 'frontend';
const SERVICE_VERSION = process.env.SERVICE_VERSION || '1.0.0';
const ENVIRONMENT = process.env.DEPLOYMENT_ENV || 'mesh-apps';

// ── Resource ──
const resource = new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
    [SemanticResourceAttributes.SERVICE_VERSION]: SERVICE_VERSION,
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: ENVIRONMENT,
    'mesh.namespace': 'mesh-apps',
    'mesh.provider': 'istio',
});

// ── Exporters ──
const traceExporter = new OTLPTraceExporter({ url: OTEL_ENDPOINT });
const logExporter = new OTLPLogExporter({ url: OTEL_ENDPOINT });
const metricExporter = new OTLPMetricExporter({ url: OTEL_ENDPOINT });

// ── SDK ──
const sdk = new NodeSDK({
    resource,
    traceExporter,
    metricReader: new PeriodicExportingMetricReader({
        exporter: metricExporter,
        exportIntervalMillis: 10_000,
    }),
    logRecordProcessor: new BatchLogRecordProcessor(logExporter),
    instrumentations: [
        getNodeAutoInstrumentations({
            '@opentelemetry/instrumentation-http': {
                // Capture request/response bodies (careful with PII)
                requestHook: (span, req) => {
                    span.setAttribute('http.request.header.x-forwarded-for',
                        req.headers['x-forwarded-for'] || '');
                    span.setAttribute('istio.trace_id',
                        req.headers['x-b3-traceid'] || '');  // Bridge Istio B3 headers
                },
                responseHook: (span, res) => {
                    span.setAttribute('http.response.status_code', res.statusCode);
                },
            },
            '@opentelemetry/instrumentation-grpc': { enabled: true },
            '@opentelemetry/instrumentation-express': { enabled: true },
        }),
    ],
});

sdk.start();

// ── Structured logger (replaces console.log in your app) ──
const logger = logsAPI.logs.getLogger(SERVICE_NAME);

function structuredLog(level, message, attributes = {}) {
    logger.emit({
        severityText: level.toUpperCase(),
        body: message,
        attributes: {
            ...attributes,
            'service.name': SERVICE_NAME,
            'deployment.environment': ENVIRONMENT,
        },
    });
    // Also print to stdout so kubectl logs still works
    console[level === 'error' ? 'error' : 'log'](
        JSON.stringify({ level, message, service: SERVICE_NAME, ...attributes, ts: new Date().toISOString() })
    );
}

// Export for use in your app
module.exports = {
    log: {
        info: (msg, attrs) => structuredLog('info', msg, attrs),
        warn: (msg, attrs) => structuredLog('warn', msg, attrs),
        error: (msg, attrs) => structuredLog('error', msg, attrs),
        debug: (msg, attrs) => structuredLog('debug', msg, attrs),
    }
};

// Graceful shutdown
process.on('SIGTERM', () => {
    sdk.shutdown().then(() => process.exit(0));
});
