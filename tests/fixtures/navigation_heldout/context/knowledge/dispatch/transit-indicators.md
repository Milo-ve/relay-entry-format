---
type: Reference
status: stable
tags:
- humidity
- receiving
- dotted-red-square
sources:
- resource: synthetic://morrowglass/dispatch/transit-indicators
description: Packaging symbols observed when a crate arrives.
title: Transit indicator legend
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
# Transit indicator legend

## Dotted red square
A dotted red square on the transit indicator records a humidity exposure event in transit. Receiving photographs the indicator with the crate identifier, keeps the crate in the receiving hold area, and requests a packaging assessment before unpacking. The symbol says nothing by itself about the ceramic run's firing grade. It is not a solid red bench isolation tag.

## Hollow amber circle
A hollow amber circle means the indicator's transport latch has not been set. Receiving records an unset indicator rather than claiming that no transport exposure occurred.

[Fieldbook hub](../studio/fieldbook.md).
