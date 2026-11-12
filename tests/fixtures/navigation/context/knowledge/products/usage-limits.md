---
type: Reference
title: Usage limits
description: API, storage and seat limits per plan
status: stable
tags:
- limits
- api
- seats
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/usage-limits
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Usage limits

Limits by plan ([plan tiers](plan-tiers.md)). Exceeding them is covered by the [acceptable use policy](../policies/acceptable-use.md). Terms: [terms](../glossary/terms.md).

## API limits
Requests per minute: Starter 60, Team 600, Enterprise 6,000 (negotiable). Limits are per API key. How the API reports excess is in [API overview](api-overview.md).

## Storage
Starter 5 GB, Team 100 GB, Enterprise negotiated.

## Seats
Starter 3 seats, Team 25 seats, Enterprise unlimited. An active seat is defined in [terms](../glossary/terms.md).
