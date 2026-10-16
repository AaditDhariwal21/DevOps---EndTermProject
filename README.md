# DeskFlow — Helpdesk Ticketing, from laptop to monitored Kubernetes

DeskFlow is a small SaaS-style **helpdesk ticketing system**. Customer requests come
in as tickets, support agents triage them by priority and category, assign an owner,
and move them through `open → in progress → resolved → closed`. A dashboard shows
the live workload, an audit trail of every change, and which commit is currently
deployed.

The application is deliberately small; the point of the project is the **delivery
pipeline around it**: tests, containers, CI/CD, security scanning, a registry,
infrastructure as code, Kubernetes, Helm, Ingress, autoscaling, monitoring and
troubleshooting.

![DeskFlow dashboard](docs/screenshots/dashboard.png)

---

## Contents

1. [Architecture](#1-architecture)
2. [Repository layout](#2-repository-layout)
3. [Run it locally (Docker Compose)](#3-run-it-locally-docker-compose)
4. [Backend: API, database, tests](#4-backend-api-database-tests)
5. [CI/CD pipeline](#5-cicd-pipeline-github-actions)
6. [Security scanning (Trivy)](#6-security-scanning-trivy)
7. [AWS infrastructure (Terraform)](#7-aws-infrastructure-terraform)
8. [Kubernetes + Helm](#8-kubernetes--helm)
9. [Ingress, HPA, monitoring](#9-ingress-autoscaling-and-monitoring)
10. [Troubleshooting lab](#10-troubleshooting-lab)
11. [Tear down](#11-tear-down)

Grading map and screenshot checklist: [docs/SUBMISSION.md](docs/SUBMISSION.md) ·
Presentation script: [docs/DEMO.md](docs/DEMO.md)

---

## 1. Architecture

```mermaid
flowchart LR
    dev([Developer]) -->|git push| gh[GitHub]
    gh --> ci

    subgraph ci[GitHub Actions]
        direction TB
        t[pytest + ruff<br/>migration check<br/>frontend build] --> b[docker build<br/>tag = commit SHA]
        b --> s[Trivy scan<br/>fail on HIGH/CRITICAL]
        s --> p[push to GHCR]
        p --> d[helm upgrade --install]
    end

    tf[Terraform] -->|creates| aws

    subgraph aws[AWS ap-southeast-2]
        subgraph vpc[VPC: 2 public + 2 private subnets]
            nlb[Network Load Balancer]
            subgraph eks[EKS cluster]
                tr[Traefik Ingress] -->|/| fe[frontend<br/>React + Nginx ×2]
                tr -->|/api, /docs| be[backend<br/>FastAPI ×2..6 HPA]
                be --> pg[(PostgreSQL<br/>StatefulSet + EBS)]
                prom[Prometheus] -->|scrape /metrics| be
                graf[Grafana] --> prom
            end
        end
    end

    d --> eks
    user([Browser]) --> nlb --> tr
```

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite, hand-written responsive CSS, served by unprivileged Nginx |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, Uvicorn |
| Database | PostgreSQL 17 |
| Metrics | `prometheus-fastapi-instrumentator` + a custom business counter |
| Tests | pytest (31 tests) on an in-memory SQLite DB, ruff lint |
| Containers | Multi-stage Dockerfiles, non-root users, Docker Compose |
| CI/CD | GitHub Actions → Trivy → GHCR → Helm on EKS (OIDC role or access-key secrets) |
| Infrastructure | Terraform: VPC + EKS 1.35 + managed node group (+ optional GitHub OIDC role) |
| Platform | Helm chart, Traefik Ingress, HPA, PDBs, metrics-server |
| Observability | kube-prometheus-stack (Prometheus Operator + Grafana), auto-provisioned dashboard |

**Why Traefik and not ingress-nginx?** The Kubernetes project retired ingress-nginx in
March 2026 (no more security fixes), so a maintained controller is the responsible choice.
The Ingress *resource* is standard; only `ingressClassName` changes.

---

## 2. Repository layout

```text
.
├── frontend/                 React app (src/), Nginx config, multi-stage Dockerfile
├── backend/
│   ├── app/                  FastAPI app: main.py, routers/, models, schemas, config
│   ├── alembic/versions/     0001 schema, 0002 demo seed data
│   ├── tests/                pytest suite + conftest.py (isolated test DB)
│   ├── pytest.ini
│   └── Dockerfile
├── docker-compose.yml        Full local stack (postgres + backend + frontend)
├── .github/workflows/        ci-cd.yml — test → build/scan/push → deploy
├── terraform/                AWS VPC + EKS (+ GitHub OIDC deploy role)
├── helm/deskflow/            Helm chart (values.yaml, values-dev.yaml, values-eks.yaml)
├── k8s/                      Namespace + bootstrap manifests
├── monitoring/               kube-prometheus-stack and Traefik Helm values
├── troubleshooting/          Deliberately broken manifests + solutions
├── scripts/                  bootstrap, local deploy, load test, teardown
└── docs/                     Submission checklist, demo script, screenshots
```

---

## 3. Run it locally (Docker Compose)

Requirements: Docker Desktop (or Docker Engine + Compose v2).

```bash
docker compose up --build
```

| URL | What |
|-----|------|
| http://localhost:3000 | DeskFlow UI |
| http://localhost:8000/docs | Swagger UI (also at http://localhost:3000/docs) |
| http://localhost:8000/health | Liveness |
| http://localhost:8000/ready | Readiness (checks the DB) |
| http://localhost:8000/metrics | Prometheus metrics |

On start-up the backend container runs `alembic upgrade head` (creating the tables and
8 demo tickets), then starts Uvicorn. Compose waits for PostgreSQL's healthcheck before
starting the backend, and for the backend's healthcheck before starting the frontend.

Look at the data directly:

```bash
docker compose exec postgres psql -U deskflow -c "SELECT id, status, priority, title FROM tickets;"
```

Stop with `docker compose down` (add `-v` to delete the database volume).

---

## 4. Backend: API, database, tests

### REST API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service info |
| GET | `/health` | Liveness: process is up (no DB call, cheap) |
| GET | `/ready` | Readiness: returns 503 if PostgreSQL is unreachable |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/tickets` | List; filters `status`, `priority`, `category`, `unassigned`, `q`, `limit`, `offset` |
| GET | `/api/tickets/{id}` | One ticket (404 if missing) |
| POST | `/api/tickets` | Create (validated: email, enums, lengths) → 201 |
| PUT | `/api/tickets/{id}` | Partial update; only sent fields change |
| DELETE | `/api/tickets/{id}` | Delete → 204 |
| GET | `/api/tickets/stats` | Counts by status/priority/category, urgent-open, resolution rate |
| GET | `/api/activity` | Audit log of creates/updates/deletes (powers the activity feed) |
| GET | `/api/system` | Version, **git SHA**, environment, DB status (shown in the UI) |

The browser only ever calls relative `/api/...` URLs. It never needs to know the backend's
hostname: Vite proxies in development, Nginx proxies in Docker Compose, and the Ingress
routes in Kubernetes.

### Database and migrations

Two tables, `tickets` and `ticket_activity`, managed by Alembic:

- `0001_create_tickets_and_activity.py`: schema, indexes, CHECK constraints on enums
- `0002_seed_demo_tickets.py`: demo data, so a fresh environment isn't empty

Each backend replica runs `alembic upgrade head` on start. `alembic/env.py` takes a
PostgreSQL **advisory lock** first, so two Pods starting at the same moment can't race
each other's migrations.

Run without Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://deskflow:deskflow@localhost:5432/deskflow'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Tests

```bash
cd backend
pytest -v
```

- 31 tests covering every endpoint: happy paths, validation errors (422), missing
  resources (404), filters, stats maths, the activity log, readiness failure (503), the
  `/metrics` format.
- **No real database:** `tests/conftest.py` sets `DATABASE_URL` to in-memory SQLite and
  overrides FastAPI's `get_db` dependency. Every test gets fresh tables.
- CI additionally runs the Alembic migrations up → down → up against a throwaway
  PostgreSQL service container.

---

## 5. CI/CD pipeline (GitHub Actions)

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) runs on every push and PR to `main`:

```text
backend-test ─┐
frontend-build├─► build-scan-push (matrix: backend, frontend) ─► deploy (main only)
repo-scan ────┘
```

| Job | What it does | Why |
|-----|--------------|-----|
| `backend-test` | ruff lint + format check, `pytest -v` with coverage, Alembic up/down/up on Postgres | First quality gate: bad code never becomes an image |
| `frontend-build` | `npm ci && npm run build` | Proves the UI compiles |
| `repo-scan` | Trivy secret scan (blocking) + IaC misconfig scan (report) | Catches committed credentials |
| `build-scan-push` | `docker build` → Trivy (fails on fixable HIGH/CRITICAL) → push `ghcr.io/<owner>/deskflow-{backend,frontend}:<commit-sha>` | Only scanned images reach the registry |
| `deploy` | Log in to AWS (OIDC role or access-key secrets) → `helm upgrade --install --atomic` with the new SHA → smoke test checks `/api/system` reports the new SHA | Automatic, verifiable, auto-rollback on failure |

**Image tag = full Git commit SHA.** Every running Pod can be traced back to the exact
commit that produced it, and the UI's *Delivery pipeline* card shows that SHA.

Pull requests run tests, builds and scans but **never push or deploy**.

### One-time GitHub setup

1. Push this repo to GitHub (public, or give the instructor access).
2. After the first green run on `main`, open each package (**your profile → Packages →
   deskflow-backend / deskflow-frontend → Package settings**) and set visibility to
   **Public**, so EKS can pull without credentials. (Or keep them private and use
   `imagePullSecrets` in `values.yaml`.)
3. To enable automatic deployment once EKS exists (section 7), add **repository
   variables** (Settings → Secrets and variables → Actions → *Variables*):

   | Variable | Value |
   |----------|-------|
   | `DEPLOY_ENABLED` | `true` |
   | `AWS_REGION` | `ap-southeast-2` |
   | `EKS_CLUSTER_NAME` | `deskflow-eks` |
   | `AWS_DEPLOY_ROLE_ARN` | *(OIDC option only)* `terraform output -raw github_deploy_role_arn` |

   Then pick **one** way for the deploy job to authenticate to AWS:

   - **OIDC role (preferred, no stored keys):** set `github_repository` in
     `terraform.tfvars` before `terraform apply`, then set the `AWS_DEPLOY_ROLE_ARN`
     variable above. GitHub's OIDC token is exchanged for short-lived credentials, and
     the role only trusts this repo's `main` branch / `production` environment.
   - **Access keys (when your AWS Organization blocks IAM OIDC providers, as course
     sandbox accounts often do):** leave `AWS_DEPLOY_ROLE_ARN` unset and add the
     **repository secrets** `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (Settings →
     Secrets and variables → Actions → *Secrets*), using the same IAM user that ran
     `terraform apply`. That user is already cluster-admin as the cluster creator.

---

## 6. Security scanning (Trivy)

Each image is scanned twice in CI:

1. A full report (all severities) is printed and attached to the run summary.
2. **The gate:** `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1` fails the job
   if a high/critical vulnerability **that has a fix available** is present.

`--ignore-unfixed` is deliberate. Failing on CVEs nobody can patch yet would block every
release without making anything safer. Unfixed issues still show up in the report.

**What we found and fixed while building this project:**

| Finding | Explanation | Fix |
|---------|-------------|-----|
| `CVE-2026-97687` (urllib3, HIGH), `GHSA-6v7p-g79w-8964` (msgpack, HIGH), `CVE-2025-47273` (setuptools, HIGH) | Not our dependencies: they were **vendored inside `pip`** in the image's virtualenv. urllib3's flaw allows traffic interception through an HTTPS proxy TLS override. | pip is only needed at build time, so the Dockerfile uninstalls it from the runtime image. |
| 44 HIGH CVEs (util-linux, libacl, …), all "affected / no fix yet" | Debian packages in `python:3.12-slim` | Switched the base to `python:3.12-alpine`: **0 HIGH/CRITICAL**, and ~100 MB smaller |

Result: both images scan clean at HIGH/CRITICAL.

> **Supply-chain note:** in March 2026 the `aquasecurity/trivy-action` tags and Trivy
> v0.69.4 were compromised (CVE-2026-33634). This pipeline therefore runs the official
> `aquasec/trivy:0.69.3` image directly instead of the GitHub Action.

Container scanning is one layer of several: **SAST** (code), **dependency scanning**,
**secret scanning** (the `repo-scan` job), **container scanning** (Trivy on images),
**IaC scanning** (Trivy misconfig on Dockerfiles/Helm/Terraform) and **runtime
security** (non-root users, read-only root filesystems, dropped capabilities, Pod
Security Admission in Kubernetes).

---

## 7. AWS infrastructure (Terraform)

```text
AWS (ap-southeast-2)
 ├── VPC 10.0.0.0/16
 │    ├── 2 public subnets  (Internet Gateway, NAT, load balancers)
 │    ├── 2 private subnets (worker nodes)
 │    └── 1 NAT gateway
 ├── EKS 1.35 (standard support only; avoids extended-support fees)
 │    ├── managed node group: 3 × t3.medium (min 2, max 4), AL2023
 │    └── add-ons: vpc-cni, coredns, kube-proxy, pod-identity, ebs-csi
 └── IAM: node/cluster roles (+ optional GitHub OIDC deploy role)
```

Prerequisites: Terraform ≥ 1.6, AWS CLI configured with an identity allowed to create
VPC/EC2/EKS/IAM resources in the region. With a named CLI profile, run
`export AWS_PROFILE=<profile>` first. Terraform, kubectl and the scripts all honour it.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars    # optional: github_repository = "you/your-repo" (OIDC)
terraform init
terraform plan                                  # review: VPC, subnets, NAT, EKS, node group, IAM
terraform apply                                 # ~15 minutes
$(terraform output -raw configure_kubectl)      # aws eks update-kubeconfig ...
kubectl get nodes
```

No credentials live in this repo: Terraform reads them from your AWS CLI profile, and
`*.tfvars` / `*.tfstate` are git-ignored (only `terraform.tfvars.example` is committed).

**Cost:** roughly $0.10/h (EKS) + 3 × $0.045/h (nodes) + $0.056/h (NAT) + load balancer
≈ **$0.30/hour**. Destroy it when you're done (section 11).

---

## 8. Kubernetes + Helm

### On EKS

```bash
GRAFANA_PASSWORD='pick-one' scripts/bootstrap-cluster.sh eks   # namespaces, gp3, metrics-server, Prometheus/Grafana, Traefik
```

Then either push to `main` (with `DEPLOY_ENABLED=true`, CI deploys) or deploy by hand:

```bash
helm upgrade --install deskflow ./helm/deskflow -n deskflow --create-namespace \
  -f helm/deskflow/values-eks.yaml \
  --set backend.image.repository=ghcr.io/<owner>/deskflow-backend  --set backend.image.tag=<sha> \
  --set frontend.image.repository=ghcr.io/<owner>/deskflow-frontend --set frontend.image.tag=<sha>
```

### On minikube (local rehearsal)

```bash
minikube start --cpus 4 --memory 6g
scripts/bootstrap-cluster.sh minikube
scripts/deploy-local.sh            # builds images, tags with git SHA, loads into minikube, helm install
minikube tunnel                    # separate terminal: gives Traefik's LoadBalancer an IP
```

### What the chart creates

| Resource | Notes |
|----------|-------|
| `Deployment` backend | 2–6 Pods (HPA), rolling update with `maxUnavailable: 0`, startup/liveness/readiness probes, non-root, read-only root FS |
| `Deployment` frontend | 2 Pods, Nginx on 8080, read-only root FS |
| `StatefulSet` postgresql | 1 Pod + PVC (EBS gp3 on EKS); password in a generated `Secret` kept across upgrades |
| `Service` ×3 | ClusterIP for backend, frontend, postgresql |
| `Ingress` | `/api`, `/docs`, `/openapi.json` → backend; `/` → frontend |
| `HorizontalPodAutoscaler` | backend, target 60 % CPU of the 100m request |
| `PodDisruptionBudget` ×2 | keep ≥1 Pod during node drains |
| `ServiceMonitor` | tells Prometheus to scrape backend `/metrics` |
| `ConfigMap` dashboard | Grafana auto-loads the DeskFlow dashboard |
| helm test Pod | `helm test deskflow -n deskflow` checks `/ready`, the UI and the `/api` proxy |

```bash
kubectl get pods,svc,ingress,hpa -n deskflow
helm list -n deskflow
helm history deskflow -n deskflow
helm rollback deskflow <revision> -n deskflow
```

**PostgreSQL in Kubernetes vs Amazon RDS:** the in-cluster StatefulSet is simple and
free, which suits a classroom. But backups, failover, patching and storage are then your
problem, and a single EBS volume lives in one AZ. In production you'd use RDS
(Multi-AZ, automated backups, point-in-time recovery). The chart already supports that:
`postgresql.enabled=false` plus `externalDatabase.host` / `existingSecret`.

---

## 9. Ingress, autoscaling and monitoring

### Ingress

An Ingress resource is only configuration; **Traefik** (the Ingress controller) actually
implements it. On EKS, Traefik's `LoadBalancer` Service provisions an AWS NLB:

```bash
kubectl get ingress -n deskflow
kubectl get svc traefik -n ingress     # EXTERNAL-IP = NLB DNS name → open http://<that>/
```

Locally `values-dev.yaml` uses the host `deskflow.local`. Add `127.0.0.1 deskflow.local`
to your hosts file and run `minikube tunnel`.

### Horizontal Pod Autoscaler

```bash
kubectl get hpa -n deskflow               # TARGETS cpu: 3%/60%  REPLICAS 2
scripts/load-test.sh 6 300                # 6 in-cluster load generators for 5 minutes
kubectl get hpa -n deskflow -w            # watch replicas climb 2 → 3 → 4 …
kubectl top pods -n deskflow
```

The HPA needs CPU **requests** (it scales on usage ÷ request) and **metrics-server**.
Scale-down waits 2 minutes, so short dips don't make it flap.

### Prometheus + Grafana

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090 -n monitoring
# http://localhost:9090/targets → serviceMonitor/deskflow/deskflow-backend is UP

kubectl port-forward svc/monitoring-grafana 3001:80 -n monitoring
# http://localhost:3001 (admin / $GRAFANA_PASSWORD) → Dashboards → "DeskFlow — API overview"
```

The dashboard (provisioned automatically from `helm/deskflow/dashboards/`) answers:

- How many requests are arriving, per endpoint? → *Request rate by endpoint*
- Which endpoint is slow? → *Latency p50/p95/p99*
- Are errors increasing? → *Error rate (5xx)*, *Responses by status class*
- Is CPU increasing? Is the HPA scaling? → *Backend CPU per pod*, *HPA replicas*
- Business view → *Tickets created* (custom `deskflow_tickets_created_total` counter)

---

## 10. Troubleshooting lab

See [troubleshooting/README.md](troubleshooting/README.md): broken image
(`ImagePullBackOff`), broken Service selector (no endpoints), and a bonus broken
readiness probe, each with its investigation path and fix.

---

## 11. Tear down

```bash
scripts/destroy-eks.sh     # helm uninstall → delete PVCs/LB → terraform destroy
```

Order matters. Kubernetes created an NLB and EBS volumes that Terraform doesn't know
about, and a leftover load balancer blocks VPC deletion. The script removes those first,
then runs `terraform destroy`. Afterwards, check the AWS console for leftovers
(EC2 → Load Balancers / Volumes, VPC).
