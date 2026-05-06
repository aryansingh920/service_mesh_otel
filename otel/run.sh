#!/bin/bash
# ================================================================
# apply-all.sh  — apply OTel + Istio resilience configs
# Usage: chmod +x apply-all.sh && ./apply-all.sh
# ================================================================
set -euo pipefail

NS="mesh-apps"

echo "═══════════════════════════════════════════════"
echo "  mesh-apps: OTel + Istio Resilience Setup"
echo "═══════════════════════════════════════════════"

# ── 1. Deploy OTel Collector ────────────────────────────────
echo ""
echo "▶ Deploying OpenTelemetry Collector..."
kubectl apply -f otel/otel-collector-config.yaml
kubectl -n $NS rollout status deployment/otel-collector --timeout=90s
echo "✓ OTel Collector ready"

# ── 2. Apply Istio Resilience Policies ─────────────────────
echo ""
echo "▶ Applying VirtualServices (timeouts + retries)..."
kubectl apply -f istio/istio-resilience.yaml
echo "✓ Istio policies applied"

# ── 3. Verify ───────────────────────────────────────────────
echo ""
echo "▶ Verifying resources in namespace: $NS"
echo ""
echo "── VirtualServices ──"
kubectl get virtualservices -n $NS

echo ""
echo "── DestinationRules ──"
kubectl get destinationrules -n $NS

echo ""
echo "── AuthorizationPolicies ──"
kubectl get authorizationpolicies -n $NS

echo ""
echo "── OTel Collector ──"
kubectl get pods -n $NS -l app=otel-collector

# ── 4. Verify mTLS ──────────────────────────────────────────
echo ""
echo "▶ Checking mTLS status..."
kubectl get peerauthentication -n $NS

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✓ All done!"
echo ""
echo "  Next steps:"
echo "  1. Add OTEL_SERVICE_NAME + OTEL_EXPORTER_OTLP_ENDPOINT"
echo "     env vars to your frontend/backend Deployments"
echo "  2. Import otel-instrumentation.js (Node) or"
echo "     otel_setup.py (Python) in your service entrypoints"
echo "  3. Uncomment fault injection in istio-resilience.yaml"
echo "     to test circuit breaker behaviour"
echo "  4. Watch Kiali — circuit breaker lightning bolt will"
echo "     appear on edges when trips fire"
echo "═══════════════════════════════════════════════"
