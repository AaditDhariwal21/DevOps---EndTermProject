#!/usr/bin/env bash
# Build both images locally, load them into minikube, and deploy with Helm.
# Images are tagged with the current commit SHA — exactly like CI does — so the
# UI's pipeline panel shows which commit is running.
#
# Usage: scripts/deploy-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"
if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]; then
  SHA="${SHA}-dirty"   # uncommitted changes: don't pretend this is the commit
fi

echo "==> Building images (tag $SHA)"
docker build -t "deskflow-backend:$SHA" --build-arg GIT_SHA="$SHA" "$ROOT/backend"
docker build -t "deskflow-frontend:$SHA" --build-arg GIT_SHA="$SHA" "$ROOT/frontend"

echo "==> Loading images into minikube"
minikube image load "deskflow-backend:$SHA" --overwrite=true
minikube image load "deskflow-frontend:$SHA" --overwrite=true

echo "==> helm upgrade --install"
kubectl apply -f "$ROOT/k8s/namespace.yaml"
helm upgrade --install deskflow "$ROOT/helm/deskflow" \
  -n deskflow \
  -f "$ROOT/helm/deskflow/values-dev.yaml" \
  --set backend.image.tag="$SHA" \
  --set frontend.image.tag="$SHA" \
  --wait --timeout 5m

kubectl -n deskflow get pods,svc,ingress,hpa
