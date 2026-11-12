---
type: Procedure
status: stable
tags:
- probe
- acceptance
- calibration
sources:
- resource: synthetic://morrowglass/kilns/calibration
description: Checks and reference-card records for chamber indicators.
title: Kiln observation calibration
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
# Kiln observation calibration

## Routine comparison
At the start of the designated comparison shift, record the display and the reference-card reading beside the chamber identifier. This routine comparison is separate from a check after replacement.

## Post change check
After a thermocouple exchange, run an empty synthetic comparison cycle with reference card K2. Both indicated endpoints must be within 3 synthetic degrees of the card's two marked reference points. Record both pairs, the new probe serial and the comparison ticket. The equipment checker records PASS only if both pairs meet the limit; otherwise retain the awaiting-check tag and investigate. Resume production only after that recorded pass.

## Reference card custody
Keep the original reference card in the instrument drawer. A photocopy can identify the card but cannot replace it for a comparison entry.

[Fieldbook hub](../studio/fieldbook.md).
