# Verification evidence

Verified on 26 October 2026, Windows, Python 3.13.2, Node 22.14.0, and Chromium
in the Codex browser. No package installation, paid API call, model download,
production database, or deployment was needed.

## Automated checks

- `python -m unittest discover -s tests -v`: **64 tests passed**.
- `node --test tests/client.test.mjs`: **8 tests passed**.
- Python compilation, JavaScript syntax, and whitespace checks are collected in
  `.codex/scripts/check.ps1` and run before publication.

| Suite | What it checks |
|---|---|
| Engine | Validation, limits, exact offsets/lines, changed-source IDs, relevance, headings, abstention, injection text, Unicode, bounded evidence, numeric comparisons |
| Gold-source evaluation | Release gate, retry failure, owner, decision, cache conditions, paired citations, abstention with a configured model |
| Local model contract | Actual loopback HTTP requests; success, invalid JSON/envelopes/schema, fabricated citations, excessive response size, HTTP errors, blocked redirects, fallback |
| HTTP boundary | Real ephemeral server; bundled assets, complete demo, bad JSON/UTF-8/schema, origins, Host/DNS rebinding, traversal, body limits, request methods, concurrency, recovery |
| Client logic | Collection constraints, Unicode, Markdown provenance/synthesis export, malformed history and verified snapshot restoration |

The gold-source set is small and authored with the demo. It is a regression
benchmark, not a broad estimate of retrieval accuracy or model quality.

## Browser acceptance results

These checks used the actual running app through its UI. They are separate from
the automated unit/integration suites and are not part of the CI matrix.

| Flow | Observed result |
|---|---|
| Load demo → investigate | Four sources, ten cited passages, two numerical discrepancy flags |
| Click 420 ms | Performance report opens with the exact sentence highlighted at line 5 |
| Filter performance report | Two evidence cards; All sources restores ten |
| Export brief | Browser downloads `trace-evidence-brief.md`; provenance and log preserved |
| Add a source | Collection count increases and the prior report invalidates |
| Duplicate source name | Inline error; no duplicate added |
| Pasted HTML/script in source/name | Rendered literally; no image/script elements created |
| Remove source | Count decreases; current report invalidates |
| Reload and reopen history | Original four-source snapshot and ten-passage report restored |
| Upload UTF-8 Markdown | Source added, including accented text |
| Upload invalid UTF-8 binary | Clear error; collection unchanged |
| Unrelated Jupiter question | Insufficient-evidence state and zero passages |
| Ctrl+Enter | Runs an investigation successfully |
| Mobile source shortcut | Jumps to source collection |
| Local model success fixture | Labeled synthesis with an inspectable citation |
| Local model invalid-citation fixture | Visible fallback; no invalid synthesis shown |
| Cancel delayed local-model fixture | Cancels browser request, restores controls and sources |
| Cancel after previous fallback | Cancellation message remains visible; previous warning does not overwrite it |
| Invalid model URL | Rejected before sending the investigation |
| Clear history, reload | No saved investigations remain |
| Run without sources | Clear instruction to add sources or load demo |
| About dialog + Escape | Dialog closes normally |
| Suggested question on empty collection | Loads demo sources and fills question |
| 390, 768, 1024 px viewport tests | No horizontal document overflow or off-screen buttons |
| Desktop visual review | Real workspace and report screenshots captured |
| Normal browser console | No unexpected warnings or errors before intentional offline test |
| Server stopped during next run | Clear connection error, prior report retained, controls recover |
| Server restarted | Re-run succeeds without changing the source collection |
| Emoji before cited text | Correct highlighted quotation and saved-history restoration using UTF-16 browser offsets |

The model fixtures emulate the Ollama wire protocol for acceptance testing. They
are **not a real language model**. The temporary fixture was stopped after testing;
the final demo is in extractive mode. Live model inference, model quality, and
performance on the user's hardware remain unverified.

## Performance sample

A local direct-engine smoke benchmark processed **270,300 characters / 10,200
passages across 12 documents in 160.1 ms**, returning the bounded ten passages.
This is a synthetic sample on one machine, not a performance guarantee.

## Reproduce

1. Run the commands in the README or the PowerShell check script.
2. Start `python -m trace.server` and repeat the browser flows above.
3. For a real local AI check, use a model already installed in Ollama. Ask the demo
   question, inspect synthesis citations, then stop Ollama and check fallback.
4. See `tests/test_model.py` for the deterministic local-model HTTP fixture.

## Remaining limits

No semantic entailment scoring, model-quality benchmark, general multilingual
retrieval benchmark, or production penetration test was performed. Browser tests
were on Chromium; Safari and Firefox were not tested. CI adds Windows/Linux and
Python 3.11/3.13 coverage; its actual remote outcome must be checked separately.

A repeated-request regression additionally checks 80 early HTTP rejections in one
test. This reproduced a Windows reset caused by closing sockets with unread
request bytes. Rejected small bodies are now drained with strict size/time bounds
before responding; oversized/chunked input is not consumed by that path.
