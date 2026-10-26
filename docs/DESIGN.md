# Trace: show the evidence

Trace answers questions over a small local document collection. Its target use is
investigating a launch, project decision, or incident across conflicting notes.
It provides a reviewable evidence brief, not a truth verdict.

The agent has four bounded phases: derive lexical subqueries, search sentence
chunks with BM25 and query expansion, verify quotation provenance and compare
numbers sharing a metric, then compose an extractive report. A second retrieval
pass includes source diversity. Every finding carries a stable document/chunk ID.
Discrepancies are candidates for human review; time and scope can explain them.
Low overlap yields an explicit insufficient-evidence result.

Optional Ollama synthesis takes only retrieved chunks and a fixed instruction.
It returns JSON containing a summary and known citation IDs. Invalid output,
timeouts or missing models produce a visible fallback to extractive mode. The
adapter cannot execute tools or instructions in documents. Generated synthesis
is labeled and is not a substitute for inspecting the cited quotations.

The local HTTP service binds to 127.0.0.1. It has a fixed static-file allowlist,
JSON schema/size validation, same-origin write checks and no persistent server
storage. It never accepts a user-supplied model URL. Browser history is local,
bounded, and can be cleared. Documents never enter a URL or remote service.
No PDF parsing, web crawling, cloud APIs, accounts, or deployment are in scope.

UI direction: an editorial research desk, warm paper, ink typography, rust accent,
compact document rail, spacious report, and visible source provenance. CSS uses
system fonts and local assets. Small screens stack the desk into one column.
