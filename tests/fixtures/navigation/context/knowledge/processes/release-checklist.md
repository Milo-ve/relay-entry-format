---
type: Process
title: Release checklist
description: Steps before shipping a release
status: stable
tags:
- engineering
- release
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/processes/release-checklist
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# Release checklist

Terms: [terms](../glossary/terms.md).

## Before
Tests pass, migrations reviewed, rollback plan written.

## During
Deploy to a canary, watch error rates for 30 minutes.

## After
Announce in the changelog. If something breaks, start [incident response](incident-response.md).
