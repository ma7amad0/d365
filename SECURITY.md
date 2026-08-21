# Security model

## Core boundary

> The backend application may have broader access than the current employee; therefore all employee-level authorization must be enforced by the portal backend.

The browser will authenticate to the portal using single-tenant Microsoft Entra SSO. The backend separately authenticates to D365 with an application identity. The browser must never receive the D365 credential or access token. No employee-data API will be added until validated Entra identity, verified local mapping, object-level authorization, explicit D365 filtering, and allow-listed response DTOs are in place.

## Current milestone

The portal now uses MSAL authorization-code flow with PKCE and validates portal API access tokens on the backend. Tokens use memory-only browser caching and are sent only in the `Authorization` header to same-origin APIs. `/me` returns allow-listed DTOs only after a verified mapping; no HTTP route exposes metadata or raw D365 responses.

Tokens are cached only in backend process memory, refreshed five minutes early, never logged, and invalidated once after a D365 401. Secrets use Pydantic secret types and are not included in validation output. Logs are structured and include request correlation IDs without authorization headers or employee payloads.

## Threat model

| Threat | Required mitigation |
|---|---|
| Employee requests another personnel number | `/me` APIs derive identity exclusively from validated `oid`; never accept a personnel number. Verified mapping and object filters are mandatory. |
| Compromised browser modifies an API request | Server-side authorization on every object; restrictive CSP; explicit DTOs; ignore client identity assertions. |
| Stolen Entra token | Validate signature, single-tenant issuer, tenant, audience, expiry, not-before, issued-at, version, calling client and scope; short lifetime; TLS; conditional access. |
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

The implemented model is a single-tenant SPA authorization-code flow with PKCE and bearer access tokens held only in memory, never `localStorage` or cookies. Because authentication uses the `Authorization` header rather than ambient cookies, conventional CSRF does not apply. XSS remains the primary browser-token threat, mitigated through React escaping, no injected HTML, strict CSP, exact redirect URIs, dependency review, and explicit DTOs. A future switch to cookie authentication requires `HttpOnly`, `Secure`, `SameSite` cookies plus CSRF tokens.

## Authorization and sensitive data

Implemented profile access sequence:

```text
validated Entra token -> exact D365 UPN lookup -> immutable oid equality -> verified mapping -> authorized worker scope
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
