---
type: Process
title: Support triage
description: How a support ticket is classified and routed
status: stable
tags:
- support
- triage
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/support-triage
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Support triage

Terms: [terms](../glossary/terms.md). Response targets: [support SLA](../policies/support-sla.md). Escalation: [escalation rules](../policies/escalation-rules.md).

## Intake
Every ticket gets a plan and a workspace name before anything else.

## Priority
Map the report to a severity using [severity levels](../glossary/severity-levels.md). When unsure, choose the higher one and correct it later.

## Routing
Login and identity problems go to the integrations queue ([SSO setup](../products/sso-setup.md)); billing to Finance; everything else to Tier 1.
