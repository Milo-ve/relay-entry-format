---
type: Procedure
status: stable
tags:
- isolate
- hold
- defect
- release
sources:
- resource: synthetic://morrowglass/bench/quarantine
description: Bench disposition of runs awaiting assessment.
title: Defective run isolation
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
# Defective run isolation

## Red tag and release
To hold a cooled production run with an unexplained defect, attach a solid red isolation tag to its rack, move the entire identified run to the marked isolation bay, and enter its run identifier and observed defect on the hold ledger. Mark the dispatch board BLOCKED against that run. Only the bench assessor may record release, and only after the assessment ticket names the disposition and the affected run. Removing the physical tag alone does not release anything.

## Partial dispositions
If an assessor separates sublots, retain the original run link and record each sublot's disposition. A transport indicator is a packaging observation, not this solid red bench tag.

[Fieldbook hub](../studio/fieldbook.md).
