{{/*Name of the components ------------------------------------------------------------*/}}

{{- define "lomas.caddy.name" -}}caddy{{- end }}
{{- define "lomas.oauth2proxy.name" -}}oauth2proxy{{- end }}


{{/*Fullnames ------------------------------------------------------------*/}}

{{- define "lomas.caddy.fullname" -}}
{{- printf "%s-caddy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "lomas.oauth2proxy.fullname" -}}
{{- printf "%s-oauth2proxy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/*Selector labels ------------------------------------------------------------*/}}

{{- define "lomas.caddy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2proxy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2proxy.name" . }}
{{- end }}


{{/*Labels* ------------------------------------------------------------*/}}

{{- define "lomas.caddy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2proxy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2proxy.name" . }}
{{- end }}


{{/* Secrets  ------------------------------------------------------------*/}}

{{- define "lomas.oauth2proxy.cookieSecretName" -}}
{{- $secretName := .Values.oauth2proxy.config.cookieSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-cookie-secret" (include "lomas.oauth2proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2proxy.cookieSecretKey" -}}
    {{- if and .Values.oauth2proxy.config.cookieSecretExistingSecretName .Values.oauth2proxy.config.cookieSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.oauth2proxy.config.cookieSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "cookie-secret" -}}
    {{- end -}}
{{- end -}}

{{- define "lomas.oauth2proxy.clientSecretName" -}}
{{- $secretName := .Values.oauth2proxy.config.clientSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-client-secret" (include "lomas.oauth2proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2proxy.clientSecretKey" -}}
    {{- if and .Values.oauth2proxy.config.clientSecretExistingSecretName .Values.oauth2proxy.config.clientSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.oauth2proxy.config.clientSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "client-secret" -}}
    {{- end -}}
{{- end -}}

{{/* ConfigMap  ------------------------------------------------------------*/}}
{{- define "lomas.caddy.configMapName" -}}
{{ include "lomas.caddy.fullname" . }}-config
{{- end }}