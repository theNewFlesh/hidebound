{{- define "_values" -}}
    {{- $output := deepCopy .Values -}}
    {{- $env := $output.env_configmap -}}
    {{- $secret := $output.env_secret -}}

    {{- /* CONVERT YAML ENV VARS TO STRINGS */ -}}
    {{- $vars := list
        "HIDEBOUND_WORKFLOW"
        "HIDEBOUND_SPECIFICATION_FILES"
        "HIDEBOUND_DASK_GATEWAY_CLUSTER_OPTIONS"
    -}}
    {{- range $key := $vars -}}
        {{- $val := (get $env $key) | default list | toYaml -}}
        {{- $env := set $env $key $val -}}
    {{- end -}}

    {{- /* SET ENV VALUES TO STRING */ -}}
    {{- range $key, $val := $env -}}
        {{- $temp := $val | toString -}}
        {{- if eq ($temp | lower) "true" -}}
            {{- $env := set $env $key "True" -}}
        {{- else if eq ($temp | lower) "false" -}}
            {{- $env := set $env $key "False" -}}
        {{- else -}}
            {{- $env := set $env $key $temp -}}
        {{- end -}}
    {{- end -}}

    {{- /* CONVERT SECRET YAML ENV VARS TO STRINGS AND ENCRYPT */ -}}
    {{- $secrets := list
        "HIDEBOUND_WEBHOOKS"
        "HIDEBOUND_EXPORTERS"
    -}}
    {{- range $key := $secrets -}}
        {{- $val := (get $secret $key) | toYaml | b64enc -}}
        {{- $secret := set $secret $key $val -}}
    {{- end -}}

    {{ $output | toYaml }}
{{- end -}}
