---
type: Glossary
status: stable
tags:
- hold
- run
- release
- defect
- dispatch
sources:
- resource: synthetic://morrowglass/kilns/dwell-time
description: Meaning of a hold inside a firing program.
title: Thermal hold intervals
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
# Thermal hold intervals

A thermal hold, also called a dwell, is a programmed plateau in a firing curve. Its duration is entered as a synthetic minute count on the program card.

## Hold a run
The phrase on this sheet means keeping a programmed temperature level. It does not mean isolating a defective cooled run and gives no release authority. Physical isolation is governed by the [bench quarantine sheet](../bench/quarantine.md).

## Display notation
The Amber recorder abbreviates a dwell as H followed by the planned count. An observed plateau is recorded separately from the planned count.

[Fieldbook hub](../studio/fieldbook.md).
