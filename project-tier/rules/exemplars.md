# Exemplars: Canonical Implementations to Mirror

This catalog pairs a ratified design decision with the canonical file to copy from and
a one-line reason. When you start new work that matches one of these decisions, read
the cited module first and mirror its shape. The entries name stable module paths, not
line numbers, so they survive refactors.

These exemplars encode the same default-good the rules describe: prefer a typed model
over a raw dict, fail fast on missing configuration, reuse a published boundary instead
of reaching into another service. For the module-cohesion rule they reflect, see the
Naming & Organization section in `code-style.md`.

## Service-to-service authentication: Entra client-credentials over static JWT

Mirror `src/python/mx2/workers_comp/api/app.py`: it builds an explicit authenticator
chain (`EntraClientCredentialsAuthenticator(...)` plus `EntraJWTAuthenticator()`) and
passes it to `FastAPIConfig(authenticators=...)`. Prefer this chain form for new
services. `src/python/mx2/court_reporting/api/app_init.py` uses the older config-path
form (`FastAPIConfig(entra_client_credentials_secret_id=...)`); it is acceptable but
not the shape to copy. Implementation reference:
`src/python/mx2/auth/authenticators/entra_client_credentials.py`.

The chain is authentication only, not authorization: `EntraJWTAuthenticator` admits
any valid company SSO user (it rejects only client-credentials tokens), so routes
that must be restricted to specific callers carry a per-route `require_roles(...)`
gate from `mx2.auth.rbac`, the way workers_comp gates `/coverage/verify` with
`require_roles(Roles.SALESFORCE)`. Gate every non-public route; the gotcha is
documented in `src/python/mx2/workers_comp/CLAUDE.md`.

Why: short-lived, role-scoped, centrally revocable tokens beat long-lived pre-shared
secrets.

## Operational store: DynamoDB via dyntastic, with a typed model

Mirror `src/python/mx2/folio/document/document_index.py`: a `Dyntastic` model with
`__table_name__`, `__hash_key__`, `__range_key__`, and conditional writes
(`save(condition=...)`) for deduplication. The model is the typed contract; do not
reach for a raw dict. To read another service's table without importing its settings,
follow the standalone own-table pattern in `src/python/mx2/<service>/coverage/models.py`
(`Dyn2redStatus` reads dyn2red's table, `CaseMatter` reads sf_sync's table, each with
`__table_name__()` derived from the local `AppSettings`).

Why: single-digit-millisecond key lookups, a Pydantic-backed model instead of an
untyped dict, and conditional writes for idempotency. DynamoDB via dyntastic is
already the named operational-store reference in `architecture.md`.

## API scaffolding: FastAPIBuilder plus FastAPIConfig

Mirror `src/python/mx2/api_builder/config.py` (`FastAPIConfig`, a frozen Pydantic model
with `extra="forbid"`) and `src/python/mx2/api_builder/builder.py` (`FastAPIBuilder`).
The smallest full example of wiring them together is
`src/python/mx2/workers_comp/api/app.py`.

Why: consistent middleware, a uniform healthcheck and verify surface, and a single
docs-exposure policy come for free; hand-wired apps drift from the standard.

## Configuration: self-contained Pydantic Settings with a Singleton lifecycle

Mirror `src/python/mx2/folio/api/settings.py`: an `AppSettings(BaseSettings, Singleton)`
whose required fields are declared without a default, so a missing value fails fast at
startup. The lifecycle primitive is `src/python/mx2/objects/singleton.py`, whose
`set_for_testing` context manager gives deterministic per-test configuration.

Why: missing required config fails at startup rather than mid-request; explicit required
fields beat implicit defaults; tests get isolated config with no global-state leakage.

## Module split by concern (the module-cohesion rule, applied)

There is no single file to mirror here; the pattern is the destination. Campaign
MX2-NNNNN takes a catch-all `utils.py`, splits it into concern-named modules, and moves
any test-only helper under the test tree. Mirror that destination, not a catch-all,
when a module starts to accrete unrelated helpers.

Why: each module names the concern it owns, production and test-only code no longer
share an import graph, and hidden duplication (a hand-rolled query that a typed accessor
already expresses) surfaces during the split.
