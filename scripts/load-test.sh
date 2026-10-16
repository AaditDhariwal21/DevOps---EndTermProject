#!/usr/bin/env bash
# Generate CPU load on the backend so the HPA scales it out.
#
# Starts N load-generator Pods inside the cluster that hammer the stats and
# list endpoints (both hit PostgreSQL and serialise JSON = real CPU work).
#
# Usage:  scripts/load-test.sh [workers=6] [duration_seconds=300]
# Watch:  kubectl get hpa -n deskflow -w
#         kubectl top pods -n deskflow
set -euo pipefail

WORKERS="${1:-6}"
DURATION="${2:-300}"
NS="deskflow"
TARGET="http://deskflow-backend:8000"

cleanup() {
  echo "==> Removing load generators"
  kubectl -n "$NS" delete pod -l app=deskflow-load --ignore-not-found --wait=false >/dev/null
}
trap cleanup EXIT INT TERM

echo "==> Starting $WORKERS load generators for ${DURATION}s against $TARGET"
for i in $(seq 1 "$WORKERS"); do
  kubectl -n "$NS" run "deskflow-load-$i" \
    --image=busybox:1.37 --restart=Never --labels=app=deskflow-load \
    --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"load","image":"busybox:1.37","securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}},"command":["sh","-c","end=$(( $(date +%s) + '"$DURATION"' )); while [ $(date +%s) -lt $end ]; do wget -q -O /dev/null '"$TARGET"'/api/tickets/stats; wget -q -O /dev/null '"$TARGET"'/api/tickets; done"]}]}}' \
    >/dev/null
done

echo "==> Load running. HPA status (Ctrl+C to stop early):"
end=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$end" ]; do
  kubectl -n "$NS" get hpa deskflow-backend -o \
    jsonpath="{'$(date +%H:%M:%S)'}  cpu={.status.currentMetrics[0].resource.current.averageUtilization}% (target {.spec.metrics[0].resource.target.averageUtilization}%)  replicas={.status.currentReplicas} → desired={.status.desiredReplicas}{'\n'}" \
    2>/dev/null || echo "hpa not found"
  sleep 15
done
