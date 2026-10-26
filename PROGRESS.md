# Trace implementation and handoff

## Design
Build a local evidence investigation agent suitable for a portfolio submission.
Python 3.11+ standard library HTTP service, dependency-free browser client, and optional
Ollama synthesis. Default mode uses real BM25 retrieval and verbatim extracts, not a
simulated language model. No cloud calls, model downloads, or dependencies at runtime.
Demo material is explicitly fictional. User documents are treated as data.

## Plan and acceptance
- [x] Tests first: document validation, stable chunk citations, relevance ranking,
  search expansion, numerical discrepancy detection, insufficient-evidence behavior.
- [x] Implement bounded planning/search/verification/report tools and optional local
  model adapter; reject invalid citations and fall back honestly on model errors.
- [x] Test HTTP boundaries with a real ephemeral server: schema errors, request size,
  traversal, origin checks, content types, methods, health and complete investigations.
- [x] Build responsive, keyboard-accessible UI: source manager, demo, investigation,
  evidence inspector, execution log, local history, cancellation, Markdown export.
- [x] Run browser acceptance flows at desktop and mobile widths; check errors and
  overflow; capture a real screenshot. Run full checks and inspect final diff.
- [x] Add README, architecture, test instructions, license, CI, sample submission.
- [ ] Create GitHub repository in the authenticated user's account, publish the
  project, verify remote files and commit. No deployment requested or performed.

## Checks and handoff
Local implementation complete. Final check script passes: 64 Python tests, 8 client
tests, Python compilation, JS syntax, and whitespace checks. Browser checks and
real screenshots are recorded in docs/TESTING.md. Final diff reviewed, including
Windows early-response resets and Python/browser Unicode coordinate regressions.

The workspace was empty; no prior code or user changes were overwritten. Public
repository created at https://github.com/mattwatson7/trace-evidence-agent.
Publication and remote CI verification are the remaining steps. GitHub connector
access works; local gh credentials are invalid. No deployment has been requested.

Optional live Ollama inference is unverified. Wire protocol and failure handling
were checked using real loopback test servers; temporary fixtures were stopped.
No packages or models were installed and no paid APIs were called.
