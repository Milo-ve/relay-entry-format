---
type: Process
title: Account offboarding
description: Closing a customer account safely
status: stable
tags:
- offboarding
- deletion
- export
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/account-offboarding
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Account offboarding

When a customer leaves. Terms such as "account closure": [terms](../glossary/terms.md).

## Export
Offer a full export 14 days before closure, using [data export](../products/data-export.md). Confirm the customer has the files before closing.

## Deletion
Closing the account starts the retention clock described in [data retention](../policies/data-retention.md): content is deleted 30 days after closure. Tell the customer the exact date in writing. An earlier deletion needs a written request.

## Final invoice
Issue a final prorated invoice and any credit note through [invoicing](invoicing.md). Outstanding balances do not delay deletion.
