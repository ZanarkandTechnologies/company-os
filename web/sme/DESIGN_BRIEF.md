---
title: Hermes SME visual system
status: approved
owner: HermesCorp
updated_at: 2026-08-17
---

# Hermes SME visual system

## Functional basis

- **User:** an SME owner or operator evaluating how Hermes fits their company.
- **Primary job:** understand where apps, facts, decisions, and procedures live.
- **Key states:** normal page, selected route, keyboard focus, narrow viewport,
  JavaScript unavailable, and reduced motion.

## Register

**Brand/product hybrid.** A public brand page explaining a concrete operating
model rather than a cinematic campaign or repeated-use dashboard.

**Scene sentence:** An owner reviews a serious operating blueprint after hours;
the page feels calm, exact, and accountable rather than futuristic.

## Taste dials

- **Visual density: 4/10** — sparse enough for the system model to breathe.
- **Design variance: 5/10** — stable grid with a few asymmetric editorial offsets.
- **Motion intensity: 2/10** — only focus, reveal, and route-state transitions.
- **Color commitment: 4/10** — bone/black foundation with two semantic accents.
- **Materiality: 1/10** — flat surfaces, one-pixel rules, no shadows or glass.

## Visual system

- **Typography:** Inter for display/body; DM Mono for navigation, IDs, and
  metadata. Headlines are firm grotesk, moderately sized, tightly tracked, and
  sentence case.
- **Color:** black `#090A08`; graphite `#10120F`; bone `#EDE9DF`; muted
  `#A09E94`; signal green `#C8FF57`; soft orange `#D36A32`.
- **Spacing:** 8px base; 16/24/40/64/96 section rhythm; wide desktop gutters.
- **Radius/elevation:** zero radius; no shadows. Structure comes from lines.
- **Components:** square buttons, tab rail, bordered data rows, full-width
  system columns, compact mono labels, and thin semantic accents.
- **Icon/media:** no illustrative icons or imagery. Numbers, arrows, and rules
  carry navigation and sequence.
- **Motion:** transform/opacity only, 120–220ms, with complete reduced-motion
  fallback.

## Reusable tokens and components

`web/shared/hermes-brandkit.css` owns colors, typography, spacing, focus,
buttons, labels, rules, data rows, and page-width primitives. Page-specific
composition stays in `web/sme/site.css`.

## Anti-slop constraints

- No purple/blue gradients, glow, glass, grain overlay, fake terminal, or orb.
- No repeated icon-card grid or nested container soup.
- No huge metric numbers, fake logos, testimonials, or performance claims.
- No anthropomorphic “agent brain” or memory metaphor.
- Do not use green and orange together unless they encode different states.
- Never hide approval, responsibility, provenance, or source ownership in a
  tooltip.
