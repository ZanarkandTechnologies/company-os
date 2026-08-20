---
title: Google Drive doctor workflow
status: active
owner: company-os-onboarding
kind: skill-method-reference
---

# Google Drive Doctor Workflow

Read only when Google Drive is selected for the Knowledge surface.

## Probe

1. Call the connected Drive profile/status action. Persist only success/failure,
   never an account ID or email.
2. List Shared Drives. If none exist, require explicit approval of a My Drive
   folder as company scope.
3. List at most 30 immediate children of the owner-supplied folder. Without one,
   list at most 30 root items only to diagnose boundaries; never recurse.
4. Optionally inspect at most 20 recent metadata records. Fetch no content in
   the doctor pass.
5. Preserve only sanitized counts, type mix, structural observations, and
   sharing-verification state—not unrelated titles, IDs, URLs, or content.

## Decision Rules

- `reachable`: status and one list call succeed.
- `permissioned`: proposed scope is listable and understood; broad account
  access alone earns at most 1/2.
- `structurally_consistent`: a repeatable route exists; mixed personal/company
  root earns 0/2.
- `canonically_owned`: the owner explicitly names the authoritative root.
- `reliably_searchable`: a bounded query can stay inside that root and return
  stable native references.

Do not add an unapproved root to the rendered workspace context. After approval,
run one natural company-document query and pass only when retrieval stays inside
the root and returns its native link plus observed time.
