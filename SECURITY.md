# Security Policy

## Reporting a vulnerability

Open a GitHub issue marked `security` if the problem is not exploitable with a
user's own key, or contact the repository owner privately through GitHub if it is.
Please do not include any real API key, token, or live record data in a report.

## Credential handling — the rules this project follows

- **No credentials are shipped.** This repository contains no API key, token, surrogate
  value, or real account identifier. Workspace hosts, company IDs, and record data from
  the author's account were removed before publication (see `REVIEW.md`).
- **Bring your own key.** Every user registers their own Agiled API key through Muse's
  secure API-access flow, or sets `AGILED_API_TOKEN` in their own shell environment for
  standalone use. The client never writes the key to disk and never prints it; error
  messages are sanitised so URLs (which carry the key as a query parameter, per Agiled's
  own API design) are not echoed back.
- **Fixed destination.** Requests are built against one hard-coded API host
  (`my.agiled.app`) with an allowlist re-check inside Muse's credential layer, redirects
  are refused, and user-supplied paths are validated so they cannot escape `/api/v1`
  or smuggle a second credential parameter.
- **Output is sensitive.** The client prints full API payloads to stdout. Anything that
  captures that output (shell history, CI logs, agent transcripts) will persist record
  fields — treat it accordingly and do not paste raw `users` output into issues.

## Supported versions

Only the latest release is supported. The Agiled API is undocumented publicly and can
change without notice; if a route breaks, please file an issue with the (redacted)
error JSON the client prints.
