# Provenance

- **What this is:** an original, standard-library-only Python client plus a Muse
  connector descriptor and companion skill for the Agiled REST API. No Agiled code,
  SDK, documentation text, or assets are included — endpoints, field names, and error
  behaviour are facts learned by calling the API, recorded in the connector doc.
- **How it was built:** written by Atlas (a Muse agent) working for the repository
  owner, on 2026-11-02, and verified live against the owner's own Agiled workspace:
  every list route was read, throwaway contact/project records were created, updated,
  and deleted to prove the write paths, and the account was confirmed back at its
  starting state afterwards.
- **How it was reviewed:** the code went through a full QA pass before publication —
  a manual security audit, an independent second-agent code review (25 findings, all
  fixed or explicitly scoped), a re-review (8 further findings, fixed), three automated
  skill/code scanners with every finding hand-adjudicated, and a live regression run.
  The adjudication record is summarised in `REVIEW.md`.
- **Genericisation:** the author's workspace host, company ID, and account details were
  replaced with the placeholder `your-workspace.agiled.app` and example data before
  this copy was staged for publication. The placeholder configuration makes the client
  refuse to send requests until a real brand is set, so an unconfigured clone can
  never call the author's workspace (or anyone else's).
- **Trademark note:** "Agiled" is a trademark of its owner. This project is an
  independent, unofficial integration and is not affiliated with or endorsed by Agiled.
