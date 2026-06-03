{{/*
Expand the name of the chart.
*/}}
{{- define "lomas.tempo.name" -}}
tempo
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "lomas.tempo.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- printf "%s-tempo" .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s-tempo" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "lomas.tempo.labels" -}}
helm.sh/chart: {{ include "lomas.chart" . }}
{{ include "lomas.tempo.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "lomas.tempo.selectorLabels" -}}
app.kubernetes.io/name: {{ include "lomas.tempo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
