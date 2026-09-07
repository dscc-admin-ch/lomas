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


{{/* PVC names */}}
{{- define "lomas.server.dataPVCName" -}}
{{- printf "%s-%s" (include "lomas.server.fullname" .) "data" }}
{{- end}}
{{- define "lomas.server.backupPVCName" -}}
{{- printf "%s-%s" (include "lomas.server.fullname" .) "backup" }}
{{- end}}
{{- define "lomas.server.dbPVCName" -}}
{{- printf "%s-%s" (include "lomas.server.fullname" .) "db" }}
{{- end}}

{{/* Secrets names and keys  ------------------------------------------------------------*/}}

{{/* bootstrap secret */}}
{{- define "lomas.server.bootstrapSecretName" -}}
{{- $secretName := .Values.server.runtime_args.bootstrap.existingSecret -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-server-bootstrap-secret" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.server.bootstrapSecretKey" -}}
    {{- if and .Values.server.runtime_args.bootstrap.existingSecret .Values.server.runtime_args.bootstrap.existingKey -}}
        {{- printf "%s" (tpl .Values.server.runtime_args.bootstrap.existingKey $) -}}
    {{- else -}}
        {{- printf "bootstrap" -}}
    {{- end -}}
{{- end -}}

{{/* woker api key secret */}}
{{- define "lomas.server.workerApiKeySecretName" -}}
{{- $secretName := .Values.server.runtime_args.worker_api_key.existingSecret -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-server-worker-api-key-secret" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.server.workerApiKeySecretKey" -}}
    {{- if and .Values.server.runtime_args.worker_api_key.existingSecret .Values.server.runtime_args.worker_api_key.existingKey -}}
        {{- printf "%s" (tpl .Values.server.runtime_args.worker_api_key.existingKey $) -}}
    {{- else -}}
        {{- printf "worker_api_key" -}}
    {{- end -}}
{{- end -}}

{{/* s3 backup uri secret */}}
{{- define "lomas.server.s3BackupUriSecretName" -}}
{{- $secretName := .Values.server.runtime_args.s3Backup.uri.existingSecret -}}
{{- if $secretName -}}
    {{- printf "%s" (tpl $secretName $) -}}
{{- else -}}
    {{- printf "%s-server-s3-backup-uri-secret" (include "lomas.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "lomas.server.s3BackupUriSecretKey" -}}
    {{- if and .Values.server.runtime_args.s3Backup.uri.existingSecret .Values.server.runtime_args.s3Backup.uri.existingKey -}}
        {{- printf "%s" (tpl .Values.server.runtime_args.s3Backup.uri.existingKey $) -}}
    {{- else -}}
        {{- printf "s3-backup-uri" -}}
    {{- end -}}
{{- end -}}

{{/* Private DB credentials */}}
{{- define "lomas.server.private-db-credentials-secrets" -}}
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
