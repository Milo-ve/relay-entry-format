---
type: Decision
title: 'ADR-001: annual billing'
description: Why annual billing gets two free months
status: stable
tags:
- decision
- billing
- pricing
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/decisions/adr-001-annual-billing
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# ADR-001: annual billing

## Context
Monthly churn was high and invoices were costly to process. See [terms](../glossary/terms.md).

## Decision
Offer annual billing at ten months for twelve. Described in [discounts](../policies/discounts.md) and priced in [current pricing](../products/pricing-current.md).

## Consequences
Refunds on annual plans need a clear rule, now in the [refund policy](../policies/refund-policy.md). Finance approves every annual refund ([refund handling](../processes/refund-handling.md)).
