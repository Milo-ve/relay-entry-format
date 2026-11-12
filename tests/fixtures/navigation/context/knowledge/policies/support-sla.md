---
type: Policy
title: Support SLA
description: Response targets by plan and severity
status: stable
tags:
- support
- sla
generated: &id001
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/support-sla
verified: *id001
stale_after: '2099-01-01T00:00:00Z'
---
# Support SLA

Targets are first responses, not resolutions. Plans are described in [plan tiers](../products/plan-tiers.md); severity is defined in [severity levels](../glossary/severity-levels.md). See also [terms](../glossary/terms.md).

## Response targets by plan
| Severity | Starter | Team | Enterprise |
|---|---|---|---|
| Severity 1 | 8 hours | 2 hours | 30 minutes |
| Severity 2 | 2 business days | 8 business hours | 4 hours |
| Severity 3 | 3 business days | 2 business days | 1 business day |

## Hours
Severity 1 is covered around the clock on Team and Enterprise. Everything else follows business hours, Monday to Friday.

## Exclusions
Scheduled maintenance announced 5 days ahead and customer-caused outages are excluded. Phone support was dropped; see [ADR-005](../decisions/adr-005-drop-phone-support.md). Tickets are routed as described in [support triage](../processes/support-triage.md).
