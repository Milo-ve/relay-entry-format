---
type: Schema
status: stable
tags:
- traceability
- lineage
- pots
- split
sources:
- resource: synthetic://morrowglass/records/trace-map
description: Recorded identities across preparation, firing and division.
title: Material and fired lot trace map
generated:
  by: process:heldout-fixture
  at: '2026-01-07T10:00:00Z'
stale_after: '2199-01-01T00:00:00Z'
verified:
  by: process:synthetic-fixture-check
  at: '2026-01-08T10:00:00Z'
  note: Synthetic machine-confirmed signal for evaluation only; not human review or
    observed operational validation.
---
# Material and fired lot trace map

## Pot identities
Each glaze pot record maps its pot identifier to family code, preparation ticket and originating container identifier. A remnant keeps the same pot identity; mark its new remnant location in that record without assigning a fresh preparation identity. Preserve the original mapping even when a pot is discarded. Physical storage and disposal are governed by the remnant sheet.

## Split lots
A fired-lot record points to its run identifier and raw-body batch identifier. When splitting a lot, create one child sublot record per outgoing crate, each pointing to the unchanged parent fired lot, and record the quantity in that child. The parent link preserves the route to the raw-body batch. Do not manufacture a new raw-body identifier for a split fired lot. The label sheet defines which of these identifiers to print.

## Corrected ancestry
If a source identifier was transcribed incorrectly, retain the original mapping and add a correction referencing the preparation ticket. An unknown parent stays unknown until supported by a recorded source; similar shade is not ancestry.

[Fieldbook hub](../studio/fieldbook.md).
