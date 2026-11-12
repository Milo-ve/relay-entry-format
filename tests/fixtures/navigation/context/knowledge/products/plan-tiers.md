---
type: Reference
title: Plan tiers
description: Starter, Team and Enterprise compared
status: stable
tags:
- plans
- pricing
- tiers
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/plan-tiers
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Plan tiers

Fernwood Metrics sells three plans. Prices are in [current pricing](pricing-current.md); limits in [usage limits](usage-limits.md); discounts in [discounts](../policies/discounts.md). Terms: [terms](../glossary/terms.md). Customer types: [customer segments](../glossary/customer-segments.md).

## Starter
For individuals and very small groups. Up to 3 seats, 1 GB exports, community support. No single sign-on.

## Team
For small companies. Up to 25 seats, scheduled data exports, integrations ([integrations](integrations.md)), faster support ([support SLA](../policies/support-sla.md)). No single sign-on.

## Enterprise
For large organizations. Unlimited seats, single sign-on and SCIM ([SSO setup](sso-setup.md)), audit logs ([audit logs](audit-logs.md)), the fastest support targets and negotiated terms. Single sign-on is Enterprise only; see [ADR-003](../decisions/adr-003-sso-enterprise-only.md).

## Comparison
| | Starter | Team | Enterprise |
|---|---|---|---|
| Seats | 3 | 25 | Unlimited |
| Scheduled exports | No | Yes | Yes |
| Single sign-on | No | No | Yes |
| Audit logs | No | No | Yes |
| Support | Community | Standard | Priority |
