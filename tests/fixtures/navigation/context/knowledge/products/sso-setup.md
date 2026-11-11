---
type: Feature
title: SSO setup
description: Enterprise SSO via SAML and SCIM
status: stable
tags:
- sso
- saml
- login
- identity-provider
- scim
generated:
  by: process:okf-icm
  at: '2026-02-10T09:00:00Z'
sources:
- resource: synthetic://fernwood/products/sso-setup
verified:
- by: human:reviewer-a
  at: '2026-02-10T09:00:00Z'
stale_after: '2099-01-01T00:00:00Z'
---
# SSO setup

Enterprise only; the reason is [ADR-003](../decisions/adr-003-sso-enterprise-only.md) and the plans are in [plan tiers](plan-tiers.md). Terms: [terms](../glossary/terms.md). Onboarding context: [customer onboarding](../processes/customer-onboarding.md).

## SAML
Create a SAML application in the customer's IdP, paste our ACS URL and entity ID, and upload the IdP metadata. Test with one user before enforcing SSO for the workspace.

## SCIM
Provision and deprovision users from the IdP with a SCIM token generated in workspace settings.

## Troubleshooting
Login loops are usually clock skew over 5 minutes or a wrong ACS URL. Check that the user is assigned to the application in the IdP, that the email claim matches the workspace email, and that the IdP certificate has not expired. If the IdP shows success but the workspace rejects the assertion, escalate with the assertion ID using [support triage](../processes/support-triage.md).
