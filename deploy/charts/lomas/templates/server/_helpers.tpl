{{/*Name of the components*/}}
{{- define "lomas.server.name" -}}server{{- end }}
{{- define "lomas.worker.name" -}}worker{{- end }}

{{/*Fullnames*/}}
{{- define "lomas.server.fullname" -}}
{{- printf "%s-server" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "lomas.worker.fullname" -}}
{{- printf "%s-worker" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*Selector labels*/}}
{{- define "lomas.server.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.server.name" . }}
{{- end }}
{{- define "lomas.worker.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.worker.name" . }}
{{- end }}


{{/*Labels*/}}
{{- define "lomas.server.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.server.name" . }}
{{- end }}
{{- define "lomas.worker.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.worker.name" . }}
{{- end }}
