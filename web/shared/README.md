---
title: Hermes shared web layer
status: active
owner: HermesCorp
updated_at: 2026-08-17
---

# Hermes shared web layer

This folder owns dependency-free modules shared by Hermes public web surfaces.
It does not own page-specific composition or operational application state.

## Modules

- `hermes-brandkit.css` — color, type, spacing, focus, buttons, status, data
  rows, and width primitives.
- `site-shell.js` — progressive section-navigation state and year rendering.
- `system-router.js` — accessible company-change routing and its canonical
  destination copy.

## Use

```html
<link rel="stylesheet" href="/shared/hermes-brandkit.css">
<script type="module">
  import {setupSiteShell} from "/shared/site-shell.js";
  setupSiteShell();
</script>
```

Keep page grids and section scenes in the consuming page's stylesheet. Promote
a style here only when at least two surfaces need the same semantic behavior.

## Provenance

The visual system adapts Aino's sparse editorial structure and Banksman's
published palette/font pairing. It does not include either source's custom
font files, code, imagery, copy, or protected creative.
