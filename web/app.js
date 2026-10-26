const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const number = (value) => new Intl.NumberFormat('en').format(value);
const HISTORY_KEY = 'trace.investigations.v1';
const state = {documents: [], history: [], report: null, reportDocs: [], demo: null, controller: null, generation: 0, inspectIndex: null};

export function validateCollection(documents, allowEmpty = false) {
  if (!Array.isArray(documents) || documents.length > 12 || (!allowEmpty && !documents.length)) throw new Error('Add between 1 and 12 sources.');
  const names = new Set();
  let total = 0;
  for (const doc of documents) {
    if (!doc || typeof doc.name !== 'string' || !doc.name.trim() || doc.name.length > 120) throw new Error('Source names need 1–120 characters.');
    if (typeof doc.text !== 'string' || !doc.text.trim() || doc.text.length > 100000) throw new Error('Each source needs 1–100,000 characters of text.');
    if (/[\x00-\x08\x0B\x0C\x0E-\x1F]/.test(doc.name + doc.text)) throw new Error('Use plain text without binary control characters.');
    const key = doc.name.trim().toLowerCase();
    if (names.has(key)) throw new Error(`A source named “${doc.name}” already exists. Use a unique name.`);
    names.add(key);
    total += doc.text.length;
  }
  if (total > 300000) throw new Error('The collection is limited to 300,000 characters.');
  return documents;
}

export function reportMarkdown(report) {
  const lines = ['# Trace / Evidence brief', '', report.question, '', `Mode: ${report.mode} | ${report.evidence.length} passages | ${report.source_count} sources searched`, '', report.summary, ''];
  if (report.warning) lines.push(`Warning: ${report.warning}`, '');
  if (report.synthesis) lines.push('## Local AI synthesis', '', report.synthesis.summary, '', `Model: ${report.synthesis.model}`, `Citations: ${report.synthesis.citations.join(', ')}`, '', 'AI-generated synthesis. Citation validity does not guarantee factual accuracy.', '');
  if (report.discrepancies.length) {
    lines.push('## Numerical discrepancies — review required', '');
    for (const item of report.discrepancies) lines.push(`- ${item.metric}: ${item.values.join(' vs ')} [${item.evidence_ids.join(', ')}]. ${item.note}`);
    lines.push('');
  }
  lines.push('## Evidence', '');
  report.evidence.forEach((hit, i) => lines.push(`### [${i + 1}] ${hit.source} · line ${hit.line}`, '', ...hit.quote.split('\n').map(line => `> ${line}`), '', `Citation ID: ${hit.id}`, ''));
  lines.push('## Execution log', '');
  for (const step of report.steps) lines.push(`- ${step.tool}: ${step.detail}`);
  lines.push('', '## Follow-up', '', ...report.followups.map(item => `- ${item}`), '', 'Trace uses lexical retrieval. These findings are evidence, not a truth verdict.');
  return lines.join('\n');
}

function notice(message) {
  $('#notice').textContent = message;
  $('#notice').hidden = !message;
}

function invalidateReport() {
  state.report = null;
  $('#report').hidden = true;
  $('#empty').hidden = false;
}

function renderSources() {
  $('#source-count').textContent = state.documents.length;
  $('#mobile-count').textContent = state.documents.length;
  $('#collection-size').textContent = `${number(state.documents.reduce((sum, doc) => sum + doc.text.length, 0))} characters`;
  $('#source-list').innerHTML = state.documents.length ? state.documents.map((doc, index) => `<button class="source-item" data-source="${index}" title="${esc(doc.name)}"><span class="source-icon" aria-hidden="true">≡</span><span class="source-copy"><span class="source-name">${esc(doc.name)}</span><span class="source-meta">${number(doc.text.length)} characters · Ready</span></span><span class="source-arrow" aria-hidden="true">↗</span></button>`).join('') : '<p class="blank-sources">Your collection is empty.<br>Add a source or try the demo below.</p>';
  $('#add-source').disabled = state.documents.length >= 12;
}

function readHistory() {
  try { return parseHistory(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

export function parseHistory(serialized) {
  try {
    if (typeof serialized !== 'string' || serialized.length > 4000000) return [];
    const records = JSON.parse(serialized);
    if (!Array.isArray(records)) return [];
    return records.filter(record => {
      try {
        validateCollection(record.documents);
        const r = record.report;
        if (typeof record.date !== 'string' || !Number.isFinite(Date.parse(record.date)) || !r ||
            typeof r.question !== 'string' || typeof r.summary !== 'string' || !['complete','insufficient'].includes(r.status) ||
            !['extractive','ollama'].includes(r.mode) || !Number.isInteger(r.source_count) || !Number.isFinite(r.elapsed_ms) ||
            (r.warning !== null && typeof r.warning !== 'string') ||
            !Array.isArray(r.evidence) || r.evidence.length > 10) return false;
        const validEvidence = r.evidence.every(e => e && typeof e.id === 'string' && typeof e.source === 'string' && typeof e.quote === 'string' &&
          Number.isInteger(e.line) && e.line >= 1 && Number.isInteger(e.offset) && e.offset >= 0 &&
          Number.isInteger(e.document_index) && record.documents[e.document_index]?.name === e.source &&
          record.documents[e.document_index].text.slice(e.offset_utf16 ?? e.offset, (e.offset_utf16 ?? e.offset) + e.quote.length) === e.quote &&
          Array.isArray(e.matched_terms) && e.matched_terms.every(t => typeof t === 'string'));
        const ids = new Set(r.evidence.map(e => e.id));
        const validIds = list => Array.isArray(list) && list.every(id => typeof id === 'string' && ids.has(id));
        return validEvidence && Array.isArray(r.steps) && r.steps.every(s => s && ['tool','title','detail'].every(k => typeof s[k] === 'string')) &&
          Array.isArray(r.discrepancies) && r.discrepancies.every(d => d && typeof d.metric === 'string' && typeof d.note === 'string' &&
            Array.isArray(d.values) && d.values.length === 2 && d.values.every(v => typeof v === 'string') && validIds(d.evidence_ids)) &&
          Array.isArray(r.followups) && r.followups.every(f => typeof f === 'string') &&
          (!r.synthesis || (typeof r.synthesis.summary === 'string' && typeof r.synthesis.model === 'string' && validIds(r.synthesis.citations)));
      } catch { return false; }
    }).slice(0, 8);
  } catch { return []; }
}

function renderHistory() {
  $('#clear-history').disabled = !state.history.length;
  $('#history-list').innerHTML = state.history.length ? state.history.map((record, index) => `<button class="history-item" data-history="${index}">${esc(record.report.question)}<span>${esc(new Date(record.date).toLocaleDateString(undefined, {month:'short', day:'numeric'}))} · ${record.report.evidence.length} passages</span></button>`).join('') : '<p class="muted small">Your next question starts a trail.</p>';
}

function saveHistory(report, documents) {
  state.history.unshift({date: new Date().toISOString(), report, documents: structuredClone(documents)});
  state.history = state.history.slice(0, 8);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history)); }
  catch { notice('Investigation complete. Browser storage is unavailable or full, so this run could not be saved. Export your brief to keep it.'); }
  renderHistory();
}

function inspect(documents, index, evidence = null, removable = false) {
  const doc = documents[index];
  if (!doc) return;
  state.inspectIndex = removable ? index : null;
  $('#inspect-title').textContent = doc.name;
  $('#inspect-location').textContent = evidence ? `Citation ${evidence.id} · line ${evidence.line} · exact source quotation` : `${number(doc.text.length)} characters · original source`;
  const container = $('#inspect-text');
  container.replaceChildren();
  const offset = evidence?.offset_utf16 ?? evidence?.offset;
  if (evidence && doc.text.slice(offset, offset + evidence.quote.length) === evidence.quote) {
    container.append(document.createTextNode(doc.text.slice(0, offset)));
    const mark = document.createElement('mark');
    mark.textContent = evidence.quote;
    container.append(mark, document.createTextNode(doc.text.slice(offset + evidence.quote.length)));
  } else container.textContent = doc.text;
  $('#remove-source').hidden = !removable;
  $('#inspect-dialog').showModal();
  if (evidence) container.querySelector('mark')?.scrollIntoView({block: 'center'});
  else container.scrollTop = 0;
}

function inspectEvidence(id) {
  const hit = state.report?.evidence.find(item => item.id === id);
  if (hit) inspect(state.reportDocs, hit.document_index, hit);
}

function renderReport(report) {
  state.report = report;
  const citations = (ids, values) => ids.map((id, index) => `<button data-citation="${esc(id)}">${esc(values?.[index] ?? `[${report.evidence.findIndex(e => e.id === id) + 1}]`)} ↗</button>`).join('');
  const conflicts = report.discrepancies.length ? `<div class="discrepancy"><h3>↗ ${report.discrepancies.length} numerical discrepancies to review</h3><p>Different values are a signal to investigate. Dates and measurement conditions may explain the difference.</p>${report.discrepancies.map(item => `<div class="discrepancy-row"><strong>${esc(item.metric)}</strong>${citations(item.evidence_ids, item.values)}</div>`).join('')}</div>` : '';
  const synthesis = report.synthesis ? `<div class="synthesis"><h3>Local AI synthesis · ${esc(report.synthesis.model)}</h3><p>${esc(report.synthesis.summary)}</p>${citations(report.synthesis.citations)}<p><small>AI-generated. Citation IDs are validated; factual accuracy still requires review.</small></p></div>` : '';
  $('#report').innerHTML = `<div class="report-top">
    <span class="eyebrow">YOUR INVESTIGATION / EVIDENCE BRIEF</span>
    <button id="export" class="text-button">Export brief ↓</button>
    </div>
    <h2 class="report-title">${esc(report.question)}</h2>
    <div class="report-meta">
    <span class="badge ${report.status === 'insufficient' ? 'amber' : ''}">${report.status === 'insufficient' ? 'MORE EVIDENCE NEEDED' : 'INVESTIGATION COMPLETE'}</span>
    <span>${report.evidence.length} passages</span>
    <span>${report.source_count} sources searched</span>
    <span>${report.elapsed_ms} ms · ${report.mode === 'ollama' ? 'Local AI' : 'Extractive'}</span>
    </div>
    <p class="report-summary">${esc(report.summary)}</p>${synthesis}${conflicts}<div class="report-layout">
    <div>
    <div class="section-heading">
    <h3>The evidence</h3>
    <span>EVERY QUOTE, A SOURCE</span>
    </div>${report.evidence.length ? `<div class="report-filter">
    <button data-filter="all" aria-pressed="true">All sources</button>${[...new Set(report.evidence.map(e => e.source))].map(source => `<button data-filter="${esc(source)}" aria-pressed="false">${esc(source.replace(/^\d+-/, '').replace(/\.(md|txt)$/i, ''))}</button>`).join('')}</div>` : '<p class="muted small">No matching passages. Try a more specific question or add a relevant source.</p>'}<div class="evidence-list">${report.evidence.map((hit, index) => `<article class="evidence-card" data-evidence-source="${esc(hit.source)}">
    <div class="evidence-card-top">
    <span class="citation">[${String(index + 1).padStart(2,'0')}]</span>
    <button class="source-link" data-citation="${esc(hit.id)}">${esc(hit.source)} · L${hit.line}</button>
    </div>
    <blockquote>${esc(hit.quote)}</blockquote>
    <div class="evidence-card-footer">
    <span>Exact quotation · ${hit.reason ? esc(hit.reason) : `${hit.matched_terms.length} matched terms`}</span>
    <button data-citation="${esc(hit.id)}">View in source ↗</button>
    </div>
    </article>`).join('')}</div>
    <div class="followups">
    <h3>KEEP PULLING THE THREAD</h3>${report.followups.map(item => `<p>↗ &nbsp; ${esc(item)}</p>`).join('')}</div>
    </div>
    <aside class="execution" aria-label="Execution log">
    <h3>THE AGENT’S TRAIL</h3>
    <div class="execution-steps">${report.steps.map(step => `<div class="step">
    <strong>${esc(step.title)}</strong>
    <p>${esc(step.detail)}</p>
    </div>`).join('')}</div>
    <p class="execution-note">${report.mode === 'ollama' ? 'A local language model synthesized the retrieved evidence.' : 'No language model used. This run used lexical retrieval and verbatim evidence.'}<br>
    <br>Relevance is not certainty.<br>Always check the receipts.</p>
    </aside>
    </div>`;
  $('#report').hidden = false;
  $('#empty').hidden = true;
  if (report.warning) notice(report.warning);
}

function setBusy(busy) {
  $('#run').hidden = busy;
  $('#cancel').hidden = !busy;
  $('#loading').hidden = !busy;
  $('#question').disabled = busy;
  for (const id of ['load-demo', 'add-source', 'upload', 'model']) $("#" + id).disabled = busy || (id === 'add-source' && state.documents.length >= 12);
  $('#investigate-form').setAttribute('aria-busy', String(busy));
}

async function investigate(event) {
  event.preventDefault();
  if (state.controller) return;
  notice('');
  try { validateCollection(state.documents); }
  catch (error) { notice(`${error.message} Use “Load demo collection” to get started.`); return; }
  const question = $('#question').value.trim();
  if (!question || question.length > 1000 || !/[\p{L}\p{N}]/u.test(question)) { notice('Ask a question with a meaningful search term (up to 1,000 characters).'); return; }
  const model = $('#model').value.trim();
  if (model && !/^[\w][\w.:-]{0,119}$/.test(model)) { notice('Use a local model name, such as qwen3:4b.'); return; }
  const documents = structuredClone(state.documents);
  const generation = ++state.generation;
  const controller = new AbortController();
  state.controller = controller;
  const timer = setTimeout(() => controller.abort('timeout'), 60000);
  $('#report').hidden = true;
  $('#empty').hidden = true;
  setBusy(true);
  try {
    const response = await fetch('/api/investigate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, documents, ...(model ? {model} : {})}), signal:controller.signal});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
    if (generation !== state.generation) return;
    state.reportDocs = documents;
    renderReport(result);
    saveHistory(result, documents);
    $('#report').setAttribute('tabindex', '-1');
    $('#report').focus({preventScroll: true});
  } catch (error) {
    if (generation !== state.generation) return;
    if (state.report) renderReport(state.report); else $('#empty').hidden = false;
    notice(controller.signal.aborted ? (controller.signal.reason === 'timeout' ? 'The investigation timed out. Try extractive mode or a smaller collection.' : 'Investigation cancelled. Your sources are still here.') : `Could not investigate: ${error.message} Make sure the local Trace server is running.`);
  } finally {
    clearTimeout(timer);
    if (generation === state.generation) { state.controller = null; setBusy(false); }
  }
}

async function loadDemo() {
  if (!state.demo) {
    const response = await fetch('/api/demo');
    if (!response.ok) throw new Error('The demo could not load. Check the local server.');
    state.demo = await response.json();
  }
  state.documents = structuredClone(state.demo.documents);
  invalidateReport();
  renderSources();
  $('#question').value = state.demo.questions[0];
  notice('Meridian demo loaded: four fictional sources. Run an investigation to follow the evidence.');
  $('#question').focus();
}

function downloadBrief() {
  if (!state.report) return;
  const url = URL.createObjectURL(new Blob([reportMarkdown(state.report)], {type:'text/markdown;charset=utf-8'}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'trace-evidence-brief.md';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function init() {
  state.history = readHistory();
  renderSources();
  renderHistory();
  $('#investigate-form').addEventListener('submit', investigate);
  $('#question').addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); $('#investigate-form').requestSubmit(); } });
  $('#cancel').addEventListener('click', () => state.controller?.abort('cancelled'));
  $('#model').addEventListener('input', () => { $('#mode-caption').textContent = $('#model').value.trim() ? 'Local AI requested' : 'Extractive mode'; });
  $('#load-demo').addEventListener('click', () => loadDemo().catch(error => notice(error.message)));
  $('#about').addEventListener('click', () => $('#about-dialog').showModal());
  $('#add-source').addEventListener('click', () => { $('#source-form').reset(); $('#source-error').textContent = ''; $('#source-dialog').showModal(); });
  $('#source-form').addEventListener('submit', event => {
    event.preventDefault();
    const doc = {name: $('#source-name').value.trim(), text: $('#source-text').value};
    try {
      validateCollection([...state.documents, doc]);
      state.documents.push(doc);
      invalidateReport(); renderSources(); $('#source-dialog').close(); notice(`Added ${doc.name}.`);
    } catch (error) { $('#source-error').textContent = error.message; }
  });
  $('#upload').addEventListener('click', () => $('#file-input').click());
  $('#file-input').addEventListener('change', async event => {
    const input = event.target;
    try {
      const files = [...input.files];
      if (!files.length) return;
      if (files.length + state.documents.length > 12) throw new Error('The collection supports up to 12 sources.');
      const docs = [];
      for (const file of files) {
        if (!/\.(txt|md)$/i.test(file.name)) throw new Error('Upload .txt or .md files only.');
        if (file.size > 400000) throw new Error(`${file.name} is too large. Use up to 100,000 characters per source.`);
        let text;
        try { text = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer()); }
        catch { throw new Error(`${file.name} is not valid UTF-8 text.`); }
        docs.push({name:file.name, text});
      }
      if (state.controller) throw new Error('Wait for the current investigation before adding files.');
      validateCollection([...state.documents, ...docs]);
      state.documents.push(...docs);
      invalidateReport(); renderSources(); notice(`Added ${docs.length} source${docs.length === 1 ? '' : 's'}.`);
    } catch (error) { notice(error.message); }
    finally { input.value = ''; }
  });
  $('#remove-source').addEventListener('click', () => {
    if (state.controller || state.inspectIndex === null) return;
    state.documents.splice(state.inspectIndex, 1);
    $('#inspect-dialog').close(); invalidateReport(); renderSources(); notice('Source removed from this collection. Saved investigations retain their own source snapshots.');
  });
  $('#clear-history').addEventListener('click', () => {
    try { localStorage.removeItem(HISTORY_KEY); state.history = []; renderHistory(); notice('Saved investigation history cleared from this browser.'); }
    catch { notice('Browser storage is unavailable. History could not be cleared.'); }
  });
  document.addEventListener('click', async event => {
    const target = event.target.closest('button');
    if (!target) return;
    if (target.dataset.close) document.getElementById(target.dataset.close)?.close();
    if (target.dataset.source !== undefined && !state.controller) inspect(state.documents, Number(target.dataset.source), null, true);
    if (target.dataset.citation) inspectEvidence(target.dataset.citation);
    if (target.dataset.history !== undefined && !state.controller) {
      const record = state.history[Number(target.dataset.history)];
      state.documents = structuredClone(record.documents); state.reportDocs = structuredClone(record.documents);
      $('#question').value = record.report.question; renderSources(); notice('Saved investigation restored with its original sources.'); renderReport(record.report);
    }
    if (target.dataset.question) {
      if (state.controller) return;
      try { if (!state.documents.length) await loadDemo(); $('#question').value = target.dataset.question; $('#question').focus(); }
      catch (error) { notice(error.message); }
    }
    if (target.dataset.filter !== undefined) {
      for (const button of document.querySelectorAll('[data-filter]')) button.setAttribute('aria-pressed', String(button === target));
      for (const card of document.querySelectorAll('[data-evidence-source]')) card.hidden = target.dataset.filter !== 'all' && card.dataset.evidenceSource !== target.dataset.filter;
    }
    if (target.id === 'export') downloadBrief();
  });
  try {
    const response = await fetch('/api/health');
    if (!response.ok) throw new Error('Unavailable');
  } catch { $('#connection').textContent = 'Server unavailable'; notice('Start the local server with python -m trace.server, then reload this page.'); }
}

if (typeof document !== 'undefined') init();
