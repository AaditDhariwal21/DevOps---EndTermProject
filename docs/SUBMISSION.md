# Submission checklist: rubric → evidence

Every rubric line, where it lives in the repo, and the screenshot/command that proves it.
Save screenshots in [`docs/screenshots/`](screenshots/) with the suggested file names.

## M1 Application (10)

| Criterion | Evidence |
|-----------|----------|
| FastAPI starts, `/health` responds | `curl localhost:8000/health` → `{"status":"ok"}` |
| ≥4 REST endpoints (GET/POST/PUT/DELETE) | `backend/app/routers/tickets.py`: 7 ticket/activity endpoints; Swagger at `/docs` |
| PostgreSQL table via Alembic | `backend/alembic/versions/0001_…`, `0002_…` |
| Frontend renders + calls API | `frontend/src/api.js` → `/api/tickets`, `/api/tickets/stats`, `/api/activity`, `/api/system` |
| Responsive UI | Sidebar becomes a drawer < 860 px; table becomes cards < 640 px |

Screenshots: `app-desktop.png`, `app-mobile.png` (DevTools device mode), `swagger.png`

## M2 Testing (10)

| Criterion | Evidence |
|-----------|----------|
| pytest runs | `cd backend && pytest -v` (31 passed) |
| ≥5 tests, ≥3 endpoints | `tests/test_tickets.py`, `tests/test_system.py`: every endpoint covered |
| Test DB, not production | `tests/conftest.py`: in-memory SQLite + `get_db` override |
| pytest.ini / conftest.py | `backend/pytest.ini`, `backend/tests/conftest.py` |

Screenshot: `pytest.png` (output of `pytest -v`)

## M3 Git & GitHub (5)

| Criterion | Evidence |
|-----------|----------|
| Public repo | GitHub URL |
| Meaningful commits | `git log --oneline` (conventional-commit style: `feat(helm): …`, `ci: …`) |
| `.gitignore` | excludes `.env`, `__pycache__`, `node_modules`, `.venv`, `*.tfstate`, `*.tfvars` |

Screenshot: `commits.png` (GitHub → Commits, ≥10)

## M4 Docker (10)

| Criterion | Evidence |
|-----------|----------|
| backend Dockerfile builds | `docker build -t deskflow-backend:local ./backend` |
| frontend multi-stage | `frontend/Dockerfile`: `node:24-alpine AS build` → `nginx-unprivileged` runtime |
| Non-root | backend `USER 10001`; frontend uid 101. Check: `docker compose exec backend id` |
| Compose starts all three | `docker compose up --build`, then `docker compose ps` (all *healthy*) |

Screenshots: `compose-up.png`, `compose-ps.png`, `app-localhost-3000.png`

## M5 CI/CD (15)

| Criterion | Evidence |
|-----------|----------|
| Workflow file | `.github/workflows/ci-cd.yml` |
| Triggers on push to `main` | `on.push.branches: [main]` |
| pytest job fails the build | `backend-test`; `build-scan-push` `needs:` it |
| Frontend built | `frontend-build` job |
| Both images built | `build-scan-push` matrix `[backend, frontend]` |
| Pushed to GHCR | `docker push ghcr.io/<owner>/deskflow-*` |
| SHA tags, not `latest` | tag = `${{ github.sha }}`; no `latest` tag is ever pushed |

Screenshots: `actions-green.png` (run graph), `ghcr-packages.png` (SHA tags)
Tip: prove the gate works by pushing a failing test on a branch/PR and screenshotting the red run.

## M6 Trivy (5)

| Criterion | Evidence |
|-----------|----------|
| Scans both images in CI | "Trivy gate" step, matrix over both images |
| Fails on HIGH/CRITICAL | `--severity HIGH,CRITICAL --exit-code 1` |
| Explain a CVE / clean result | Paragraph below |

Screenshot: `trivy.png` (job log or run summary table)

**Written explanation (paste into the form):**

> Trivy scanned both container images (OS packages from the Alpine base image, plus every
> Python package in the backend's virtualenv and the files in the Nginx image) against
> its vulnerability database. The pipeline fails if any HIGH or CRITICAL vulnerability
> with an available fix is found. The first scan failed on the backend: CVE-2026-97687
> (HIGH) in urllib3 and two other HIGHs. They weren't our dependencies but copies
> *vendored inside pip*. pip is only needed at build time, so we removed it from the
> runtime image. We also replaced the Debian slim base (44 unfixed HIGH CVEs) with
> Alpine. Both images now scan clean at HIGH/CRITICAL. A clean scan means no *known*
> fixable high-severity CVEs today; it doesn't prove the app is secure, which is why
> the pipeline also scans for committed secrets and IaC misconfigurations.

## M7 Terraform (15)

| Criterion | Evidence |
|-----------|----------|
| Valid HCL | `terraform validate` |
| init | `terraform init` |
| Non-empty plan | `terraform plan` |
| VPC with ≥2 public subnets | `module "vpc"`: `az_count = 2` public + 2 private |
| EKS + node group | `module "eks"`, `eks_managed_node_groups.general` |
| Clean destroy | `scripts/destroy-eks.sh` |
| `terraform.tfvars.example`, no secrets | committed example; `*.tfvars`/state git-ignored |

Screenshots: `tf-plan.png`, `aws-vpc.png`, `aws-eks.png` (ap-south-1), `tf-destroy.png`

## M8 Kubernetes + Helm (15)

| Criterion | Evidence |
|-----------|----------|
| `k8s/namespace.yaml` | `kubectl apply -f k8s/namespace.yaml` |
| Chart with Chart.yaml, values.yaml, templates | `helm/deskflow/` |
| `helm upgrade --install` works | CI deploy job or manual command in README §8 |
| ≥2 replicas each | backend HPA min 2; frontend `replicaCount: 2` |
| ClusterIP Services | `kubectl get svc -n deskflow` |
| Ingress `/` + `/api` | `helm/deskflow/templates/ingress.yaml` |
| All pods Running | `kubectl get pods -n deskflow` |

Screenshots: `kubectl-pods.png`, `kubectl-svc.png`, `helm-list.png`, `app-ingress.png` (browser on the NLB hostname)

## M9 Observability (10)

| Criterion | Evidence |
|-----------|----------|
| `/metrics` Prometheus format | `curl http://<host>/metrics` (or port-forward the backend) |
| Prometheus scraping the app | Prometheus → Status → Targets: `serviceMonitor/deskflow/deskflow-backend` **UP** |
| Grafana accessible | `kubectl port-forward svc/monitoring-grafana 3001:80 -n monitoring` |
| Panel with live metrics | "DeskFlow — API overview" dashboard (run `scripts/load-test.sh` first) |

Screenshots: `metrics-curl.png`, `prometheus-targets.png`, `grafana-dashboard.png`, `hpa-scaling.png`

## M10 Presentation (5)

- `README.md` at the root ✔
- Live demo: follow [DEMO.md](DEMO.md)

## Final pre-submission checks

```bash
git log --oneline | wc -l                 # ≥ 10
git ls-files | grep -E '\.tfstate|\.tfvars$|\.env$'   # must print nothing
docker run --rm -v "$PWD:/repo" aquasec/trivy:0.69.3 fs --scanners secret /repo   # no secrets
```

After grading: **`scripts/destroy-eks.sh`** and confirm in the AWS console that nothing is left running.
