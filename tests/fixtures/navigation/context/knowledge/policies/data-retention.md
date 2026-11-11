---
type: Policy
title: Data retention policy
description: How long customer data is kept and when it is deleted
status: stable
tags:
- retention
- privacy
- deletion
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/data-retention
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Data retention policy

Definitions of "workspace" and "account closure" are in [terms](../glossary/terms.md).

## Retention periods
Customer content is kept while the subscription is active. After account closure it is deleted 30 days later. Encrypted backups expire after 35 days. Audit logs are kept 12 months; see [audit logs](../products/audit-logs.md).

## Deletion requests
A customer may ask for earlier deletion in writing. Deletion completes within 7 days of a verified request. Backups are not edited; they expire on their own schedule.

## Backups
Backups are encrypted and stored in one region. They are used only for disaster recovery, never to answer a customer request for data; use [data export](../products/data-export.md) for that.

## Rationale
Retention was reduced from 90 to 30 days. The reasoning is in [ADR-002](../decisions/adr-002-retention-30-days.md). Vendors that process data are listed in the [subprocessor list](subprocessor-list.md).
