---
type: Process
title: Invoicing
description: Billing cycle, failed payments and credit notes
status: stable
tags:
- billing
- invoices
- finance
generated: &id001
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/invoicing
verified: *id001
stale_after: '2099-01-01T00:00:00Z'
---
# Invoicing

Prices: [current pricing](../products/pricing-current.md). Terms such as "billing cycle": [terms](../glossary/terms.md).

## Billing cycle
Monthly plans are billed on the purchase day each month; annual plans once a year. Invoices are emailed on the billing day.

## Failed payments
A failed payment is retried after 3 and 7 days. After 14 days the workspace becomes read-only.

## Credit notes
A refund or correction is issued as a credit note linked to the original invoice, never by editing the invoice. Credit notes reduce the next charge or are paid out to the original payment method. Refund rules: [refund policy](../policies/refund-policy.md); execution: [refund handling](refund-handling.md).
