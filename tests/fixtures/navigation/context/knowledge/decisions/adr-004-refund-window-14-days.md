---
type: Decision
title: 'ADR-004: refund window 14 days'
description: Why the refund window went from 30 to 14 days
status: stable
tags:
- decision
- refunds
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/decisions/adr-004-refund-window-14-days
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# ADR-004: refund window 14 days

## Context
Most refund requests came in the first week. See [terms](../glossary/terms.md).

## Decision
Shorten the monthly refund window to 14 days. Annual plans keep 30 days.

## Consequences
See the [refund policy](../policies/refund-policy.md). The 2023 text is kept as [history](../policies/refund-policy-2023.md).
