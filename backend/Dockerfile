# syntax=docker/dockerfile:1
#
# Alpine base: Trivy reported 44 unfixed HIGH CVEs in the Debian-based
# python:3.12-slim OS packages vs 0 on python:3.12-alpine (and ~100 MB smaller).
# All dependencies ship musllinux wheels, so nothing is compiled here.

# ---------- Stage 1: build a virtualenv with the dependencies ----------
FROM python:3.12-alpine AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# pip is only needed to install; remove it afterwards. Trivy flagged HIGH CVEs in
# pip's own vendored libraries (urllib3, msgpack, setuptools) — none of which the
# app uses — so the cleanest fix is to not ship pip at all.
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip uninstall -y pip

# ---------- Stage 2: slim runtime image ----------
FROM python:3.12-alpine AS runtime

ARG GIT_SHA=local
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    GIT_SHA=${GIT_SHA}

LABEL org.opencontainers.image.title="deskflow-backend" \
      org.opencontainers.image.description="DeskFlow FastAPI backend" \
      org.opencontainers.image.revision=${GIT_SHA}

# Pull in OS security patches and drop the base image's own pip too:
# the runtime image has no package installer at all.
RUN apk upgrade --no-cache \
    && python -m pip uninstall -y pip

# Dedicated unprivileged user (fixed UID so Kubernetes runAsNonRoot can verify it).
RUN addgroup -S -g 10001 app \
    && adduser -S -D -u 10001 -G app -h /app -s /sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .
RUN chmod 0555 docker-entrypoint.sh && chown -R app:app /app

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

# Runs `alembic upgrade head`, then execs uvicorn as PID 1.
ENTRYPOINT ["./docker-entrypoint.sh"]
