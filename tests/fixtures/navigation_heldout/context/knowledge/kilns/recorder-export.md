---
type: Procedure
status: stable
tags:
- csv
- logger
- export
- batch
sources:
- resource: synthetic://morrowglass/kilns/recorder-export
description: Extracting a chamber observation series.
title: Recorder CSV export
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
# Recorder CSV export

## Column layout
A recorder export contains elapsed tick, display reading, independent reading and program marker. Export as UTF-8 CSV with a header row. Preserve an unchanged copy of the raw export with the run journal.

## Missing samples
Represent a missing tick by an empty numeric cell and an explicit gap marker, not by interpolation. A trend file cannot establish raw-material ancestry or crate lineage; use the [trace map](../records/trace-map.md).

[Fieldbook hub](../studio/fieldbook.md).
