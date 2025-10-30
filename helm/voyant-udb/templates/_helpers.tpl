{{- define "voyant-udb.fullname" -}}
{{- printf "%s-%s" .Chart.Name (include "voyant-udb.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "voyant-udb.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}
