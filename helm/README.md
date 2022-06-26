# Hidebound Helm Chart Structure

This Helm chart has been structured to incorporate the overlay logic of
kustomize.

The values.yaml file of this Helm chart is divided into three sections:
1. The context section, where the user use chooses which overlay is to be
   applied.
2. The base section, which defines the default values for the chart parameters.
3. The overlays section, where the parameter overlays are defined.

The _helpers.tpl file then patches the base section with the chosen overlay section and uses the result to fill in the parameter values of the Helm chart.

---
## Context Section
Defines which overlay to use.

For example:
```
overlay: rancher_desktop
```

---
## Base Section
The base section mirrors the file structure of this repository in the following way:

File structure:
```
helm
  |- Chart.yaml
  |- values.yaml
  |- templates
     |- [template-name].yaml (kebab-case)
```

Base structure:
```
base:
  [template_name]: (snake_case)
    [parameter]: [value]
```

Thus templated paremeters defined under a template name in the base structure are easily indexed to a template file of the same name.

### Enable Subsection
In addition to this, the base section also has a subsection called "enable". Enable has the following structure:

```
base:
  enable:
    [template_name]: [bool]
```
Enable's corresponding template files contain a conditional at the top of their definition, such that their entire contents are rendered or not depending on their enable value.

For example:
```
{{- with (include "overlay" . | fromYaml) -}}
{{ if .enable.image_pull_secret }}
...
{{ end }}
{{- end -}}
```

---
## Overlays Section
Defines groups of base parameters to be patched with new values.

Each overlay in this section will incompletly mirror the full structure of the base section.

Overlays has the following structure:
```
overlays:
  [overlay_name]:
    enable:
      [template_name]: [bool]

    [template_name]:
      [parameter]: [value]
```

For example:
```
overlays:
  example_overlay:
    enable:
      traefik_ingress: true

    traefik_ingress:
      match: HostRegexp(`hidebound.local`)
```

This example declares an overlay called "example_overlay", enables the traefik_ingress.yaml file and sets its `match` parameter to `HostRegexp('hidebound.local')`.
