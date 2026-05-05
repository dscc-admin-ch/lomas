{{/*Name of the components*/}}
{{- define "lomas.demoSetupJob.name" -}}admin-demo-setup{{- end }}

{{/*Fullnames*/}}
{{- define "lomas.demoSetupJob.fullname" -}}
{{- printf "%s-%s" (include "lomas.fullname" .) (include "lomas.demoSetupJob.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*Labels*/}}
{{- define "lomas.demoSetupJob.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.demoSetupJob.name" . }}
{{- end }}
