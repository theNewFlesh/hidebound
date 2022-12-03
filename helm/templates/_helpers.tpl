{{- define "_overlay" -}}
    {{- /* patch base dict with overlay dict */ -}}

    {{- $output := .Values.base -}}
    {{- if ne .Values.overlay "base" -}}
        {{- $output := (get .Values.overlays .Values.overlay) -}}
        {{- $output := deepCopy .Values.base | merge $output -}}
        {{ $output | toYaml }}
    {{- else -}}
        {{ $output | toYaml }}
    {{- end -}}
{{- end -}}

{{- define "overlay" -}}
    {{- /* convert everlay yaml values to strings */ -}}

    {{- with (include "_overlay" . | fromYaml) -}}
        {{- $output := deepCopy . -}}
        {{- $env := $output.env_configmap }}
        {{- $secret := $output.env_secret }}

        {{- /* convert yaml env vars to strings */ -}}
        {{- $vars := list
            "HIDEBOUND_WORKFLOW"
            "HIDEBOUND_SPECIFICATION_FILES"
            "HIDEBOUND_DASK_GATEWAY_CLUSTER_OPTIONS"
            "HIDEBOUND_EXPORTERS"
            "HIDEBOUND_WEBHOOKS"
        -}}
        {{- range $key := $vars -}}
            {{- $val := (get $env $key) | toYaml -}}
            {{- $env := set $env $key $val -}}
        {{- end -}}

        {{- /* set env values to string */ -}}
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

        {{- /* convert secret yaml env vars to strings and encrypt */ -}}
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
{{- end -}}