---
type: Policy
title: Security incident policy
description: Severity, notification deadlines and roles for security incidents
status: stable
tags:
- security
- incidents
- notification
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/policies/security-incident-policy
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Security incident policy

Applies to confirmed or suspected unauthorized access to customer data. Severity names follow [severity levels](../glossary/severity-levels.md); general terms are in [terms](../glossary/terms.md).

## Severity levels
A suspected exposure of customer data is Severity 1 until ruled out.

## Notification deadlines
Executive team: within 4 hours of suspicion. Affected customers: within 72 hours of confirmation. Regulators: as required by the law of the customer's country. The deadlines run from the moment of confirmation, not from the end of the investigation.

## Roles
An Incident Commander directs the response and a Communications Lead writes every external message. The practical steps are in [incident response](../processes/incident-response.md); who is called next is in [escalation rules](escalation-rules.md).
