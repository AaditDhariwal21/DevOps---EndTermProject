{{/* Chart name, truncated to the 63-char DNS label limit. */}}
{{- define "deskflow.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Fully qualified app name: "<release>" if it already contains the chart name, else "<release>-<chart>". */}}
{{- define "deskflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "deskflow.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Common labels. */}}
{{- define "deskflow.labels" -}}
helm.sh/chart: {{ include "deskflow.chart" . }}
app.kubernetes.io/part-of: deskflow
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end }}

{{/*
Selector labels for one component. Services find Pods through exactly these
labels — see troubleshooting/broken-service.yaml for what happens when they differ.
Usage: include "deskflow.selectorLabels" (dict "ctx" $ "component" "backend")
*/}}
{{- define "deskflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "deskflow.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "deskflow.componentLabels" -}}
{{ include "deskflow.labels" .ctx }}
{{ include "deskflow.selectorLabels" . }}
{{- end }}

{{/* "<repository>:<tag>", tag defaulting to the chart appVersion. */}}
{{- define "deskflow.image" -}}
{{- printf "%s:%s" .repository (default $.appVersion .tag | toString) }}
{{- end }}

{{- define "deskflow.backendImage" -}}
{{- include "deskflow.image" (merge (dict "appVersion" .Chart.AppVersion) .Values.backend.image) }}
{{- end }}

{{- define "deskflow.frontendImage" -}}
{{- include "deskflow.image" (merge (dict "appVersion" .Chart.AppVersion) .Values.frontend.image) }}
{{- end }}

{{/* ----------------------------------------------------------- database */}}
{{- define "deskflow.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "deskflow.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "deskflow.db.secretName" -}}
{{- if .Values.postgresql.enabled }}
{{- default (include "deskflow.postgresql.fullname" .) .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- required "externalDatabase.existingSecret is required when postgresql.enabled=false" .Values.externalDatabase.existingSecret }}
{{- end }}
{{- end }}

{{- define "deskflow.db.host" -}}
{{- if .Values.postgresql.enabled }}
{{- include "deskflow.postgresql.fullname" . }}
{{- else }}
{{- required "externalDatabase.host is required when postgresql.enabled=false" .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{- define "deskflow.db.port" -}}
{{- ternary 5432 .Values.externalDatabase.port .Values.postgresql.enabled }}
{{- end }}

{{- define "deskflow.db.user" -}}
{{- ternary .Values.postgresql.auth.username .Values.externalDatabase.username .Values.postgresql.enabled }}
{{- end }}

{{- define "deskflow.db.name" -}}
{{- ternary .Values.postgresql.auth.database .Values.externalDatabase.database .Values.postgresql.enabled }}
{{- end }}

{{/* Hardened container defaults shared by app containers. */}}
{{- define "deskflow.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
capabilities:
  drop: ["ALL"]
seccompProfile:
  type: RuntimeDefault
{{- end }}
