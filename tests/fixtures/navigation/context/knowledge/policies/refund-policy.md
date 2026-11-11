---
type: Policy
title: Refund policy
description: When a subscription can be refunded and how much
status: stable
tags:
- refunds
- billing
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/refund-policy
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Refund policy

Applies to every Fernwood Metrics subscription. Terms such as "billing cycle" are defined in [terms](../glossary/terms.md). Chargebacks raised through a bank are covered separately in the [chargeback policy](chargeback-policy.md). To carry out a refund, follow [refund handling](../processes/refund-handling.md).

## Eligibility
A customer is eligible while the subscription is active, or ended inside the refund window, and no abuse was recorded under the [acceptable use policy](acceptable-use.md). Plan names are defined in [plan tiers](../products/plan-tiers.md).

## Refund window
Monthly plans: a full refund when requested within 14 days of the first purchase or of a renewal. The window was shortened from 30 days; the reasoning is in [ADR-004](../decisions/adr-004-refund-window-14-days.md). A request on day 15 or later is declined unless an exception below applies.

## Exceptions
A full refund is due at any time for a billing error, or when the service was unavailable beyond the targets in the [support SLA](support-sla.md).

## Annual plans
A full refund within 30 days of purchase. After 30 days, a prorated credit note for unused full months, approved by Finance. The annual discount itself is described in [discounts](discounts.md) and is not refunded separately.
