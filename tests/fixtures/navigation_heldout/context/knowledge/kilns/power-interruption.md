---
type: Procedure
status: stable
tags:
- power
- interrupted
- ramp
sources:
- resource: synthetic://morrowglass/kilns/power-interruption
description: Disposition of a run interrupted during a ramp.
title: Interrupted firing record
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
# Interrupted firing record

## Record and isolate
Record the interruption in the run journal, mark the entire load interrupted, and keep it out of normal production release. Do not automatically resume a stored ramp or infer a pass from the controller returning to its start screen. Refer the tagged run to the process assessor for a documented disposition. The journal's [interruption fields](../records/run-journal.md#interruption-fields) specify the required observations.

## Empty chamber outage
An outage with an empty chamber is an equipment availability entry rather than a product disposition. Keep it in the equipment log without fabricating a product run.

[Fieldbook hub](../studio/fieldbook.md).
