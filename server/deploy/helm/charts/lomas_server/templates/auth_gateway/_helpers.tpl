{{/*Name of the components ------------------------------------------------------------*/}}

{{- define "lomas.caddy.name" -}}caddy{{- end }}
{{- define "lomas.oauth2-proxy.name" -}}oauth2-proxy{{- end }}


{{/*Fullnames ------------------------------------------------------------*/}}

{{- define "lomas.caddy.fullname" -}}
{{- printf "%s-caddy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "lomas.oauth2-proxy.fullname" -}}
{{- printf "%s-oauth2-proxy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/*Selector labels ------------------------------------------------------------*/}}

{{- define "lomas.caddy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2-proxy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2-proxy.name" . }}
{{- end }}


{{/*Labels* ------------------------------------------------------------/}}

{{- define "lomas.caddy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2-proxy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2-proxy.name" . }}
{{- end }}


{{/* Secrets  ------------------------------------------------------------*/}}

{{- define "lomas.oauth2-proxy.cookieSecretName" -}}
{{- $secretName := .Values.admin.cookieSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-cookie-secret" (include "lomas.oauth2-proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2-proxy.cookieSecretKey" -}}
    {{- if and .Values.admin.cookieSecretExistingSecretName .Values.admin.cookieSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.admin.cookieSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "cookie-secret" -}}
    {{- end -}}
{{- end -}}

{{- define "lomas.oauth2-proxy.clientSecretName" -}}
{{- $secretName := .Values.admin.clientSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-cookie-secret" (include "lomas.oauth2-proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2-proxy.clientSecretKey" -}}
    {{- if and .Values.admin.clientSecretExistingSecretName .Values.admin.clientSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.admin.clientSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "client-secret" -}}
    {{- end -}}
{{- end -}}