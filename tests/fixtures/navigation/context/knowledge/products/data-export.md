---
type: Feature
title: Data export
description: Export formats, scheduling and limits
status: stable
tags:
- export
- data
generated: &id001
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/data-export
verified: *id001
stale_after: '2099-01-01T00:00:00Z'
---
# Data export

Lets a customer take their data with them. Retention rules: [data retention](../policies/data-retention.md). Terms: [terms](../glossary/terms.md).

## Formats
CSV and JSON on every plan. Parquet on Enterprise.

## Scheduling
Scheduled exports, daily or weekly, are available on Team and Enterprise. Starter exports are manual. Plan details: [plan tiers](plan-tiers.md).

## Limits
One export job may contain up to 1 GB on Starter and 5 GB on Team and Enterprise. Larger data is split into several jobs. Used in [account offboarding](../processes/account-offboarding.md).
