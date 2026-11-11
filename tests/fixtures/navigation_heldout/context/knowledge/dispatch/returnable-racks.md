---
type: Register
status: stable
tags:
- racks
- pool
- return
sources:
- resource: synthetic://morrowglass/dispatch/returnable-racks
description: Rack identities and empty rack returns.
title: Returnable rack register
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
# Returnable rack register

## Ownership and return
A rack stamped M belongs to the fictional internal pool; a rack stamped E belongs to the external crate pool. Keep the stamp visible when the rack travels empty and record its return movement against that identity. This register has no external desk assignment or contact details.

## Damage observation
Record the rack identifier and a sketch of damage on its return card. The pool desk directory is maintained separately; do not infer a current contact from an old movement receipt.

[Fieldbook hub](../studio/fieldbook.md).
