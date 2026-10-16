# syntax=docker/dockerfile:1

# ---------- Stage 1: build the React app with Node ----------
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Baked into the bundle so the UI can show which commit it was built from.
ARG GIT_SHA=local
ENV VITE_GIT_SHA=${GIT_SHA}
RUN npm run build

# ---------- Stage 2: serve static files with unprivileged Nginx ----------
# Only dist/ is copied over: Node, npm and node_modules never reach the runtime image.
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime

ARG GIT_SHA=local
LABEL org.opencontainers.image.title="deskflow-frontend" \
      org.opencontainers.image.description="DeskFlow React UI served by Nginx" \
      org.opencontainers.image.revision=${GIT_SHA}

# Apply Alpine security patches (needs root briefly), then drop back to nginx (uid 101).
USER root
RUN apk upgrade --no-cache
USER 101

# Where /api is proxied to; overridden per environment.
ENV BACKEND_URL=http://backend:8000

COPY nginx/security-headers.conf /etc/nginx/security-headers.conf
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/nginx-health || exit 1
