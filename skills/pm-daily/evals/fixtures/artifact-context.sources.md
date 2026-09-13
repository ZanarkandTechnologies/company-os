# Synthetic AGI Toy Shop source cache

Frozen interval: 2026-09-08T09:00:00Z to 2026-09-09T09:00:00Z. All records below are fictional eval data; no provider access is needed.

## Project

<a id="project"></a>

```json
{"id":"PROJ-TOY-STOCK","title":"AGI Toy Shop — Stock Operations","url":"https://example.invalid/stock","body":"Deliver the inventory comparison by 11 September. Maya Chen owns data validation; Alex Rivera approves exports."}
```

## Meeting

<a id="meeting"></a>

```json
{"id":"MTG-190","project_id":"PROJ-TOY-STOCK","title":"Inventory kickoff","url":"https://example.invalid/kickoff","status":"Done","updated_at":"2026-09-08T12:00:00Z","body":"Maya Chen and Alex Rivera compared CSV export against live API sync. They chose CSV for Friday's inventory comparison: live sync would take three additional engineering days and risk the deadline. Accepted cost: Maya must refresh the export manually each morning. Revisit API sync after the September comparison. Maya demonstrated the repeatable normalization procedure: read stock.csv and aliases.csv, replace supplier aliases using the lookup, reject unmatched names for correction, and write normalized-stock.csv. The procedure is called normalize_stock. Alex also said to follow up with sales. Meeting outcome: CSV approach approved and the above responsibilities recorded; no software delivery was claimed."}
```

## Validation

<a id="validation"></a>

```json
{"id":"WORK-191","project_id":"PROJ-TOY-STOCK","title":"Validate normalized inventory","url":"https://example.invalid/validation","owner":{"id":"PERSON-88","name":"Maya Chen"},"status":"Done","updated_at":"2026-09-09T08:00:00Z","body":"Maya validated all 120 inventory rows against the approved August comparison. No unmatched supplier aliases remain. Result: normalized-stock.csv at https://example.invalid/normalized-stock.csv; validation log at https://example.invalid/validation-log. Alex Rivera reviewed the validation log and accepted the normalization check as complete at 08:00. This acceptance covers validation only; publishing the export still needs separate approval."}
```

## Approval

<a id="approval"></a>

```json
{"id":"WORK-192","project_id":"PROJ-TOY-STOCK","title":"Approve inventory export","url":"https://example.invalid/approval","owner":{"id":"PERSON-89","name":"Alex Rivera"},"status":"Blocked","due_date":"2026-09-10","updated_at":"2026-09-09T08:15:00Z","body":"Export remains blocked pending Alex's approval. Alex confirmed he will review at 14:00 today. Maya will publish after approval; no other blocker is known."}
```

## Empty

<a id="empty"></a>

```json
{"id":"WORK-193","project_id":"PROJ-TOY-STOCK","title":"Decision: switch database","url":"https://example.invalid/empty","owner":null,"status":"Todo","body":"","messages":[{"id":"MSG-194","project_id":"PROJ-TOY-STOCK","url":"https://example.invalid/greeting","body":"hello"}]}
```
