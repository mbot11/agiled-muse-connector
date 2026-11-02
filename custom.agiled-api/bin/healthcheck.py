#!/usr/bin/env python3
"""Healthcheck for the custom.agiled-api connector.

Runs three harmless reads (users, contacts, projects) through the same
code path as agiled.py and prints a one-line PASS summary with counts.
It prints no names, emails, or other record contents. A response that
does not carry a recognisable record list counts as FAIL, not as a
count of one, so a degraded API cannot produce a false PASS.
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

AGILED_PATH = Path(__file__).resolve().with_name("agiled.py")


def load_agiled():
    if not AGILED_PATH.exists():
        print(json.dumps({"healthcheck": "FAIL", "failed_on": f"missing {AGILED_PATH}"}))
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("agiled", AGILED_PATH)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(json.dumps({"healthcheck": "FAIL", "failed_on": "import agiled.py",
                          "detail": str(exc)[:200]}))
        sys.exit(1)
    return mod


def count_of(mod, path):
    result = mod.call("GET", path)
    if not isinstance(result, dict) or "data" not in result:
        raise ValueError(f"unexpected response shape for {path}")
    data = result["data"]
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        total = data.get("total")
        return total if isinstance(total, int) else len(data["data"])
    raise ValueError(f"unexpected data shape for {path}")


def main():
    mod = load_agiled()
    checks = []
    plan = [("users", "/users"), ("contacts", "/contacts"), ("projects", "/projects")]
    for index, (label, path) in enumerate(plan):
        try:
            checks.append(f"{label}={count_of(mod, path)}")
        except Exception as exc:  # AgiledError and response-shape errors
            print(json.dumps({"healthcheck": "FAIL", "failed_on": label,
                              "detail": str(exc)[:200]}))
            sys.exit(1)
        if index < len(plan) - 1:
            time.sleep(4)
    print(json.dumps({"healthcheck": "PASS", "counts": checks}))


if __name__ == "__main__":
    main()
