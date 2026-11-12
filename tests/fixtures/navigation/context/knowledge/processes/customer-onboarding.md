---
type: Process
title: Customer onboarding
description: The first two weeks with a new customer
status: stable
tags:
- onboarding
- customers
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/customer-onboarding
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Customer onboarding

A new customer is considered onboarded after day 14. What the customer can use depends on the plan ([plan tiers](../products/plan-tiers.md)). Terms: [terms](../glossary/terms.md).

## Kickoff
Day 1 to 2: a 30 minute call to confirm goals, seats and plan.

## Data import
Week 1: import existing data and confirm that counts match. Large imports are split by [usage limits](../products/usage-limits.md).

## Training
Week 2: one training session for administrators. Enterprise customers also set up single sign-on ([SSO setup](../products/sso-setup.md)).

## Two-week check
Day 14: confirm that the customer reached the first goal they named. Record the result on the account.
