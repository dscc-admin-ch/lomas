{{/* Secrets names and keys */}}

{{/* Enforce MongoDB only has one password in the list -------------------------*/}}

{{- if gt (len .Values.mongodb.auth.passwords) 1 }}
{{- fail "Lomas only supports a single password in 'mongodb.auth.passwords'." }}
{{- end }}


{{/* Lomas Admin ---------------------------------------------------------------*/}}

{{- define "lomas-admin.secretName" -}}
{{- $secretName := .Values.admin.client_secret_existing_secret -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-admin-secret" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas-admin.secretKey" -}}
    {{- if and .Values.admin.client_secret_existing_secret .Values.admin.client_secret_secret_key -}}
        {{- printf "%s" (tpl .Values.admin.client_secret_secret_key $) -}}
    {{- else -}}
        {{- printf "client-secret" -}}
    {{- end -}}
{{- end -}}


{{/* Lomas Service  ------------------------------------------------------------*/}}

{{- define "lomas-service.secretName" -}}
{{- $secretName := .Values.admin.lomas_service_existing_secret -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-service-secret" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas-service.secretKey" -}}
    {{- if and .Values.admin.lomas_service_existing_secret .Values.admin.lomas_service_secret_key -}}
        {{- printf "%s" (tpl .Values.admin.lomas_service_secret_key $) -}}
    {{- else -}}
        {{- printf "client-secret" -}}
    {{- end -}}
{{- end -}}


{{/* Private DB Credentials ----------------------------------------------------*/}}

{{- define "lomas-service.private-db-credentials-secrets" -}}
{{- $result := list }}
{{- range $i, $cred := .Values.server.runtime_args.private_db_credentials }}
  {{- $name := "" }}
  {{- if $cred.existing_secret }}
    {{- $name = $cred.existing_secret }}
  {{- else }}
    {{- $name = printf "%s-private-db-credentials-%d" (include "lomas.fullname" $) $i }}
  {{- end }}
  {{- $result = append $result (tpl $name $) }}
{{- end }}
{{- toYaml $result }}
{{- end }}