# AGI Toy Shop — Launch source cache

## Coverage

Frozen at 2026-09-10T00:00:00Z for 2026-W37. Project page, complete Work inventory with comments, and chat interval 2026-09-07T00:00:00Z through cutoff were read successfully. Pagination is exhausted. Records below are synthetic.

## Acceptance

WORK-TOY-CATALOG-A, owner PERSON-TOY-NUR-001 (display name Nur), receiver PERSON-TOY-MEI-002 (Mei). Nur produced catalog-ready-A.csv from catalog-input-A.csv. Mei's September 7 acceptance: "All 12 rows match the approved product fields; exception list attached; accepted for publication." Workflow key catalog_handoff_v1. Active time and waiting time were not recorded. Acceptance controls: complete product-data package, receiver acknowledgment, exception list. This is the same workflow and output class as the approved catalog handoff baseline.

## Conversion

WORK-TOY-CONVERT-ONE, owner PERSON-TOY-NUR-001, receiver PERSON-TOY-MEI-002. Input vendor-september.csv was mapped by SKU into vendor-review.xlsx; duplicate SKU rows were listed in exceptions.csv; Mei checked row counts and accepted the review sheet September 8. Workflow key vendor_csv_to_review_sheet_v1. This is the only observation of this conversion. No duration was recorded and no standing SOP was approved.

## Input conflict

WORK-TOY-PUBLISH-B, owner PERSON-TOY-NUR-001, receiver PERSON-TOY-MEI-002, status blocked. product-price-v3.csv sets ROBOT-01 to RM49 and TRAIN-02 to RM79; finance-price-v4.csv sets them to RM55 and RM75. No source marks either version authoritative. Reminders on September 8 and September 9 asked Nur for publication progress. Nur answered both times that the authoritative input was undecided; neither reminder changed the input or decision state. Publication remains pending.

## Decision

DECISION-TOY-PRICE-01, decision owner PERSON-TOY-AISHA-003 (Aisha), status open. Aisha's September 9 instruction: "I own the price version decision. Put the two versions and the affected SKUs together with the margin impact so I can select the source. Mei should verify the approved exception rows before publishing." Margin inputs are absent from the frozen cache. This decision affects the batch B publication gate; there is no recorded approval, selected price version, publication receipt, or new deadline.
