{{/*Name of the components*/}}
{{- define "lomas.admin.demo-setup.name" -}}admin-demo-setup{{- end }}

{{/*Fullnames*/}}
{{- define "lomas.admin.demo-setup.fullname" -}}
{{- printf "%s-%s" (include "lomas.fullname" .) (include "lomas.admin.demo-setup.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*Labels*/}}
{{- define "lomas.admin.demo-setup.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.admin.demo-setup.name" . }}
{{- end }}
