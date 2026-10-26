# Trace: a brief you can audit

## Problem

An engineering decision rarely lives in one document. A launch brief defines the
gate, a performance report says things look healthy, and incident notes disagree.
A fluent answer is insufficient unless a reviewer can trace it back to evidence.

Trace explores a small agent workflow for that problem: retrieve, cross-check,
preserve provenance, and produce an inspectable brief. The user stays responsible
for interpreting the evidence and making a decision.

## Demo: a launch that looks ready until you compare the tests

Four fictional documents describe Meridian. One report records checkout latency
of 420 ms and an error rate of 0.6%; a later rehearsal reports 870 ms and 3.8%.
The decision log explains that cache and retry conditions differed and calls for a
controlled repeat test. The evidence supports a review, not a simplistic “one
report is wrong” verdict.

The demo is an executable example, not a hardcoded answer. Changing documents or
questions changes retrieval and discrepancy results. The gold-source evaluation
checks owners, gates, decisions, retry failures, and environmental conditions.

## Agent architecture

The orchestrator has five logged tool phases with a fixed budget. A first BM25
search anchors the investigation. Query expansion broadens it. A comparison request
adds a focused numeric tool over retrieved sources. That tool can reserve paired
quotes so evidence selection does not lose the very measurements being compared.
The final brief contains at most ten passages.

Citations combine a content digest with a character offset. That makes repeated
sentences distinguishable and changes citation identity when a source changes.
The browser highlights the original source span; saved briefs carry snapshots so
their citations survive later collection edits.

Optional Ollama synthesis operates after retrieval. It has no tool execution
capability. Schema and citation validation reject malformed output, but cannot
prove semantic entailment. The UI therefore labels synthesis and keeps original
quotes available. Without a model, the entire investigation remains usable.

## What testing changed

- The first demo integration test found that headings consumed evidence slots.
  Excluding headings improved substantive passage retrieval.
- The same test showed that comparing only the first search's sources missed a
  report discovered through query expansion. The comparison tool now uses both
  retrieval passes and reserves citation pairs.
- Browser cancellation testing caught an old fallback warning overwriting a new
  cancellation message. Restoring the previous report now happens before reporting
  the cancellation outcome.
- Adversarial input tests found that unpaired Unicode surrogates could reach
  citation hashing. The boundary now rejects them as invalid input.
- Saved-history review led to schema and source-span validation before restoring
  a brief, avoiding crashes from incompatible browser data.
- A repeated HTTP check reproduced Windows connection resets when an early error
  left unread request bytes. A bounded drain now preserves the error response.
- Cross-language review found that Python counts Unicode code points while the
  browser slices UTF-16 units. Citations now include both coordinates, with
  regression checks for emoji before a quotation and saved-history restoration.

## Reliability boundaries

Trace abstains when there is no lexical overlap. Partial or incidental overlap can
still retrieve weak evidence; it does not measure calibrated confidence. Numeric
comparison recognizes explicit metric/value/unit statements and does not normalize
units or interpret dates. Different scopes can explain every flagged discrepancy.

The HTTP boundary restricts origins and Host headers, caps requests, limits active
investigations, and serves only fixed asset paths. Source text is rendered as text,
not HTML. The model adapter disables proxies and redirects. These are practical
boundaries for a local prototype, not a production security certification.

## Next experiments

Measure retrieval quality on a larger, separately authored corpus; add a held-out
evaluation set and paraphrase cases. Compare lexical retrieval with hybrid semantic
retrieval. Evaluate model claims for entailment separately from citation validity.
Extend metric extraction only with tested handling of dates, units, and scope.

The main lesson: provenance and failure behavior belong in the product itself.
The execution trail, source viewer, abstention state, and explicit fallback make the
agent easier to evaluate than a polished paragraph alone.
