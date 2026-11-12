---
type: Procedure
status: stable
tags:
- labels
- split
- lot
- identifiers
sources:
- resource: synthetic://morrowglass/dispatch/labels
description: Identity fields printed on a loaded crate.
title: Outgoing crate labels
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
# Outgoing crate labels

## Standard placement
Place the contents label inside the lid pocket and on the outside short face. The permanent shell mark remains visible. A shipment label is not a replacement for a product run identifier.

## Split crate labels
When a fired lot is divided between two crates, print the parent fired-lot identifier, the assigned child sublot identifier and the crate contents sequence on both label copies for each crate. Never reuse a child sublot identifier on the other crate. Labels carry the child and parent identities; raw-body ancestry remains in the trace map rather than being guessed from the crate colour.

## Damaged label
Reprint against the recorded contents entry and retain the illegible label with the correction card. Do not regenerate lineage from memory.

[Fieldbook hub](../studio/fieldbook.md).
