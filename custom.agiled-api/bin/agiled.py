#!/usr/bin/env python3
"""Agiled CLI helper for the custom.agiled-api connector.

Talks to the Agiled REST API (https://my.agiled.app/api/v1). Inside Muse
the registered API key is swapped in at request time through the dynamic
credential surrogate (query_param:api_token placement); the key itself
never appears in this file, in arguments, or in logs. Outside Muse, set
the AGILED_API_TOKEN environment variable instead — it is read at call
time and never printed.

Agiled also requires a Brand header naming the workspace. Verified live
on 2026-11-02 against a real workspace: the brand value is the full
workspace host, "your-workspace.agiled.app" (a bare subdomain returns
401 Invalid Brand). The brand is not a secret, but it is per-account
configuration: resolution order is the --brand flag, then the
AGILED_BRAND environment variable, then DEFAULT_BRAND below. Until a
real brand is configured the client refuses to send anything.

Full capability: the generic `request` command can call any API method
on any path under /api/v1 (paths are normalised and anything escaping
/api/v1 is refused). Named commands cover the resources verified live.
Writes go through the same code path as reads. Deleting is exposed only
through the generic request command so it stays a deliberate, explicit
call.

Usage examples:
  agiled.py users
  agiled.py contacts
  agiled.py projects
  agiled.py invoices
  agiled.py get /contacts --param page=2
  agiled.py request POST /contacts --json '{"first_name":"Ada","email":"ada@example.com","role":"Client"}'
  agiled.py request DELETE /contacts/123
"""

import argparse
import http.client
import json
import os
import posixpath
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Credential source 1 (preferred inside Muse): the platform surrogate.
# Imported defensively so the CLI still runs standalone (source 2) when
# the Muse module is absent.
try:
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import url_with_surrogate_query_param

    _HAVE_SURROGATE = True
except Exception:  # pragma: no cover - depends on environment
    url_with_surrogate_query_param = None
    _HAVE_SURROGATE = False

CREDENTIAL = "custom.agiled-api"
ALLOWED_HOSTS = ["my.agiled.app"]  # the only host requests are ever sent to
BASE = "https://my.agiled.app/api/v1"
# Placeholder shipped with the public copy. Configure your real
# workspace host via --brand or AGILED_BRAND; while the brand is still
# this placeholder the client raises a configuration error and sends
# nothing.
PLACEHOLDER_BRAND = "your-workspace.agiled.app"
DEFAULT_BRAND = PLACEHOLDER_BRAND
USER_AGENT = "agiled-muse-connector/1.1 (Python urllib)"
MAX_BODY_BYTES = 10_000_000
BRAND_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$")


class AgiledError(Exception):
    """A failed API call or local validation error, shown as clean JSON."""

    def __init__(self, code, body):
        super().__init__(str(body))
        self.code = code
        self.body = body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise AgiledError("redirect", "redirect refused, verify the endpoint")


def validate_brand(brand):
    if not brand or not BRAND_RE.fullmatch(brand.strip()):
        raise AgiledError(
            "config",
            f"invalid brand {brand!r}: expected a workspace host such as "
            "'your-workspace.agiled.app'",
        )
    return brand.strip()


def normalize_path(path):
    """Return a clean path guaranteed to stay under /api/v1."""
    if not isinstance(path, str) or not path.strip():
        raise AgiledError("usage", "path must be a non-empty string")
    if "://" in path or path.startswith("//"):
        raise AgiledError("usage", f"path must not contain a host: {path!r}")
    if "?" in path or "#" in path:
        raise AgiledError(
            "usage",
            "path must not contain '?' or '#'; pass query values with --param",
        )
    if "\\" in path:
        raise AgiledError("usage", "path must not contain backslashes")
    if any(ord(char) < 33 or ord(char) == 127 for char in path):
        raise AgiledError(
            "usage", "path must not contain spaces or control characters"
        )
    # Reject dot segments in the raw and URL-decoded path before any
    # normalisation can collapse them away.
    if ".." in path.split("/") or ".." in urllib.parse.unquote(path).split("/"):
        raise AgiledError("usage", f"path must not contain '..' segments: {path!r}")
    if not path.startswith("/"):
        path = "/" + path
    clean = posixpath.normpath(path)
    if clean == "." or clean == "/":
        raise AgiledError("usage", f"path names no resource: {path!r}")
    return clean


def build_url(path, params):
    url = BASE + normalize_path(path)
    query = dict(params or {})
    if "api_token" in query:
        # The credential parameter is managed by this helper; a caller
        # supplied value would duplicate or shadow it, so drop it.
        print("warning: ignoring caller-supplied api_token parameter",
              file=sys.stderr)
        del query["api_token"]
    if query:
        url += "?" + urllib.parse.urlencode(query)
    if _HAVE_SURROGATE:
        return url_with_surrogate_query_param(
            url, CREDENTIAL, allowed_hosts=ALLOWED_HOSTS
        )
    token = os.environ.get("AGILED_API_TOKEN", "").strip()
    if not token:
        raise AgiledError(
            "config",
            "no credential available: the Muse credential surrogate is "
            "absent and AGILED_API_TOKEN is not set",
        )
    sep = "&" if "?" in url else "?"
    return url + sep + urllib.parse.urlencode({"api_token": token})


def resolve_brand(flag_value):
    """--brand flag, then AGILED_BRAND (even if set empty, so validation
    can reject it loudly), then the configured default."""
    if flag_value is not None:
        return flag_value
    if "AGILED_BRAND" in os.environ:
        return os.environ["AGILED_BRAND"]
    return DEFAULT_BRAND


def call(method, path, params=None, body=None, brand=None):
    if brand is None:
        brand = resolve_brand(None)
    brand = validate_brand(brand)
    if brand == PLACEHOLDER_BRAND:
        raise AgiledError(
            "config",
            "brand not configured: pass --brand <your-workspace>.agiled.app "
            "or set AGILED_BRAND to your Agiled workspace host",
        )
    try:
        url = build_url(path, params)
    except AgiledError:
        raise
    except Exception as exc:  # credential helper errors (RuntimeError subclass)
        raise AgiledError("credential", str(exc)) from exc
    headers = {
        "Accept": "application/json",
        "Brand": brand,
        "User-Agent": USER_AGENT,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    opener = urllib.request.build_opener(NoRedirect())
    # Agiled rate-limits aggressively (429 "Too Many Attempts." seen after
    # a few rapid calls). A 429 means the request was rejected before
    # processing, so retrying any method is safe from duplication; retry
    # up to twice, honouring Retry-After clamped to [1, 120]s with jitter.
    # Other errors are not retried.
    delay = 20
    for attempt in range(3):
        request = urllib.request.Request(url, headers=headers, method=method, data=data)
        try:
            with opener.open(request, timeout=60) as response:
                raw = response.read(MAX_BODY_BYTES + 1)
                if len(raw) > MAX_BODY_BYTES:
                    raise AgiledError(
                        "protocol",
                        f"response exceeded {MAX_BODY_BYTES} bytes, refusing to process",
                    )
                if not raw:
                    return {"status": response.status, "body": ""}
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise AgiledError(
                        "protocol", "response body was not valid UTF-8"
                    ) from exc
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"status": response.status, "body": text}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", "replace")[:1200]
            if exc.code == 429 and attempt < 2:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                base = int(retry_after) if (retry_after or "").isdigit() else delay
                wait = min(max(base + random.uniform(0, 3), 1), 120)
                print(f"rate limited (429), waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                delay *= 2
                continue
            raise AgiledError(exc.code, body_text) from exc
        except AgiledError:
            raise
        except http.client.HTTPException as exc:
            # Sanitised on purpose: some HTTPException messages (e.g.
            # InvalidURL) embed the full request URL, which can carry
            # the api_token value in standalone mode. Type name only.
            raise AgiledError(
                "network", f"HTTP protocol error ({type(exc).__name__})"
            ) from exc
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
            raise AgiledError("network", str(exc)) from exc


def parse_params(items):
    params = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise AgiledError(
                "usage", f"--param expects key=value, got {item!r}"
            )
        if key in params:
            print(f"warning: duplicate --param {key!r}, last value wins",
                  file=sys.stderr)
        params[key] = value
    return params


def load_body(args):
    if args.json_body is not None and args.body_file is not None:
        raise AgiledError("usage", "pass only one of --json and --body-file")
    body = None
    if args.json_body is not None:
        if not args.json_body.strip():
            raise AgiledError("usage", "--json body must not be empty")
        try:
            body = json.loads(args.json_body)
        except json.JSONDecodeError as exc:
            raise AgiledError("usage", f"invalid --json body: {exc}") from exc
    elif args.body_file is not None:
        try:
            with open(args.body_file, "r", encoding="utf-8") as handle:
                body = json.load(handle)
        except OSError as exc:
            raise AgiledError("usage", f"cannot read --body-file: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AgiledError("usage", f"invalid JSON in --body-file: {exc}") from exc
    if body is not None and not isinstance(body, dict):
        raise AgiledError("usage", "request body must be a JSON object")
    return body


# Resource name -> list path. Every entry was verified live on
# 2026-11-02 (see CONNECTOR.md). Probed and NOT routes (404): deals,
# subscriptions, documents, proposals, leads, pipelines, appointments,
# roles. Documents live under /docs. Listing /contracts returned a
# 500 server error, so the route exists but is faulty upstream.
LIST_COMMANDS = {
    "users": "/users",
    "contacts": "/contacts",
    "accounts": "/accounts",
    "projects": "/projects",
    "tasks": "/tasks",
    "invoices": "/invoices",
    "estimates": "/estimates",
    "expenses": "/expenses",
    "contracts": "/contracts",
    "docs": "/docs",
    "employees": "/employees",
    "products": "/products",
    "tickets": "/tickets",
    "payments": "/payments",
    "currencies": "/currencies",
    "departments": "/departments",
}


def main():
    parser = argparse.ArgumentParser(description="Agiled REST API (full capability)")
    parser.add_argument("--brand", default=None,
                        help="Workspace brand host (or set AGILED_BRAND)")
    brand_parent = argparse.ArgumentParser(add_help=False)
    brand_parent.add_argument("--brand", default=argparse.SUPPRESS,
                              help="Workspace brand host (or set AGILED_BRAND)")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in LIST_COMMANDS:
        p = sub.add_parser(name, parents=[brand_parent], help=f"List {name}")
        p.add_argument("--param", action="append", default=[],
                       help="key=value query parameter, repeatable")

    p = sub.add_parser("get", parents=[brand_parent], help="GET any path under /api/v1")
    p.add_argument("path")
    p.add_argument("--param", action="append", default=[])

    p = sub.add_parser("request", parents=[brand_parent],
                       help="Any method on any path under /api/v1")
    p.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    p.add_argument("path")
    p.add_argument("--param", action="append", default=[])
    p.add_argument("--json", dest="json_body",
                   help="JSON request body as a string")
    p.add_argument("--body-file",
                   help="Path to a file holding the JSON request body")

    args = parser.parse_args()
    brand = resolve_brand(getattr(args, "brand", None))

    try:
        brand = validate_brand(brand)
        if args.command in LIST_COMMANDS:
            result = call("GET", LIST_COMMANDS[args.command],
                          params=parse_params(args.param), brand=brand)
        elif args.command == "get":
            result = call("GET", args.path, params=parse_params(args.param),
                          brand=brand)
        elif args.command == "request":
            body = load_body(args)
            result = call(args.method, args.path, params=parse_params(args.param),
                          body=body, brand=brand)
        else:  # pragma: no cover
            parser.error("unknown command")
    except AgiledError as exc:
        print(json.dumps({"error": exc.code, "body": exc.body}), file=sys.stderr)
        sys.exit(2 if exc.code in ("usage", "config") else 1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
