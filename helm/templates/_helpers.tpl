{{- define "_values" -}}
    {{- $output := deepCopy .Values -}}
    {{- $env := $output.env_configmap -}}
    {{- $secret := $output.env_secret -}}

    {{- /* COERCE ENV VALUES TO STRINGS */ -}}
    {{- range $key, $val := $env -}}
        {{- if eq (kindOf $val) "slice" -}}
            {{- $env := set $env $key ($val | toYaml) -}}
        {{- else if eq (kindOf $val) "bool" -}}
            {{- if eq $val true -}}
                {{- $env := set $env $key "True" -}}
            {{- else -}}
                {{- $env := set $env $key "False" -}}
            {{- end -}}
        {{- else -}}
            {{- $env := set $env $key ($val | toString) -}}
        {{- end -}}
    {{- end -}}

    {{- /* CONVERT SECRET VALUES TO STRINGS AND ENCRYPT */ -}}
    {{- range $key, $val := $secret -}}
        {{- $secret := set $secret $key ($val |toYaml | b64enc) -}}
    {{- end -}}

    {{ $output | toYaml }}
{{- end -}}
