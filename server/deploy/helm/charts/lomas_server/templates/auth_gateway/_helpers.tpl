{{/*Name of the components ------------------------------------------------------------*/}}

{{- define "lomas.caddy.name" -}}caddy{{- end }}
{{- define "lomas.oauth2Proxy.name" -}}oauth2Proxy{{- end }}


{{/*Fullnames ------------------------------------------------------------*/}}

{{- define "lomas.caddy.fullname" -}}
{{- printf "%s-caddy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "lomas.oauth2Proxy.fullname" -}}
{{- printf "%s-oauth2Proxy" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/*Selector labels ------------------------------------------------------------*/}}

{{- define "lomas.caddy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2Proxy.selectorLabels" -}}
{{ include "lomas.selectorLabels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2Proxy.name" . }}
{{- end }}


{{/*Labels* ------------------------------------------------------------*/}}

{{- define "lomas.caddy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.caddy.name" . }}
{{- end }}
{{- define "lomas.oauth2Proxy.labels" -}}
{{ include "lomas.labels" . }}
app.kubernetes.io/component: {{ include "lomas.oauth2Proxy.name" . }}
{{- end }}


{{/* Secrets  ------------------------------------------------------------*/}}

{{- define "lomas.oauth2Proxy.cookieSecretName" -}}
{{- $secretName := .Values.oauth2Proxy.config.cookieSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-cookie-secret" (include "lomas.oauth2Proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2Proxy.cookieSecretKey" -}}
    {{- if and .Values.oauth2Proxy.config.cookieSecretExistingSecretName .Values.oauth2Proxy.config.cookieSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.oauth2Proxy.config.cookieSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "cookie-secret" -}}
    {{- end -}}
{{- end -}}

{{- define "lomas.oauth2Proxy.clientSecretName" -}}
{{- $secretName := .Values.oauth2Proxy.config.clientSecretExistingSecretName -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-cookie-secret" (include "lomas.oauth2Proxy.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.oauth2Proxy.clientSecretKey" -}}
    {{- if and .Values.oauth2Proxy.config.clientSecretExistingSecretName .Values.oauth2Proxy.config.clientSecretExistingSecretKey -}}
        {{- printf "%s" (tpl .Values.oauth2Proxy.config.clientSecretExistingSecretKey $) -}}
    {{- else -}}
        {{- printf "client-secret" -}}
    {{- end -}}
{{- end -}}

{{/* ConfigMap  ------------------------------------------------------------*/}}
{{- define "lomas.caddy.configMapName" -}}
{{ include "lomas.caddy.fullname" . }}-config
{{- end }}