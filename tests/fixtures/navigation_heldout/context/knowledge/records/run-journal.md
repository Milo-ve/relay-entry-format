---
type: Schema
status: stable
tags:
- journal
- interruption
- fields
sources:
- resource: synthetic://morrowglass/records/run-journal
description: Required record fields for routine and interrupted firings.
title: Run journal schema
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
# Run journal schema

## Routine fields
Record the run identifier, chamber identifier, body batch, program label and assigned shift. Keep planned ramp markers distinct from observations.

## Interruption fields
For a power interruption, record the run identifier, observed interruption tick, last observed chamber reading, program segment at loss, power-return tick or UNKNOWN, and the identifier of the attached interruption tag. Add an observation-source field identifying recorder or manual entry. An unavailable reading is UNKNOWN; do not reconstruct it from a planned ramp. These fields document the event and do not decide whether the load may resume or pass.

## Filing boundary
The journal links to inspection and disposition records. A complete journal means recorded fields are present; it does not mean production acceptance.

[Fieldbook hub](../studio/fieldbook.md).
