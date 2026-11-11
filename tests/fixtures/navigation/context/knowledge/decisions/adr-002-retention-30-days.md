---
type: Decision
title: 'ADR-002: retention 30 days'
description: Why retention after closure was cut from 90 to 30 days
status: stable
tags:
- decision
- retention
- privacy
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/decisions/adr-002-retention-30-days
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# ADR-002: retention 30 days

## Context
Keeping customer data 90 days after closure raised storage cost and privacy risk, and few customers returned after day 30. See [terms](../glossary/terms.md).

## Decision
Delete content 30 days after account closure. Backups expire after 35 days.

## Consequences
The rule is in the [data retention policy](../policies/data-retention.md). The public [privacy notice](../policies/privacy-notice.md) still needs updating.
