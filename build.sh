#!/bin/bash
# rebuild-deploy.sh
# Run from your project root (service_mesh_otel/)
set -euo pipefail

CLUSTER="kind"   # change if your kind cluster has a different name
NS="mesh-apps"

echo "═══════════════════════════════════════"
echo "  Rebuild + redeploy with OTel"
echo "═══════════════════════════════════════"

# ── 1. Copy updated Dockerfile into each service dir ──────

# ── 2. Copy updated app.py files ──────────────────────────
# (skip if you already copied them manually)

# ── 3. Build images ───────────────────────────────────────
echo ""
echo "▶ Building images..."
docker build -t frontend:v1    services/frontend/
docker build -t backend:v1     services/backend/
docker build -t db-simulator:v1 services/db-simulator/

kind load docker-image frontend:v1      --name observability-mesh
kind load docker-image backend:v1       --name observability-mesh
kind load docker-image db-simulator:v1  --name observability-mesh

kubectl rollout restart deployment/frontend     -n mesh-apps
kubectl rollout restart deployment/backend      -n mesh-apps
kubectl rollout restart deployment/db-simulator -n mesh-apps

kubectl rollout status deployment/frontend     -n mesh-apps --timeout=90s
kubectl rollout status deployment/backend      -n mesh-apps --timeout=90s
kubectl rollout status deployment/db-simulator -n mesh-apps --timeout=90s

echo ""
echo "═══════════════════════════════════════"
echo "  ✓ Done! Verify with:"
echo ""
echo "  # Tail logs from all three services"
echo "  kubectl logs -n $NS -l app=frontend --since=1m -f"
echo "  kubectl logs -n $NS -l app=backend --since=1m -f"
echo ""
echo "  # Check OTel collector is receiving data"
echo "  kubectl logs -n $NS -l app=otel-collector --since=1m | head -40"
echo "═══════════════════════════════════════"


# Check pods are healthy (should show 2/2 - app + istio sidecar)
kubectl get pods -n mesh-apps

# Check OTel collector is running
kubectl get pods -n mesh-apps -l app=otel-collector

# Tail frontend logs - you should see JSON structured logs
kubectl logs -n mesh-apps -l app=frontend -f

# In a separate terminal, generate some traffic
kubectl exec -n mesh-apps deploy/sleep -- curl -s http://frontend.mesh-apps.svc.cluster.local
kubectl apply -f otel/otel-collector-config.yaml
kubectl rollout status deployment/otel-collector -n mesh-apps --timeout=90s

kubectl apply -f otel/otel-collector-config.yaml
kubectl rollout status deployment/otel-collector -n mesh-apps --timeout=90s

# overwrite the file with the downloaded one, then:
kubectl apply -f otel/otel-collector-config.yaml
kubectl rollout restart deployment/otel-collector -n mesh-apps
kubectl rollout status deployment/otel-collector -n mesh-apps --timeout=90s


# Generate a request
kubectl exec -n mesh-apps deploy/sleep -- curl -s http://frontend.mesh-apps.svc.cluster.local

# Watch the collector logs - you should see spans/logs streaming in
kubectl logs -n mesh-apps -l app=otel-collector -c otel-collector -f
