---
name: local-agiled
description: Use Agiled when the user asks about their Agiled workspace — users, CRM contacts and accounts, projects, tasks, invoices, estimates, expenses, contracts, docs, employees, products, tickets, payments, currencies or departments — via the custom.agiled-api REST connector with full read and write access.
---

# Agiled

- Read the connector doc first: `custom.agiled-api/CONNECTOR.md` (relative to the repository root; adjust to your install location).
- Helper: `python3 custom.agiled-api/bin/agiled.py <command>` — named list commands for users, contacts, accounts, projects, tasks, invoices, estimates, expenses, contracts, docs, employees, products, tickets, payments, currencies, departments, plus `get <path>` and `request <METHOD> <path> --json '<body>'` for everything else the API exposes.
- Every call needs a Brand header naming the workspace host (for example `your-workspace.agiled.app`). Configure it with `--brand` (before or after the subcommand) or the `AGILED_BRAND` environment variable. The shipped placeholder brand makes the helper refuse to send anything until a real brand is configured.
- Failures print one clean JSON error to stderr (exit 2 = usage/config, exit 1 = API/network) — no tracebacks. Paths that would escape `/api/v1` are refused locally. Full response payloads go to stdout, so treat captured helper output as sensitive.
- Verified live 2026-11-02 against a real workspace: all list reads above (contracts listing returns a 500 upstream), contact create + delete, project create + update + delete. Test records were removed afterwards.
- Creating a contact requires `"role": "Client"` (capital C). Creating a project requires `project_name` and `start_date`.
- Writes are fully wired. Still get the user's approval in the conversation before a write that affects clients, money, or other people, and before any delete — deletes cannot be undone.
- Rate limits are aggressive (429 "Too Many Attempts." after a handful of rapid calls). The helper backs off and retries twice, honouring Retry-After clamped to 1–120 seconds. Do not loop calls tightly.
- Health check: `python3 custom.agiled-api/bin/healthcheck.py` prints PASS with users/contacts/projects counts and no record contents.
- Routes that returned 404 and do not exist: deals, subscriptions, documents (use `docs`), proposals, leads, pipelines, appointments, roles. The full endpoint catalogue lives in the login-gated docs at my.agiled.app/developers — enumerate from there before assuming a route.
- User records contain sensitive payment identifier fields. Summarise, never quote them.
- There is no native Agiled MCP server. Do not route this account through Zapier MCP instructions.

## Available connectors

- [Agiled Api](../custom.agiled-api/CONNECTOR.md) — `custom.agiled-api`, API key as `api_token` query parameter plus `Brand` header, verified live 2026-11-02.
