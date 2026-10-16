# Live demo script (~12 minutes)

Follows the required flow: **Application → Git commit → CI → Docker image → security
scan → registry → Terraform → Kubernetes → Helm → Ingress → autoscaling → monitoring →
troubleshooting**.

## Before you start (T-30 min)

- [ ] EKS up (`terraform apply`), `scripts/bootstrap-cluster.sh eks` done, app deployed once by CI
- [ ] Browser tabs: app (NLB URL), `/docs`, GitHub Actions, GHCR packages, AWS console (VPC + EKS), Grafana, Prometheus Targets
- [ ] Terminal 1: `kubectl port-forward svc/monitoring-grafana 3001:80 -n monitoring`
- [ ] Terminal 2: `kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090 -n monitoring`
- [ ] Terminal 3: free, for commands
- [ ] Note the live SHA shown in the UI's *Delivery pipeline* card

## 1. Application (1 min)

- Open DeskFlow via the Ingress URL. Walk through KPIs, ticket table, filters, activity feed.
- **Create a ticket** ("Demo: printer on fire", urgent). It appears in the table and the
  activity feed, and the *Urgent & open* KPI goes up.
- Open `/docs`: run `GET /api/tickets/stats` and `PUT /api/tickets/{id}` live.

## 2. Database (30 s)

```bash
kubectl exec -n deskflow deskflow-postgresql-0 -- psql -U deskflow -c \
  "SELECT id, status, priority, title FROM tickets ORDER BY id DESC LIMIT 5;"
```

## 3. Git commit → CI → image → scan → registry → deploy (4 min, the centrepiece)

Make a visible change, e.g. `frontend/src/App.jsx`: change `'Support overview'` to
`'Support overview — live demo'`, or bump `app_version` in `backend/app/config.py`.

```bash
git checkout -b demo/title-change
git commit -am "feat(frontend): rename dashboard title for live demo"
git push -u origin demo/title-change        # optional: open a PR, show checks running
git checkout main && git merge --ff-only demo/title-change && git push
```

In GitHub Actions, narrate while it runs:

1. **backend-test**: ruff, 31 pytest tests, migrations on real Postgres. "This is the
   first quality gate; a failing test stops everything here."
2. **build-scan-push**: two images built in parallel, **Trivy** table in the run summary,
   then pushed as `ghcr.io/…:<sha>`.
3. Show **GHCR**: the new tag is the commit SHA, not `latest`. "Production traces back
   to an exact commit."
4. **deploy**: logs in to AWS (GitHub secrets), `helm upgrade --atomic`, smoke test asserts
   the live SHA equals the commit.

Refresh the app: the new title shows, and the *Delivery pipeline* card shows the new SHA.

```bash
helm history deskflow -n deskflow           # new revision
kubectl get pods -n deskflow                # new pod names (rolling update, zero downtime)
```

## 4. Terraform (1 min)

Show `terraform/main.tf` (VPC module: 2 public + 2 private subnets, single NAT; EKS
module: node group, add-ons) and the AWS console: VPC subnets, EKS cluster, node group in
ap-southeast-2. "Nothing here was clicked together; `terraform destroy` removes all of it."

## 5. Kubernetes + Helm + Ingress (1 min)

```bash
kubectl get pods,svc,ingress,hpa -n deskflow
helm list -A
kubectl get svc traefik -n ingress          # NLB hostname = the URL we've been using
```

Point out the Ingress rules: `/api` and `/docs` go to the backend, `/` to the frontend.

## 6. Autoscaling + monitoring (2.5 min)

```bash
scripts/load-test.sh 8 240
```

While it runs:

- Grafana "DeskFlow — API overview": request rate climbs, p95 latency, *Backend CPU per
  pod* rises past the 60 % target, then *HPA replicas* goes 2 → 3 → 4.
- `kubectl get hpa -n deskflow -w` in the terminal.
- Prometheus → Targets: `deskflow-backend` endpoints **UP** (one per pod, including the new ones).

## 7. Troubleshooting (2 min)

Option A, the lab:

```bash
kubectl apply -f troubleshooting/broken-service.yaml
kubectl get endpointslices -n deskflow-lab -l kubernetes.io/service-name=lab-api   # none
kubectl get pods -n deskflow-lab --show-labels
kubectl describe svc lab-api -n deskflow-lab     # selector app=lab-backend ≠ app=lab-api
kubectl apply -f troubleshooting/solutions/fixed-service.yaml
```

Option B, break the real app (more dramatic):

```bash
kubectl set image deploy/deskflow-frontend frontend=ghcr.io/<owner>/deskflow-frontend:does-not-exist -n deskflow
kubectl get pods -n deskflow            # new pod ImagePullBackOff; old pods keep serving (maxUnavailable: 0)
kubectl describe pod -n deskflow -l app.kubernetes.io/component=frontend | grep -A3 Events
kubectl rollout undo deploy/deskflow-frontend -n deskflow
```

Key line: "The rolling update never took down the working Pods, so users saw no outage.
That's `maxUnavailable: 0` plus readiness probes."

## 8. Wrap-up (30 s)

"Every change goes through tests, a security gate and an immutable SHA-tagged image, and
is deployed declaratively by Helm onto infrastructure defined in Terraform, with metrics
to show it's healthy." Then, after grading: `scripts/destroy-eks.sh`.
