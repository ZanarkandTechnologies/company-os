---
title: Hermes SME landing specification
status: approved
quality_target: standard
owner: HermesCorp
updated_at: 2026-08-17
---

# Hermes SME landing specification

## Offer

Hermes gives SME operators an accountable company layer where apps stay
editable, facts stay queryable, decisions stay attributable, and approved
procedures become reusable skills—without relying on agent memory.

**Audience:** owners, operators, and transformation leads at SMEs.

**Promised change:** replace scattered agent context with durable systems and
clear responsibility while keeping the applications people already use.

## Quality target

`standard` by explicit operator direction: very minimal, dark, typographic,
square, and low-motion. Static HTML/CSS is the intended design, not a downgrade.
No imagery or generated asset is required; the system model and typography are
the visual carriers.

## Reference synthesis

| Source | Trait | Decision | Local constraint |
| --- | --- | --- | --- |
| Aino services | Sparse editorial grid, wide whitespace, modest grotesk headline, mono-like navigation, square structure | Adapt | Preserve cadence and typography hierarchy without copying its custom font, code, or portfolio imagery |
| Banksman | Near-black/bone palette, signal green, soft orange, Inter + DM Mono | Adopt | Use `#C8FF57` and `#D36A32` sparingly as semantic signals, not decorative fields |
| Existing Hermes dashboard | Honest states and operator evidence | Adapt | Carry the accountable language forward; do not carry over the dense dashboard shell |
| Generic AI SaaS pages | Gradient heroes, glowing orbs, card grids, fake metrics | Reject | No gradients, glass, icon-card grid, fictional proof, or agent-memory claims |

## Story flow

```text
[Compact nav]
      ↓
[Hero: the business lives in its systems; agents come and go]
      ↓
[Three durable systems: apps / wiki / decisions]
      ↓
[Interactive change router: app / fact / decision / procedure]
      ↓
[Procedure compiler: approved procedure -> versioned skill + eval]
      ↓
[Decision record example: approved by + responsible + supersession]
      ↓
[No agent memory principle]
      ↓
[Final action: map the first operating lane]
```

## Section matrix

| Section | Job | Claim | Layout / carrier | Motion | Proof / content | Fallback / QA |
| --- | --- | --- | --- | --- | --- | --- |
| Hero | Orient | Durable systems outlive agents | Sparse editorial type with bottom metadata rail | Small reveal only | One clear thesis and three system guarantees | Full meaning without JS; headline fits 320px |
| Systems | Explain owners | Apps, wiki, and decisions have separate responsibilities | Three square columns with explicit owns/does-not-own rows | Hover/focus border only | Named owner, update path, agent access | Columns stack without losing order |
| Router | Make model operable | Every change has one destination | Accessible four-tab router and result panel | 150ms state change | Destination, record, next compilation step | Default fact route rendered in HTML |
| Skills | Clarify dreaming | Procedures compile; facts do not | Horizontal four-step rule | Reduced-motion-safe progress accent | Decision ref, skill version, eval contract | Text sequence remains clear without animation |
| Decisions | Show accountability | Approval and responsibility stay auditable | One full-width decision record | None | Approver, owner, dates, rationale, supersession | Semantic definition list |
| Principle | Differentiate | Hermes has no private durable agent memory | Large type and four rules | None | Replaceable runtime + durable systems | Contrast and line length checks |
| Final action | Convert | Start with one accountable operating lane | Orange rule and restrained link | Underline state | Concrete first step | No fake form or urgency |

## Asset and motion plan

- **Asset Advisor route:** skipped. The operator requested a typography-first,
  minimal surface and supplied the complete visual direction. No reference
  image is reproduced on the page.
- **Fonts:** use open Inter and DM Mono with system fallbacks. Do not copy Aino's
  proprietary `abcplus` font files.
- **Motion:** CSS opacity/translate reveal plus active router underline;
  disabled under `prefers-reduced-motion`.

## Proof plan

- Desktop screenshot at 1440×1000 and mobile screenshot at 390×844.
- No page, console, or failed same-origin asset errors.
- Keyboard selection across the four router tabs.
- No horizontal overflow at 320px, 390px, and 1440px.
- Visible focus, skip link, semantic headings, and reduced-motion rules.
- Structural tests for required systems, routes, tokens, and shared imports.
