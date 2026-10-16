#!/usr/bin/env bash
# Tear everything down in the right order so `terraform destroy` succeeds.
#
# Why not just `terraform destroy`? Kubernetes created AWS resources that
# Terraform doesn't know about: the Traefik Service made a Network Load Balancer
# and the PostgreSQL/Prometheus PVCs made EBS volumes. A load balancer left in
# the VPC blocks subnet/VPC deletion, so remove them first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Uninstalling Helm releases"
helm uninstall deskflow -n deskflow --wait 2>/dev/null || true
helm uninstall traefik -n ingress --wait 2>/dev/null || true
helm uninstall monitoring -n monitoring --wait 2>/dev/null || true
helm uninstall metrics-server -n kube-system --wait 2>/dev/null || true

echo "==> Deleting PVCs (releases EBS volumes) and namespaces"
kubectl delete pvc --all -n deskflow --wait=true 2>/dev/null || true
kubectl delete namespace deskflow monitoring ingress --wait=true 2>/dev/null || true

echo "==> Waiting for LoadBalancer services to disappear"
for _ in $(seq 1 30); do
  remaining=$(kubectl get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name}{"\n"}{end}' 2>/dev/null | wc -l)
  [ "$remaining" -eq 0 ] && break
  sleep 10
done

echo "==> terraform destroy"
terraform -chdir="$ROOT/terraform" destroy

echo "Done. Double-check the AWS console (EC2 → Load Balancers, Volumes; VPC) for leftovers."
