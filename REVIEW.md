# Review & Leak-Check Record — staged public copy

Staged 2026-11-02 from the author's private, live-verified connector (v1.1) and
genericised for publication. This file records what was checked **on this staged
tree** before any push. Nothing here was pushed anywhere at the time of writing.

## Leak check — the gate for this repo

Sweeps run over every file in this tree (text scan, plus a compiled-bytecode
check described below):

| Check | Result |
|---|---|
| API keys / tokens (pattern sweep: private-key headers, `ghp_`, `github_pat_`, `sk-ant`/`sk-proj`, `AKIA`, Slack tokens, credential surrogates `hsurr:…`, `key = "…"` literals) | **Zero hits** |
| High-entropy strings (≥28 chars, entropy > 4.2, URLs excluded) | **Zero candidates** |
| Account identifiers (workspace host, brand subdomain, company ID) | **Zero hits** — replaced by the placeholder `your-workspace.agiled.app` |
| Personal data (owner surname as data, GitHub username, phone fragments, personal email domains, other business names) | **Zero hits** |
| Personal filesystem paths (home-directory, user-profile, root, and private-workspace path prefixes) | **Zero hits** |
| Author name | Appears **only** as the copyright holder in `LICENSE` — intentional attribution for the owner's own repository |
| Platform paths | Exactly one: the Muse credential module location in `bin/agiled.py` (`/opt/muse/skills/…`). This is the same path on every Muse installation, contains no user data, and is required for the in-Muse credential surrogate to load |
| Compiled bytecode | A `__pycache__/*.pyc` produced during testing embedded the build machine's source path (normal Python behaviour). It was **deleted**, and `.gitignore` excludes `__pycache__/` and `*.pyc` so it cannot be committed |
| Environment files | None present; `.gitignore` excludes `.env*` |

Behavioural proof: with the shipped placeholder brand, the client exits with a
clean configuration error and sends nothing; with a deliberately wrong brand,
Agiled's server itself answers 401 Invalid Brand. An unconfigured or
misconfigured clone cannot reach the author's workspace.

## Functional verification on the staged copy

- **20 offline unit tests — all pass** (`tests/test_agiled.py`: path guards,
  parameter/body validation, brand resolution/validation, placeholder guard,
  credential-fallback URL building, healthcheck shape strictness).
- Both scripts compile clean (CPython 3.12); scripts are mode 0755.
- The underlying client is the same code that passed a full live regression on
  the author's workspace on 2026-11-02 (healthcheck PASS, 15/16 list routes OK
  with `/contracts` failing on Agiled's side, create/update/delete cycles clean).

## Scanner results on the staged copy (hand-adjudicated)

| Scanner | Raw result | Adjudication |
|---|---|---|
| SkillSpector v2.13.1 (skill) | score 0, 0 issues | Clean |
| SkillSpector v2.13.1 (connector) | score 93, 3 issues | **TT3 (CRITICAL, "data flow")** + **TM1 ×2 (HIGH, "tool misuse")** — all three are pattern matches on intended, documented behaviour: TT3 is the `AGILED_API_TOKEN` environment fallback flowing to Agiled's own hard-coded API host as the `api_token` parameter Agiled requires (inside Muse the surrogate path is used and the key never exists in the process); TM1 matches the DELETE examples in the docs/docstring — the connector's declared, approval-gated purpose. No finding involves an unintended destination or an undisclosed capability |
| Cisco skill-scanner (skill + code) | 3 findings | 2× MEDIUM network-use flags = the connector's declared purpose, hosts documented; 1× INFO "skill manifest has no license field" — the repository itself is MIT-licensed (`LICENSE` at root) |
| Bawbel 1.3.0 (pattern engine) | 6.8, 1 finding (AVE-2026-00026) | Same root as TT3: it pattern-matches the env-token line as "exfiltration via encoding". Destination is the fixed API host; adjudicated false positive for the reason above |

Scanner headlines measure pattern similarity, not destination or intent; the
two credential-flow findings exist **because** the standalone fallback was added
(removing it would clear them and make the client Muse-only). The fallback is
kept deliberately, and this note is the record of that decision.

## Provenance of the code

Original, standard-library-only. Full build/QA history: see `PROVENANCE.md`.
The private original (with the author's real configuration) is **not** part of
this repository and was not modified by staging.
