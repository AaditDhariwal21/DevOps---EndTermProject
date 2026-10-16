# Troubleshooting lab

Three deliberately broken workloads, all in a throwaway `deskflow-lab` namespace so
they never touch the real application. Each has a fixed version in [`solutions/`](solutions/).

| Lab | Symptom | Root cause | Key commands |
|-----|---------|------------|--------------|
| [broken-image.yaml](broken-image.yaml) | `ErrImagePull` → `ImagePullBackOff` | Image tag typo (`1.30-alpline`) | `kubectl describe pod`, `kubectl get events` |
| [broken-service.yaml](broken-service.yaml) | Pods healthy, Service returns nothing | Service selector `app=lab-backend` ≠ Pod label `app=lab-api` | `kubectl get endpointslices`, `kubectl get pods --show-labels` |
| [broken-probe.yaml](broken-probe.yaml) (bonus) | `Running` but `READY 0/1` | Readiness probe on port 80, container listens on 8080 | `kubectl describe pod` (probe failures) |

## Lab 1 — ImagePullBackOff

```bash
kubectl apply -f troubleshooting/broken-image.yaml
kubectl get pods -n deskflow-lab
# NAME                       READY   STATUS             RESTARTS
# lab-web-7c9f...            0/1     ImagePullBackOff   0

kubectl describe pod -l app=lab-web -n deskflow-lab | tail -15
# Failed to pull image "nginxinc/nginx-unprivileged:1.30-alpline": ... not found

kubectl get events -n deskflow-lab --sort-by=.lastTimestamp
```

**Investigation path:** `ImagePullBackOff` → describe Pod → Events say *not found* → the
tag is wrong → fix the Deployment:

```bash
kubectl apply -f troubleshooting/solutions/fixed-image.yaml
kubectl rollout status deploy/lab-web -n deskflow-lab
```

Other causes of the same symptom: private registry without `imagePullSecrets`, a GHCR
package that is still private, a wrong registry hostname, or Docker Hub rate limits.

## Lab 2 — Service with no endpoints

```bash
kubectl apply -f troubleshooting/broken-service.yaml
kubectl get pods -n deskflow-lab --show-labels    # app=lab-api, Running 1/1
kubectl get svc lab-api -n deskflow-lab -o wide   # SELECTOR app=lab-backend  ← mismatch
kubectl get endpointslices -n deskflow-lab -l kubernetes.io/service-name=lab-api
# ENDPOINTS: <unset>

kubectl run curl -n deskflow-lab --rm -it --image=busybox:1.37 --restart=Never \
  -- wget -qO- -T 3 http://lab-api                # fails
```

**Lesson:** a Service selects Pods *only* by labels. No matching labels → no endpoints →
no traffic, even though every Pod is healthy.

```bash
kubectl apply -f troubleshooting/solutions/fixed-service.yaml
kubectl get endpointslices -n deskflow-lab -l kubernetes.io/service-name=lab-api   # 2 IPs
```

The DeskFlow chart avoids this by generating the Service selector and the Pod labels
from the same helper (`deskflow.selectorLabels` in `helm/deskflow/templates/_helpers.tpl`).

## Lab 3 — Running but not Ready

```bash
kubectl apply -f troubleshooting/broken-probe.yaml
kubectl get pods -n deskflow-lab -l app=lab-probe          # Running, 0/1
kubectl describe pod -l app=lab-probe -n deskflow-lab | grep -A2 Readiness
# Readiness probe failed: ... dial tcp 10.x.x.x:80: connect: connection refused

kubectl apply -f troubleshooting/solutions/fixed-probe.yaml  # Ready 1/1
```

**Lesson:** a failing readiness probe never restarts the container; it only removes the
Pod from the Service. DeskFlow uses this on purpose: `/ready` fails when PostgreSQL is
unreachable, so traffic only goes to Pods that can actually serve it.

## Live demo on the real app (optional)

Break the real DeskFlow Service selector, watch the UI fail, then restore it with Helm:

```bash
kubectl patch svc deskflow-backend -n deskflow \
  -p '{"spec":{"selector":{"app.kubernetes.io/component":"api"}}}'
kubectl get endpointslices -n deskflow -l kubernetes.io/service-name=deskflow-backend  # empty
# UI shows "Can't reach the DeskFlow API"; Grafana request rate drops to 0

# Fix it the way you diagnosed it: put the selector back
kubectl patch svc deskflow-backend -n deskflow \
  -p '{"spec":{"selector":{"app.kubernetes.io/component":"backend"}}}'
```

Or let Helm reconcile the drift: `helm upgrade deskflow ./helm/deskflow -n deskflow --reuse-values`.
On **Helm 4** add `--force-conflicts`: Helm 4 uses server-side apply and, by design,
refuses to overwrite a field another tool (`kubectl patch`) now owns.

## Clean up

```bash
kubectl delete namespace deskflow-lab
```
