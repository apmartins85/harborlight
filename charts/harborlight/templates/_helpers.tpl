{{- define "harborlight.name" -}}
{{- printf "%s-harborlight" .Release.Name | trunc 48 | trimSuffix "-" -}}
{{- end -}}
