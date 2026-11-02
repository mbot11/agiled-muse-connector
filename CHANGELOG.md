# Changelog

## 1.1.0 — 2026-11-02

First public staging build, genericised from the author's private install.

- Genericised configuration: workspace brand is a placeholder
  (`your-workspace.agiled.app`) until configured via `--brand` or `AGILED_BRAND`;
  the client refuses to send anything while unconfigured. No account identifiers
  from the author's workspace are included anywhere in this repository.
- Repository scaffolding added: README, MIT LICENSE, SECURITY.md, PROVENANCE.md,
  REVIEW.md, offline smoke tests, example payloads.

Connector fixes carried in from the pre-publication QA round (all live-verified):

- Uniform clean JSON error contract (exit 2 usage/config, exit 1 API/network);
  no raw tracebacks, including for HTTP protocol errors, with URL-free messages
  so a credential can never leak through an error.
- Path validation: requests cannot escape `/api/v1` (host, query, fragment,
  backslash, space/control characters, and raw or URL-encoded `..` refused locally).
- 429 handling: Retry-After honoured, clamped to 1–120 s, with jitter.
- Standalone operation: `AGILED_API_TOKEN` environment fallback when Muse's
  credential surrogate is unavailable, with a clean configuration error otherwise.
- Caller-supplied `api_token` parameters are stripped with a warning;
  `--param` requires `key=value`; duplicate parameters warn.
- Request bodies validated locally (single JSON object; `--json`/`--body-file`
  are mutually exclusive).
- Responses capped at 10 MB; healthcheck resolves its sibling client by relative
  path and strictly fails on degraded or unexpected response shapes.
- Honest User-Agent (`agiled-muse-connector/1.1`).

## 1.0.0 — 2026-11-02

Private first build: full read/write client for the verified Agiled API surface
(16 named list commands + generic `get`/`request`), healthcheck, connector doc,
and companion skill. Verified live end-to-end, including create/update/delete
cycles on contacts and projects.
