import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateCollection, reportMarkdown, parseHistory} from '../web/app.js';

test('valid source collection and empty workspace', () => {
  assert.equal(validateCollection([{name:'a', text:'A note.'}]).length, 1);
  assert.deepEqual(validateCollection([], true), []);
});

test('collection boundaries, binary content and duplicates', () => {
  for (const docs of [null, [], {}, [null], [{name:'a', text:''}], [{name:4, text:'a'}],
    [{name:'a', text:'\x00abc'}], [{name:'a', text:'x'.repeat(100001)}],
    [{name:'a', text:'ok'}, {name:' A ', text:'also'}],
    Array.from({length:13}, (_,i) => ({name:String(i), text:'abc'})),
    Array.from({length:4}, (_,i) => ({name:String(i), text:'x'.repeat(100000)}))]) {
    assert.throws(() => validateCollection(docs));
  }
});

test('Unicode source is accepted', () => {
  assert.equal(validateCollection([{name:'Café.md', text:'日本語 — hello 👋'}]).length, 1);
});

test('Markdown export preserves evidence, discrepancies, provenance, warnings and execution', () => {
  const result = reportMarkdown({question:'Why?', mode:'extractive', source_count:2,
    summary:'Two sources disagree.', warning:'Model unavailable.',
    evidence:[{source:'Notes.md', quote:'Exact sentence.\nSecond line.', line:8, id:'abc-42'}],
    discrepancies:[{metric:'Latency', values:['2 ms','4 ms'], evidence_ids:['abc-42','def-80'], note:'Check scope.'}],
    steps:[{tool:'search', detail:'Searched documents.'}], followups:['Repeat the test.']});
  for (const value of ['Why?', '> Exact sentence.', '> Second line.', 'line 8', 'abc-42', '2 ms vs 4 ms', 'Check scope.', 'Model unavailable.', 'search: Searched documents.', 'Repeat the test.']) assert.ok(result.includes(value), value);
});

test('Markdown export includes labeled local AI synthesis and citations', () => {
  const result = reportMarkdown({question:'Why?', mode:'ollama', source_count:1, summary:'Evidence.', evidence:[], discrepancies:[], steps:[], followups:[], synthesis:{summary:'Generated answer', citations:['abc-42'], model:'qwen3:4b'}});
  assert.ok(result.includes('## Local AI synthesis'));
  assert.ok(result.includes('Citations: abc-42'));
  assert.ok(result.includes('factual accuracy'));
});

test('corrupt, incompatible and oversized history is ignored safely', () => {
  for (const value of ['{', 'null', '{}', '[null]', JSON.stringify([{documents:[{name:'a',text:'okay'}],date:'2026-10-26',report:{question:'q',evidence:[{id:'1',source:'a',quote:'okay'}],steps:[],discrepancies:[],followups:[]}}])]) {
    assert.deepEqual(parseHistory(value), []);
  }
});

test('valid history is restored and bounded to eight', () => {
  const record = {date:'2026-10-26T00:00:00Z',documents:[{name:'a',text:'Latency is 2 ms.'}],report:{question:'latency',status:'complete',mode:'extractive',source_count:1,elapsed_ms:2,summary:'Found evidence.',warning:null,evidence:[{id:'a-0',source:'a',quote:'Latency is 2 ms.',line:1,offset:0,document_index:0,matched_terms:['latency']}],steps:[{tool:'search',title:'Search',detail:'Searched.'}],discrepancies:[],followups:['Review.']}};
  assert.equal(parseHistory(JSON.stringify(Array(10).fill(record))).length,8);
  for (const bad of [{...record, date:'invalid'}, {...record,report:{...record.report,evidence:[{...record.report.evidence[0],document_index:9}]}}, {...record,report:{...record.report,steps:[null]}}]) assert.deepEqual(parseHistory(JSON.stringify([bad])),[]);
});

test('history provenance uses browser UTF-16 offsets after emoji', () => {
  const record = {date:'2026-10-26T00:00:00Z',documents:[{name:'Emoji.md',text:'👋\nLatency is 2 ms.'}],report:{question:'latency',status:'complete',mode:'extractive',source_count:1,elapsed_ms:2,summary:'Found evidence.',warning:null,evidence:[{id:'a-2',source:'Emoji.md',quote:'Latency is 2 ms.',line:2,offset:2,offset_utf16:3,document_index:0,matched_terms:['latency']}],steps:[],discrepancies:[],followups:[]}};
  assert.equal(parseHistory(JSON.stringify([record])).length,1);
});
