# SSSA Employee Portal

Production-oriented foundation for an on-premises employee portal backed by Microsoft Dynamics 365 Finance & Operations. D365 profile access is driven only by metadata-confirmed database configuration and verified identity mappings.

## Milestone status

Implemented:

- FastAPI application with structured JSON logs, request IDs, host/CORS enforcement, and security headers
- asynchronous PostgreSQL and Redis readiness checks
- `/health`, `/health/live`, and `/health/ready`
- MSAL client-credential token service with locking, cache reuse, early refresh, and sanitized errors
- asynchronous D365 OData client with bounded retry behavior for network errors, 429, 5xx, and one legitimate 401 refresh
- safe OData identifier validation, value escaping, and bounded pagination
- defused XML `$metadata` parser and entity/property search
- D365 connectivity and metadata CLI tools
- tenant-scoped Entra v2 access-token validation using cached OIDC/JWKS signing keys
- MSAL authorization-code/PKCE sign-in with memory-only browser token caching
- verified identity mapping, audit, local-role, setting, and D365 configuration schema
- protected `/api/v1/me`, `/api/v1/me/profile`, and `/api/v1/me/leave-balances` with explicit DTOs
- fail-closed identity auto-provisioning that verifies the D365 object ID against the signed token
- React/TypeScript/Vite responsive shell with English/Arabic direction support
- Docker Compose topology in which only Nginx publishes a host port
- automated backend tests

Deferred by design: mapping administration screens, manager/team APIs, leave-request APIs, approvals, and write operations. Automatic mapping uses exact UPN lookup only as a locator and refuses to provision unless D365 returns the same immutable object ID as the signed Entra token.

## Architecture

```text
Employee browser
      |
   HTTPS 443
      |
    Nginx ---------- React static UI
      |
    FastAPI -------- Redis (cache)
      |  \
      |   +--------- PostgreSQL
      |
  MSAL app identity
      |
Dynamics 365 F&O OData ($metadata first)
```

The `private` Docker network contains PostgreSQL and Redis. The backend additionally joins an un-published `egress` network so it can reach Microsoft identity and D365. No backend/database/cache ports are published.

## Project layout

```text
backend/app/core       configuration, logging, middleware
backend/app/database   async SQLAlchemy lifecycle and Alembic base
backend/app/d365       token service, OData client, queries, metadata
backend/app/health     liveness and readiness
backend/app/tools      operational CLI utilities
backend/tests          isolated automated tests
frontend/src           responsive bilingual-ready application shell
nginx                  edge reverse proxy and TLS example
```

## Local setup

Prerequisites: Docker Engine with Compose v2. A local Python 3.12 environment is optional.

1. Copy `.env.example` to `.env`.
2. Replace every placeholder and generate a random `SESSION_SECRET` of at least 32 characters.
3. For a foundation-only local launch, placeholder Entra IDs are accepted while `APP_ENV=development`; D365 CLI calls require real credentials.
4. Start the stack:

```bash
docker compose up --build
```

Open `http://localhost`. Check `http://localhost/health/ready`. Development OpenAPI is at `http://localhost/docs`. Set `API_DOCS_ENABLED=false` in production until admin/network restriction is implemented.

Run tests in an isolated image:

```bash
docker build --target test -t sssa-portal-test -f backend/Dockerfile backend
docker run --rm sssa-portal-test
```

For a normal host development environment:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload
```

Run the frontend separately with `npm install` and `npm run dev` from `frontend/`.

## Environment variables

The complete template is in `.env.example`. Important groups:

- Portal identity: tenant, SPA client ID, exact API audience, allowed clients, and delegated scope
- D365 app identity: `D365_CLIENT_ID`, `D365_CLIENT_SECRET`
- D365 endpoints: fixed by default to `https://sssa.operations.dynamics.com` and `/data`
- metadata safety: `D365_METADATA_MAX_BYTES` defaults to 256 MiB and is capped at 512 MiB
- dependencies: `DATABASE_URL`, `REDIS_URL`, and PostgreSQL bootstrap values
- edge policy: exact `ALLOWED_HOSTS` and `CORS_ORIGINS`

Production startup validates identity settings, the D365 secret, session-secret length, and rejects wildcard CORS. `.env` is ignored by Git. Prefer injected environment variables, Docker secrets, or Azure Key Vault in production. Certificate authentication has an explicit configuration seam (`D365_TOKEN_AUTH_MODE`) but is not silently emulated; selecting it currently fails closed until certificate fields are added.

## Microsoft Entra app registrations

Use three identities: a browser SPA registration, a portal API registration, and the confidential D365 backend registration.

For portal SSO:

1. Create a single-tenant SPA registration with the exact HTTPS portal redirect/logout URI. Do not enable implicit grant.
2. Create a portal API registration. Expose delegated scope `access_as_user`; define app roles `employee`, `manager`, `hr`, `finance`, `portal_admin`, and `auditor` on this API.
3. Grant the SPA delegated permission to the API scope and perform tenant admin consent where policy requires it.
4. Set `VITE_PORTAL_CLIENT_ID` and `PORTAL_ALLOWED_CLIENT_IDS` to the SPA application ID. Set `PORTAL_API_AUDIENCE` to the API application client-ID GUID. Set `VITE_PORTAL_API_SCOPE` to `api://<API-CLIENT-ID>/access_as_user`.
5. Assign users or groups to API app roles through the Enterprise Application. The API requires both the delegated scope and a recognized app role.

The API validates RS256 signature, exact tenant issuer, audience, tenant, expiration, not-before, issued-at, v2 version, calling client (`azp`), delegated scope, and app roles.

### Apply confirmed UAT entity mappings

The checked-in mapping is bound to the discovered UAT hostname and is checked against live metadata before persistence:

```bash
docker compose exec backend python -m app.tools.apply_d365_mapping \
  config/d365-uat-confirmed.json
docker compose exec backend python -m app.tools.apply_d365_mapping \
  config/d365-uat-confirmed.json --apply
```

The first command is a dry run. The second enables identity, profile, and read-only leave balances;
employment, manager, leave requests, and approvals remain disabled pending record-semantics
validation. If the app-only D365 identity receives no rows from `EssLeaveBalances`, the leave service
falls back to `LeaveBalancesActive`, remains scoped to the verified personnel number and company,
and suppresses rows whose `HideLeaveBalances` value is enabled.

At first authenticated `/me` access, the portal automatically performs the same exact UPN lookup
and immutable object-ID verification. A unique result creates a verified local mapping plus mapping
history and an audit event. Missing, mismatched, duplicate, disabled, or conflicting mappings fail
closed. No name or email-only matching is allowed.

For administrator diagnosis or manual bootstrap without display-name matching:

First perform a read-only lookup by the immutable Entra object ID and independently verify the
returned personnel number and legal entity:

```bash
docker compose exec backend python -m app.tools.lookup_identity_candidate \
  --oid <ENTRA-OBJECT-ID> \
  --upn employee@example.ae
```

Some D365 environments reject filters on the object-ID field. The UPN option performs an exact
UPN query but still fails unless D365 returns the same immutable object ID supplied with `--oid`.
The lookup never writes a mapping and fails on missing, mismatched, or duplicate D365 matches.
After approval:

```bash
docker compose exec backend python -m app.tools.create_identity_mapping \
  --oid <ENTRA-OBJECT-ID> \
  --upn employee@example.ae \
  --personnel-number <D365-PERSONNEL-NUMBER> \
  --company <D365-LEGAL-ENTITY-ID> \
  --approved-by-oid <ADMIN-ENTRA-OBJECT-ID>
```

This records `manual_approved` as the source and creates mapping history. An administrator workflow will replace the bootstrap CLI later.

For D365, create a confidential application using client credentials. The scope is automatically derived as:

```text
https://sssa.operations.dynamics.com/.default
```

The D365 token never crosses the backend boundary and is never printed by either CLI.

## Dynamics 365 configuration

In D365 F&O, register the backend application under:

```text
System administration
  -> Setup
  -> Microsoft Entra applications / Azure Active Directory applications
```

Associate its client/application ID with a dedicated D365 service user. Do **not** use a System Administrator account. Begin with the minimum permission needed to read OData metadata, then create a custom D365 security role containing only the approved entity privileges after discovery and data-owner approval.

### Connectivity

From the backend container:

```bash
docker compose exec backend python -m app.tools.test_d365_connection
docker compose exec backend python -m app.tools.test_d365_connection --metadata
```

Expected output never contains token material:

```text
[OK] Entra token acquired
[OK] D365 connection successful
[OK] OData metadata accessible (N entity sets)
Environment: https://sssa.operations.dynamics.com
```

Common failures:

- token acquisition failure: verify tenant, application ID, credential validity, and system clock
- HTTP 401: verify the secret and application registration
- HTTP 403: verify the D365 Entra application association and service-user role
- timeout: verify on-prem DNS, proxy, firewall, and outbound TLS access to Microsoft identity and the D365 hostname

### Metadata discovery

Search names and properties from the environment's actual `$metadata` document:

```bash
docker compose exec backend python -m app.tools.search_d365_entities worker
docker compose exec backend python -m app.tools.search_d365_entities email --fields
```

Results are candidates, not authorization to use an entity. Confirm entity purpose, company context, field semantics, security permissions, and data classification with the D365 owner before configuring profile queries.

## PostgreSQL, Redis, and migrations

Compose supplies private PostgreSQL and Redis services with persistent named volumes. The application uses async SQLAlchemy, parameterized statements, health-checked pooling, and an Alembic scaffold. Schema tables arrive with the identity-mapping/audit milestones so this discovery milestone does not introduce speculative schema.

Redis is not exposed to the host. Metadata may be cached for six hours when the service is constructed with Redis. Access tokens currently use MSAL's process-local cache, minimizing shared secret material; production scale-out can add an encrypted distributed MSAL cache after the organization chooses a key-management system.

## HTTPS and production deployment

The checked-in Compose port 80 is for local bootstrap only. Production Entra authentication requires HTTPS. Use an internal corporate CA or publicly trusted certificate and adapt `nginx/tls.conf.example`; redirect port 80 to 443 and enable HSTS only after HTTPS is proven for the intended domain.

Before production:

- pin frontend dependency versions with an audited lockfile
- set `APP_ENV=production` and `API_DOCS_ENABLED=false`
- restrict allowed hosts/CORS to the exact portal origin
- inject secrets from an approved secret store and define rotation procedures
- terminate TLS at Nginx, limit management access, and forward logs to the SIEM
- back up PostgreSQL and test restoration
- add container image scanning and signed-image promotion

## Troubleshooting and operational notes

`/health/live` checks only the process. `/health/ready` checks PostgreSQL and Redis without returning connection details. D365 is deliberately excluded from readiness: an external outage should degrade D365-backed features, not cause an on-prem restart storm. Use the connectivity CLI or future internal telemetry for D365 health.

The OData client follows no redirects, caps page size, validates configured identifiers, escapes apostrophes in string literals, retries only GET operations, honors bounded `Retry-After`, and never returns raw D365 payloads to a browser. Employee DTO filtering and object authorization will be added before employee endpoints exist.
