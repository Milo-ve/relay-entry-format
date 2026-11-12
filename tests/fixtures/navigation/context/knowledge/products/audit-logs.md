---
type: Feature
title: Audit logs
description: Who did what in a workspace
status: stable
tags:
- audit
- security
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/audit-logs
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Audit logs

Enterprise only ([plan tiers](plan-tiers.md)). Terms: [terms](../glossary/terms.md).

## What is recorded
Sign-ins, permission changes, exports and deletions.

## Retention
Audit logs are kept 12 months; see [data retention](../policies/data-retention.md).
