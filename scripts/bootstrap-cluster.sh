#!/usr/bin/env bash
# Installs the cluster add-ons DeskFlow relies on:
#   - namespaces (k8s/)
#   - gp3 default StorageClass            (EKS only)
#   - metrics-server  → HPA CPU metrics   (minikube uses its addon instead)
#   - kube-prometheus-stack → Prometheus + Grafana (+ ServiceMonitor CRDs)
#   - Traefik → Ingress controller
#
# Usage:  scripts/bootstrap-cluster.sh eks|minikube
#         GRAFANA_PASSWORD=... scripts/bootstrap-cluster.sh eks
set -euo pipefail

TARGET="${1:-}"
if [[ "$TARGET" != "eks" && "$TARGET" != "minikube" ]]; then
  echo "usage: $0 eks|minikube" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-deskflow-admin}"

# Chart versions pinned for reproducible installs.
KPS_VERSION="92.9.0"
TRAEFIK_VERSION="42.0.0"
METRICS_SERVER_VERSION="3.14.0"

echo "==> Context: $(kubectl config current-context)"

echo "==> Helm repositories"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add traefik https://traefik.github.io/charts >/dev/null
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
helm repo update >/dev/null

echo "==> Namespaces"
kubectl apply -f "$ROOT/k8s/namespace.yaml" -f "$ROOT/k8s/platform-namespaces.yaml"

if [[ "$TARGET" == "eks" ]]; then
  echo "==> gp3 StorageClass (default)"
  kubectl apply -f "$ROOT/k8s/storageclass-gp3.yaml"
  # Un-default the legacy gp2 class if present, so there is exactly one default.
  kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class=false --overwrite 2>/dev/null || true

  echo "==> metrics-server"
  helm upgrade --install metrics-server metrics-server/metrics-server \
    --version "$METRICS_SERVER_VERSION" -n kube-system --wait
else
  echo "==> metrics-server (minikube addon)"
  minikube addons enable metrics-server
fi

echo "==> kube-prometheus-stack (Prometheus + Grafana)"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version "$KPS_VERSION" -n monitoring \
  -f "$ROOT/monitoring/kube-prometheus-stack-values.yaml" \
  --set grafana.adminPassword="$GRAFANA_PASSWORD" \
  --wait --timeout 10m

echo "==> Traefik ingress controller"
helm upgrade --install traefik traefik/traefik \
  --version "$TRAEFIK_VERSION" -n ingress \
  -f "$ROOT/monitoring/traefik-values.yaml" \
  --wait --timeout 10m

echo
echo "Done. Next:"
if [[ "$TARGET" == "eks" ]]; then
  echo "  - push to main with DEPLOY_ENABLED=true (CI deploys), or run helm manually (README)"
  echo "  - load balancer: kubectl get svc traefik -n ingress"
else
  echo "  - scripts/deploy-local.sh"
  echo "  - run 'minikube tunnel' in another terminal for the Ingress"
fi
echo "  - Grafana: kubectl port-forward svc/monitoring-grafana 3001:80 -n monitoring  (admin / \$GRAFANA_PASSWORD)"
