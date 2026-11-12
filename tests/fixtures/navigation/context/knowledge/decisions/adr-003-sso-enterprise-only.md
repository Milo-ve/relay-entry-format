---
type: Decision
title: 'ADR-003: SSO is Enterprise only'
description: Why single sign-on is limited to Enterprise
status: stable
tags:
- decision
- sso
- plans
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/decisions/adr-003-sso-enterprise-only
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# ADR-003: SSO is Enterprise only

## Context
Single sign-on costs support time. See [terms](../glossary/terms.md).

## Decision
Offer it on Enterprise only ([plan tiers](../products/plan-tiers.md)).

## Consequences
Guide: [SSO setup](../products/sso-setup.md). Team customers who ask are pointed to Enterprise.
