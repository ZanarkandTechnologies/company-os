---
template_id: authored-filesystem-evals
template_version: "0.1.0"
kind: company-os-eval-template
status: active
owner: HermesCorp
---

# Authored filesystem evals

This company-agnostic starter turns a manager workflow into an executable file
contract. Copy the whole directory into a dedicated company project; do not put
company cases, profiles, workspaces, or generated runs in HermesCorp.

```text
owner message + disposable profile + starting files
  -> isolated Hermes workspace
  -> created / modified / deleted file events
  -> added / removed / present / absent content checks
  -> saved run receipt
```

## Start

```bash
npm test
npm run ui
```

Open the printed local URL. **Save JSON** writes the durable case under
`cases/`. **Prepare isolated session** creates an ignored run workspace without
invoking Hermes. **Run in Hermes** requires an explicit profile and then permits
only the `file,skills` toolsets:

```bash
HERMES_EVAL_PROFILE=your-company-profile npm run ui
```

The case schema is intentionally small:

```json
{
  "id": "example-report",
  "owner_message": "Prepare the report.",
  "fixture_files": [{ "path": "sources/input.md", "content": "Evidence" }],
  "file_assertions": [{
    "path": "reports/output.md",
    "event": "created",
    "content": {
      "added": ["Evidence"],
      "removed": [],
      "present": ["Review"],
      "absent": ["published"]
    }
  }]
}
```

`modified` and `deleted` assertions require the same path in `fixture_files`.
Paths may never escape the disposable workspace, and symlinked fixture content
is rejected. The evaluator uses SHA-256 changes for modification checks and
literal text relations for content checks.

This proves isolated agent behavior. Live Notion, Drive, email, messaging, and
scheduler connections need separate bounded integration smoke tests.
