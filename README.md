# Agiled Muse Connector

An unofficial connector + CLI for the [Agiled](https://agiled.app) REST API, built for
[Muse](https://muse.ai) and usable as a plain command-line client anywhere Python 3 runs.

> **Unofficial.** This project is not affiliated with, endorsed by, or supported by Agiled.
> It is an independent integration built against Agiled's customer API. Every user supplies
> their own Agiled API key — no credentials are included, requested by, or shared with this project.

## What it does

- **Full read + write coverage** of the verified Agiled API surface: users, contacts, accounts,
  projects, tasks, invoices, estimates, expenses, contracts, docs, employees, products, tickets,
  payments, currencies, departments — plus a generic `get` / `request` escape hatch for any other
  path under `/api/v1`.
- **Live-verified behaviour** (2026-11-02, against a real workspace), including the quirks that
  are not in any public doc:
  - the `Brand` header must be the **full workspace host** (a bare subdomain gets 401),
  - creating a contact requires `"role": "Client"` (capital C),
  - creating a project requires `project_name` + `start_date`,
  - rate limits are aggressive — the client retries 429s with `Retry-After` honoured and clamped,
  - listing `/contracts` currently returns a 500 from Agiled's side,
  - several plausible routes (`/deals`, `/leads`, `/pipelines`, …) do not exist; documents live under `/docs`.
- **Hardened by design:** no third-party dependencies (Python standard library only), redirects
  refused, request paths validated so they cannot escape `/api/v1`, clean JSON errors instead of
  tracebacks, a 10 MB response cap, and a healthcheck that cannot false-PASS on a degraded response.

## Layout

| Path | What it is |
|---|---|
| `custom.agiled-api/` | The Muse connector: `CONNECTOR.md` (operating doc), `connector.yaml`, `bin/agiled.py` (client), `bin/healthcheck.py` |
| `local-agiled/` | The companion Muse skill (`SKILL.md`) |
| `tests/` | Offline smoke tests (no network, no credentials needed) |
| `examples/` | Example request payloads with placeholder data |

## Quick start

### Inside Muse

1. Copy `custom.agiled-api/` and `local-agiled/` into your Muse workspace's connector/skill
   locations (or keep them together and point your setup at them).
2. Register the API connection with your own Agiled API key and workspace host — the exact
   registration payload is in `custom.agiled-api/CONNECTOR.md` under **Connect**.
3. Configure your brand (workspace host) and run a first read:

```bash
export AGILED_BRAND=your-workspace.agiled.app
python3 custom.agiled-api/bin/healthcheck.py
python3 custom.agiled-api/bin/agiled.py contacts
```

### Standalone (any machine with Python 3)

```bash
export AGILED_API_TOKEN=<your Agiled API key>
export AGILED_BRAND=your-workspace.agiled.app
python3 custom.agiled-api/bin/agiled.py users
python3 custom.agiled-api/bin/agiled.py request POST /contacts --body-file examples/create-contact.json
```

The token is read from the environment at call time and is never printed, logged, or written
to disk by the client. While the brand is still the shipped placeholder
(`your-workspace.agiled.app`), the client refuses to send anything and tells you to configure it.

## Safety model

- Writes are fully wired, including deletes. The companion skill instructs the agent to get the
  user's approval before any write that affects clients, money, or other people, and before any
  delete (deletes cannot be undone).
- The client prints full API payloads to stdout; treat captured output as sensitive —
  Agiled user records can contain payment-identifier fields.
- Error contract: failures print one JSON object to stderr and exit non-zero
  (2 = usage/configuration, 1 = API/network/credential). No tracebacks in normal operation.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests are offline: they exercise path validation, parameter/body parsing, brand
resolution and validation, the credential-fallback URL builder, and the healthcheck's
response-shape strictness — no network and no API key required.

## Known upstream issues (Agiled side, verified 2026-11-02)

- `GET /contracts` returns 500 Server Error while neighbouring routes work.
- API documentation is login-gated inside the app; there is no public OpenAPI spec.
- No published rate limits; observed throttling begins after a handful of rapid calls.

## License

MIT — see [LICENSE](LICENSE). Security reports: see [SECURITY.md](SECURITY.md).
How this was built and verified: see [PROVENANCE.md](PROVENANCE.md) and [REVIEW.md](REVIEW.md).
