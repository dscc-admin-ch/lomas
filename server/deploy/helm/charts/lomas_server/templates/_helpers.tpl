{{/*
Expand the name of the chart.
*/}}
{{- define "lomas.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "lomas.fullname" -}}
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

{{/*Create chart name and version as used by the chart label.*/}}
{{- define "lomas.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*Selector labels*/}}
{{- define "lomas.selectorLabels" -}}
app.kubernetes.io/name: {{ include "lomas.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*Common labels*/}}
{{- define "lomas.labels" -}}
helm.sh/chart: {{ include "lomas.chart" . }}
{{ include "lomas.server.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Create the name of the service account to use
We keep this here for reference.
*/}}
{{- define "lomas.serviceAccountName" -}}
{{- if .Values.server.serviceAccount.create }}
{{- default (include "lomas.fullname" .) .Values.server.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.server.serviceAccount.name }}
{{- end }}
{{- end }}
