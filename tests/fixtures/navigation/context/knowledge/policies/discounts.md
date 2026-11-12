---
type: Policy
title: Discount policy
description: Annual, nonprofit and negotiated discounts and who approves them
status: stable
tags:
- discounts
- pricing
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/discounts
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Discount policy

Prices are in [current pricing](../products/pricing-current.md); plans in [plan tiers](../products/plan-tiers.md); terms in [terms](../glossary/terms.md).

## Annual discount
Paying annually costs ten months instead of twelve (two months free). It applies automatically at checkout and cannot be combined with a negotiated discount. The decision behind it is [ADR-001](../decisions/adr-001-annual-billing.md); refunds on annual plans are in the [refund policy](refund-policy.md).

## Nonprofit
Registered nonprofit organizations receive 30 percent off Starter and Team. The customer must provide proof of registered status. Sales Operations approves nonprofit discounts up to 30 percent; Enterprise nonprofit pricing is negotiated separately.

## Approval limits
Up to 10 percent: account executive. Up to 30 percent: Sales Operations. Above 30 percent: VP Sales. Every approval is recorded on the account.
