"""Small, deterministic gold-source benchmark; not a semantic quality score."""
import unittest

from trace.demo import DEMO
from trace.engine import investigate


class GoldSourceEvaluation(unittest.TestCase):
    def assertEvidence(self, question, source, fragment):
        result = investigate(question, DEMO['documents'])
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(any(source == hit['source'] and fragment in hit['quote'] for hit in result['evidence']), question)
        for hit in result['evidence']:
            doc = DEMO['documents'][hit['document_index']]
            self.assertEqual(doc['text'][hit['offset']:hit['offset'] + len(hit['quote'])], hit['quote'])

    def test_release_gate(self):
        self.assertEvidence('What is the checkout latency release gate?', '01-launch-brief.md', '500 ms')

    def test_retry_failure(self):
        self.assertEvidence('Why is the retry queue saturated?', '03-incident-notes.md', 'retry queue is saturated')

    def test_owner(self):
        self.assertEvidence('Who is the release owner?', '01-launch-brief.md', 'Avery Chen')

    def test_decision(self):
        self.assertEvidence('What is the decision about the Meridian rollout?', '04-decision-log.md', 'defer')

    def test_environment_conditions(self):
        self.assertEvidence('What used a warm cache and disabled retries?', '02-performance-report.md', 'warm cache')

    def test_comparison_has_both_sources(self):
        result = investigate('Compare checkout latency metrics', DEMO['documents'])
        self.assertTrue(any(item['metric'] == 'checkout latency' and item['values'] == ['420 ms','870 ms'] for item in result['discrepancies']))
        by_id = {hit['id']:hit for hit in result['evidence']}
        for item in result['discrepancies']:
            self.assertTrue(all(id_ in by_id for id_ in item['evidence_ids']))

    def test_no_model_call_without_relevant_evidence(self):
        result = investigate('Jupiter orbital period', DEMO['documents'], model='missing-model')
        self.assertEqual(result['status'], 'insufficient')
        self.assertIsNone(result['warning'])
        self.assertEqual(result['mode'], 'extractive')

    def test_fictional_marker_is_preserved(self):
        self.assertTrue(all('Fictional demo' in doc['text'] for doc in DEMO['documents']))
