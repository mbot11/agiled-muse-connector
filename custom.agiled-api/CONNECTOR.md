# Agiled Api

- `custom.agiled-api` connects Muse to Agiled through its REST API at `https://my.agiled.app/api/v1`. It authenticates with a registered `api_key` credential, placed as the `api_token` query parameter. Requests go only to `my.agiled.app`; your workspace host (for example `your-workspace.agiled.app`) is used as the `Brand` header value and registered as a second host, but never receives API requests directly.

- Every request also needs a `Brand` header. Verified live on 2026-11-02 against a real workspace: the brand value is the **full workspace host**. A bare subdomain returns 401 Invalid Brand. The helper resolves the brand in this order: `--brand` flag (it works before or after the subcommand), the `AGILED_BRAND` environment variable, then the configured default. The public copy ships with the placeholder `your-workspace.agiled.app` as the default and **refuses to send anything until a real brand is configured**.

- Helpers live in `custom.agiled-api/bin/` (paths in this doc are relative to the repository root; adjust to wherever you install the connector). The main helper is `agiled.py`, a full capability client with named list commands plus generic `get` and `request` commands that reach any method and path under `/api/v1`. The second helper is `healthcheck.py`.

## Connect

- Register the connection with Muse's API-access flow (`credentials.request_api_access`) using these details, substituting your own workspace host:

```json
{
  "provider": "agiled-api",
  "auth_scheme": "api_key",
  "placement": "query_param:api_token",
  "api_hosts": ["my.agiled.app", "your-workspace.agiled.app"]
}
```

- Before the first change in a conversation, prove access with a harmless read:

```text
python3 custom.agiled-api/bin/agiled.py users
```

## Credentials

- The registered connection holds the credential. Inside Muse, helpers import the platform's `dynamic_credentials` module, which returns an `hsurr:` surrogate and places it where the provider reads the key; Muse swaps in the real credential only on an approved request to a registered host. Outside Muse, the helper falls back to the `AGILED_API_TOKEN` environment variable; if neither source is available it exits with a clean configuration error and sends nothing.

- Never put a key, token, password or cookie in this doc, a helper file, a command argument or a log. The single exception is the standalone fallback described above: an operator may set `AGILED_API_TOKEN` in their own shell environment (never in a file, and the helper never writes it anywhere). Never paste a key in chat.

- Keep redirects disabled on authenticated requests (the helper refuses redirects).

- On a 401 or 403, check the request first. Confirm that the helper attached the credential, that the host is registered and that the placement matches. Only when a request that carried the credential is still rejected, re-register the connection with the details above and `"reconnect": true`.

## What verification looks like

- On a healthy workspace, `users` returns the account's users (a single-owner workspace returns one active user), `currencies` returns 166 entries, and most other resources return an empty list until you create records. `healthcheck.py` prints PASS with the users/contacts/projects counts and no record contents.

- The API does not expose a plan or tier name on the routes probed.

## List records

- List any verified resource with its named command. Add `--param key=value` for query parameters such as pagination where the resource supports it:

```text
python3 custom.agiled-api/bin/agiled.py contacts
python3 custom.agiled-api/bin/agiled.py invoices
python3 custom.agiled-api/bin/agiled.py currencies
```

- Named list commands are users, contacts, accounts, projects, tasks, invoices, estimates, expenses, contracts, docs, employees, products, tickets, payments, currencies and departments. Every one returned 200 on 2026-11-02 except contracts, covered under Recover from errors.

- Responses wrap records in a `data` field. Contacts also return Laravel pagination fields such as `current_page`, so page through contacts with `--param page=2` and following pages. Other resources may return a plain `data` list, so always read the shape of the response you got.

- User records carry sensitive fields such as payment identifiers. Summarise user reads and never quote those fields back.

## Read any path

- Read any path under `/api/v1` with the generic get command:

```text
python3 custom.agiled-api/bin/agiled.py get /contacts --param page=2
```

- A get on a single contact path returned a paginated envelope in testing rather than one bare record. Prefer list calls and filter by the fields you need when an exact single record read matters.

## Create, update and delete records

- Call any method on any path with the generic request command. Pass the JSON body with `--json` or `--body-file`:

```text
python3 custom.agiled-api/bin/agiled.py request POST /contacts --json '{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com","role":"Client"}'
python3 custom.agiled-api/bin/agiled.py request PUT /projects/123 --json '{"project_name":"Renamed","start_date":"2026-11-02"}'
python3 custom.agiled-api/bin/agiled.py request DELETE /projects/123
```

- Creating a contact requires a `role` field, and the only value verified so far is `Client` with a capital C. The values lead, client, customer and contact in lower case were all rejected as invalid on 2026-11-02.

- Creating a project requires `project_name` and `start_date`. A create, an update and a delete on projects, and a create plus delete on contacts, were all verified live on 2026-11-02 with throwaway test records that were deleted afterwards.

- The request body must be a single JSON object. Passing both `--json` and `--body-file`, an empty `--json`, malformed JSON, or an unreadable body file is refused locally with a clean usage error (exit 2) before anything is sent. A `--body-file`'s parsed contents are transmitted to Agiled — only pass files whose contents you intend to send.

- The helper prints full response payloads to stdout. Anything that captures that output (shell logs, CI, transcripts) will persist record fields, including the sensitive user fields noted above. Treat helper output as sensitive data.

- Get the user's approval before any write that affects clients, money or other people. A delete cannot be undone through this helper.

## Routes that do not exist

- Probing on 2026-11-02 returned 404 route not found for deals, subscriptions, documents, proposals, leads, pipelines, appointments and roles. Do not call them again without new evidence from the in-app developer docs at `https://my.agiled.app/developers`, which need a signed-in browser session to read.

- Documents from the platform are served by the `/docs` route, which the docs list command covers.

## Recover from errors

- A 401 with the message Invalid Brand means the Brand header value is wrong. Use your full workspace host. A bare subdomain or the company name will fail. If the error says the brand is not configured, you are still running with the shipped placeholder — set `--brand` or `AGILED_BRAND`.

- A 422 response carries field level validation errors in its body. Read the named field, fix the payload, and only then send the request again. Contact and project creates above show the two verified cases.

- A 429 with the message Too Many Attempts means Agiled rate limited the key. Limits are aggressive in practice, with throttling seen after only a handful of rapid calls, and no limit is published. The helper retries a 429 up to twice (a 429 means the request was rejected before processing, so a retry cannot duplicate a write), honouring Retry-After clamped to between 1 and 120 seconds with small jitter. Space manual calls out instead of looping tightly.

- Paths are normalised before use. A path containing `..` (raw or URL-encoded), a host, a query string, a fragment, or spaces/control characters is refused locally, so every generic call stays under `/api/v1`. A caller-supplied `api_token` query parameter is ignored with a warning, because the helper manages that parameter itself.

- All failures print one JSON object to stderr — `{"error": ..., "body": ...}` — and exit non-zero: exit 2 for local usage or configuration errors, exit 1 for API, network and credential failures. There are no raw Python tracebacks in normal operation.

- Listing `/contracts` returned a 500 Server Error on 2026-11-02 while every neighbouring route worked. Treat contract listing as faulty upstream until a later check succeeds. Creating or reading a single contract is untested.

- After a failed or timed out change, check the current state with a read before trying again, because the first request may have completed.

## Limits

- The connector reaches only the registered hosts. The in-app developer docs and any route that needs a browser session stay out of reach of this API key.

- No native Agiled MCP server exists as of 2026-11-02. MCP access sold through Zapier is a separate third party route and is not part of this connector.

- Endpoint coverage beyond the probed list routes is untested. The generic request command can reach further routes from the developer docs, and each new route should be read tested before a write is trusted.

## Related skills

- [Agiled](../local-agiled/SKILL.md)
