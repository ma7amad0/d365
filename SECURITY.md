# Security model

## Core boundary

> The backend application may have broader access than the current employee; therefore all employee-level authorization must be enforced by the portal backend.

The browser will authenticate to the portal using single-tenant Microsoft Entra SSO. The backend separately authenticates to D365 with an application identity. The browser must never receive the D365 credential or access token. No employee-data API will be added until validated Entra identity, verified local mapping, object-level authorization, explicit D365 filtering, and allow-listed response DTOs are in place.

## Current milestone

This repository currently exposes health endpoints and a static UI only. It includes the D365 integration foundation for administrators/operators, but no HTTP route exposes metadata or D365 responses. The CLI tools run inside the trusted backend environment.

Tokens are cached only in backend process memory, refreshed five minutes early, never logged, and invalidated once after a D365 401. Secrets use Pydantic secret types and are not included in validation output. Logs are structured and include request correlation IDs without authorization headers or employee payloads.

## Threat model

| Threat | Required mitigation |
|---|---|
| Employee requests another personnel number | `/me` APIs derive identity exclusively from validated `oid`; never accept a personnel number. Verified mapping and object filters are mandatory. |
| Compromised browser modifies an API request | Server-side authorization on every object; restrictive CSP; explicit DTOs; ignore client identity assertions. |
| Stolen Entra token | Validate signature, single-tenant issuer, tenant, audience, expiry, not-before and version; short token lifetime; TLS; conditional access. Phase 2 gate. |
| Stolen D365 client secret | Secret store, least-privilege D365 role, rotation and monitoring; migrate to certificate/workload identity where feasible. |
| Admin maps the wrong employee | Dual identifiers, duplicate rejection, verification workflow, mapping history and audit event. Phase 4 gate. Never use display name. |
| D365 returns extra sensitive fields | `$select` approved fields and map into explicit Pydantic DTOs. Never proxy raw responses. |
| Malicious OData input | Entity/field identifiers come only from validated configuration; values are escaped; no raw browser filter expressions. |
| Database compromise | Private network, least-privilege account, encryption at rest/backup, parameterized ORM access, credential rotation. |
| Redis exposure | Private network only, authentication/TLS where crossing hosts, minimal non-sensitive caching, tenant/employee/company-scoped keys. |
| Internal network attacker | HTTPS with corporate/public trust, no direct backend ports, host validation, firewall segmentation, SIEM monitoring. |
| SSRF or unsafe redirect | Fixed validated D365 base URL, no user-controlled upstream URL, HTTP redirect following disabled. |
| D365 outage or throttling | Bounded idempotent retries, capped `Retry-After`, timeouts, sanitized failures, and no infinite retry. |

## Authentication and CSRF direction

Phase 2 should use the authorization-code flow with PKCE and a backend-for-frontend session: encrypted/signed opaque session cookie (`HttpOnly`, `Secure`, `SameSite=Lax`) plus CSRF tokens for state-changing requests. This keeps OAuth tokens out of browser storage. Login state and nonce must be one-time, time-bounded, and bound to the initiating session. Logout must clear the local session and use a validated post-logout URL.

Bearer-token APIs are not implemented in this milestone. If architecture constraints later require them, tokens must remain in memory (not `localStorage`) and the CSP/XSS posture must be re-reviewed.

## Authorization and sensitive data

Future access sequence:

```text
validated Entra token -> stable oid -> verified mapping -> authorized worker scope
-> configured D365 query for that worker -> explicit sanitized DTO -> audit event
```

Entra app roles are preferred. Frontend roles control presentation only and never grant authority. Managers require a backend-verified D365 or approved cached hierarchy. Portal administrators manage mappings; auditors receive read-only audit access. Denials and mapping conflicts must be audited.

## Secrets and deployment

- Never commit `.env`, credentials, tokens, authorization headers, or production employee data.
- Prefer Azure Key Vault, Docker secrets, or orchestrator-injected environment variables.
- Use a dedicated non-administrator D365 service user and a purpose-built least-privilege security role.
- Keep PostgreSQL, Redis, and FastAPI un-published; expose only Nginx.
- Require HTTPS in production. Enable HSTS only on a proven TLS virtual host.
- Disable or restrict OpenAPI in production.
- Forward access, application, D365 failure, identity, authorization, and administrative audit logs to the SIEM with retention controls.

## Reporting

Report suspected vulnerabilities through the organization's internal security incident process. Do not include real tokens, secrets, or employee records in tickets. Include the request/correlation ID, timestamp, affected route, and a sanitized reproduction.

