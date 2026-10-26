"""Bounded lexical investigation. No generated claims in extractive mode."""

from collections import Counter
import hashlib
import math
import re
import time

STOP = set('a an the is are was were be been being of for in on at to and or but as by with from this that it its do does did what why how when which who can could should would will we our their they about tell me please have has had not there any all than then into over under'.split())
EXPANSIONS = {
    'block': ['blocked', 'blocker', 'risk', 'gate'],
    'launch': ['release', 'rollout', 'ship'],
    'latency': ['response', 'p95', 'performance'],
    'error': ['failure', 'retry', 'incident'],
    'cost': ['budget', 'spend', 'price'],
    'decision': ['recommendation', 'approved', 'defer'],
    'metric': ['latency', 'error', 'rate', 'measurement'],
    'blocking': ['blocked', 'blocker', 'risk', 'gate'],
}


def tokens(text):
    words = re.findall(r'[^\W_]+', text.casefold(), re.UNICODE)
    return [w[:-1] if w.endswith('s') and len(w) > 4 else w for w in words if w not in STOP]


def validate_documents(documents):
    if not isinstance(documents, list) or not 1 <= len(documents) <= 12:
        raise ValueError('Add between 1 and 12 documents.')
    names = set()
    for doc in documents:
        if not isinstance(doc, dict):
            raise ValueError('Each document needs a name and text.')
        name, text = doc.get('name'), doc.get('text')
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError('Document names must contain 1–120 characters.')
        if not isinstance(text, str) or not text.strip() or len(text) > 100000:
            raise ValueError('Each document needs 1–100,000 characters of text.')
        if any(ord(c) < 32 and c not in '\n\r\t' for c in text + name):
            raise ValueError('Use plain UTF-8 text without binary control characters.')
        if any(0xD800 <= ord(c) <= 0xDFFF for c in text + name):
            raise ValueError('Source text must contain valid Unicode characters.')
        if name.strip().casefold() in names:
            raise ValueError('Document names must be unique.')
        names.add(name.strip().casefold())
    if sum(len(d['text']) for d in documents) > 300000:
        raise ValueError('The collection is limited to 300,000 characters.')
    return documents


def chunk_documents(documents):
    chunks = []
    for index, doc in enumerate(documents):
        cursor = 0
        previous_position = 0
        utf16_position = 0
        digest = hashlib.sha256((doc['name'] + '\0' + doc['text']).encode()).hexdigest()[:10]
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', doc['text']):
            if not sentence.strip():
                continue
            offset = doc['text'].find(sentence, cursor)
            cursor = offset + len(sentence)
            for start in range(0, len(sentence), 650):
                raw = sentence[start:start + 650]
                quote = raw.strip()
                if not quote:
                    continue
                pos = offset + start + len(raw) - len(raw.lstrip())
                utf16_position += len(doc['text'][previous_position:pos].encode('utf-16-le')) // 2
                previous_position = pos
                chunks.append({'id': f'{digest}-{pos}', 'source': doc['name'],
                               'document_index': index, 'quote': quote,
                               'line': doc['text'].count('\n', 0, pos) + 1,
                               'offset': pos,
                               'offset_utf16': utf16_position})
    return chunks


def search(query, chunks, limit=8):
    terms = set(tokens(query))
    if not terms or not chunks:
        return []
    bags = [Counter(tokens(c['quote'])) for c in chunks]
    lengths = [sum(bag.values()) for bag in bags]
    average = sum(lengths) / max(1, len(lengths)) or 1
    frequencies = Counter(term for bag in bags for term in bag)
    hits = []
    for chunk, bag, length in zip(chunks, bags, lengths):
        if chunk['quote'].lstrip().startswith('#'):
            continue  # A document title is context, not a substantive finding.
        overlap = terms.intersection(bag)
        if not overlap:
            continue
        score = 0
        for term in overlap:
            frequency = bag[term]
            idf = math.log(1 + (len(chunks) - frequencies[term] + .5) / (frequencies[term] + .5))
            score += idf * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * length / average))
        hits.append({**chunk, 'score': round(score, 4), 'matched_terms': sorted(overlap)})
    return sorted(hits, key=lambda hit: (-hit['score'], hit['document_index'], hit['offset']))[:limit]


def discrepancies(evidence):
    # Deliberately narrow: compare explicit "metric is value unit" statements only.
    pattern = re.compile(r'([\w][\w -]{1,70}?)\s+(?:is|was|=|:)\s*(\d+(?:\.\d+)?)\s*(ms|%|seconds|users|requests|days|hours|dollars)(?=\s|[.,;]|$)', re.I)
    observations = {}
    found = []
    for item in evidence:
        for match in pattern.finditer(item['quote']):
            metric = re.sub(r'^(?:the|a|an)\s+', '', match[1].lower().strip())
            key = (metric, match[3].lower())
            previous = observations.get(key)
            if previous and float(previous[0]) != float(match[2]) and previous[1]['source'] != item['source']:
                pair = [previous[1]['id'], item['id']]
                if not any(d['metric'] == metric for d in found):
                    found.append({'metric': metric, 'values': [f'{previous[0]} {key[1]}', f'{match[2]} {key[1]}'],
                                  'evidence_ids': pair,
                                  'note': 'Different reported values. Check dates, scope, and measurement conditions before treating this as a contradiction.'})
            observations[key] = (match[2], item)
    return found


def investigate(question, documents, model=None):
    started = time.perf_counter()
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise ValueError('Ask a question between 1 and 1,000 characters.')
    if any(0xD800 <= ord(c) <= 0xDFFF for c in question):
        raise ValueError('The question must contain valid Unicode characters.')
    if not tokens(question):
        raise ValueError('Include a meaningful search term in your question.')
    validate_documents(documents)
    chunks = chunk_documents(documents)
    base_terms = tokens(question)
    expanded = sorted({term for word in base_terms for term in EXPANSIONS.get(word, [])})
    steps = [{'tool': 'plan', 'title': 'Plan the investigation',
              'detail': f'Identify evidence for: {", ".join(dict.fromkeys(base_terms))}.', 'count': len(base_terms)}]
    first = search(question, chunks, limit=12)
    steps.append({'tool': 'search', 'title': 'Search the collection',
                  'detail': f'BM25 ranked {len(chunks)} passages across {len(documents)} documents; {len(first)} initial matches.', 'count': len(first)})
    more = search(question + ' ' + ' '.join(expanded), chunks, limit=20) if first else []
    # Direct matches take priority. Expansion cannot create an answer from zero evidence.
    candidates = list({hit['id']: hit for hit in first + more}.values())
    selected = []
    # Comparison questions trigger a dedicated numerical cross-check over sources
    # found by retrieval. Keep the actual paired quotes in the evidence budget.
    compare = bool(re.search(r'metric|disagree|differ|discrepanc|conflict|compar', question, re.I))
    retrieved_sources = {hit['source'] for hit in candidates}
    comparison_hits = [c for c in chunks if c['source'] in retrieved_sources] if compare else candidates
    pairs = discrepancies(comparison_hits)[:3]
    needed = {id_ for pair in pairs for id_ in pair['evidence_ids']}
    for chunk in chunks:
        if chunk['id'] in needed:
            selected.append({**chunk, 'score': 0, 'matched_terms': sorted(set(tokens(chunk['quote'])) & set(base_terms)), 'reason': 'numerical cross-check'})
    for source in dict.fromkeys(hit['source'] for hit in first):
        if len(selected) < 10 and source not in {hit['source'] for hit in selected}:
            selected.append(next(hit for hit in first if hit['source'] == source))
    for hit in candidates:
        if hit['id'] not in {h['id'] for h in selected} and len(selected) < 10:
            selected.append(hit)
    steps.append({'tool': 'expand', 'title': 'Cross-check other sources',
                  'detail': f'Expanded terms: {", ".join(expanded) if expanded else "original terms retained"}. Selected {len(selected)} passages with source diversity.', 'count': len(selected)})
    conflicts = discrepancies(selected)
    steps.append({'tool': 'verify', 'title': 'Verify provenance & compare values',
                  'detail': f'All {len(selected)} quotes verified against source text. {len(conflicts)} numerical discrepancies flagged for review.', 'count': len(conflicts)})
    summary = ('The collection does not contain enough matching evidence to answer this question. Add a relevant source or use more specific terms.'
               if not selected else
               f'Found {len(selected)} relevant passages across {len(set(h["source"] for h in selected))} sources. '
               + (f'{len(conflicts)} numerical discrepancies need review. ' if conflicts else '')
               + 'The findings below are verbatim evidence, ranked by lexical relevance. They are not a truth verdict.')
    result = {'question': question.strip(), 'status': 'complete' if selected else 'insufficient',
              'mode': 'extractive', 'summary': summary, 'evidence': selected,
              'discrepancies': conflicts, 'steps': steps,
              'source_count': len(documents), 'passage_count': len(chunks),
              'followups': ['Check the dates and scope of any different reported values.',
                            'Add the decision log or latest measurement to close evidence gaps.'] if selected else
                           ['Add documents that directly mention the subject of your question.'],
              'warning': None}
    if model and selected:
        from trace.model import synthesize
        try:
            result['synthesis'] = synthesize(question, selected, model)
            result['mode'] = 'ollama'
        except (ValueError, OSError, TimeoutError) as exc:
            result['warning'] = f'Local AI unavailable or its response failed validation; showing extractive evidence. {str(exc)[:180]}'
    steps.append({'tool': 'compose', 'title': 'Assemble the evidence brief',
                  'detail': 'Local AI synthesis with validated citation IDs.' if result['mode'] == 'ollama' else 'Extractive brief assembled. No language model used.', 'count': len(selected)})
    result['elapsed_ms'] = round((time.perf_counter() - started) * 1000)
    return result
