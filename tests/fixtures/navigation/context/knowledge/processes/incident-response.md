---
type: Process
title: Incident response
description: Practical steps during an incident
status: stable
tags:
- incidents
- operations
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/incident-response
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Incident response

The rules are in the [security incident policy](../policies/security-incident-policy.md) and [escalation rules](../policies/escalation-rules.md); severity names in [severity levels](../glossary/severity-levels.md). Terms: [terms](../glossary/terms.md).

## Detect
Alerts or a customer report open an incident. The first responder names an Incident Commander.

## Triage
Set the severity, find the affected customers and decide whether data may be exposed.

## Communicate
Post to the status page within 1 hour of confirming a Severity 1. Send the customer message written by the Communications Lead. For suspected data exposure, follow the notification deadlines in the policy. Do not promise a cause before it is confirmed.

## Postmortem
Within 5 business days, write what happened, what was affected and what changes. Blame is out of scope.
