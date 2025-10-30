{{- define "udb-api.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "udb-api.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "udb-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version -}}
{{- end -}}
