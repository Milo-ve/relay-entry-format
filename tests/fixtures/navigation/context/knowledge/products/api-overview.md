---
type: Reference
title: API overview
description: Authentication, rate limits and versioning
status: stable
tags:
- api
- rate-limits
generated: &id001
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/api-overview
verified: *id001
stale_after: '2099-01-01T00:00:00Z'
---
# API overview

Terms: [terms](../glossary/terms.md).

## Authentication
API keys created per workspace, sent as a bearer token.

## Rate limits
Per-key limits are in [usage limits](usage-limits.md). When a limit is exceeded the API returns status 429 with a Retry-After header, and rejected requests are not billed. Repeated excess on Starter is throttled, not suspended.

## Versioning
Version 2 is current. The retirement of version 1 is discussed in [ADR-006](../decisions/adr-006-api-v1-sunset.md).
