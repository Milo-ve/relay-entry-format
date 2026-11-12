---
type: Policy
title: Escalation rules
description: When and how support escalates a case
status: stable
tags:
- support
- escalation
generated: &id001
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/escalation-rules
verified: *id001
stale_after: '2099-01-01T00:00:00Z'
---
# Escalation rules

Used with [support triage](../processes/support-triage.md) and [the SLA](support-sla.md). Terms: [terms](../glossary/terms.md).

## Tier changes
Tier 1 hands a Severity 1 case to Tier 2 if it is unresolved after 30 minutes. Tier 2 hands it to Engineering on call after 60 minutes.

## Executive escalation
The executive on call is paged when a Severity 1 case exceeds 2 hours or when customer data may have been exposed. Data exposure also starts the [security incident policy](security-incident-policy.md).
