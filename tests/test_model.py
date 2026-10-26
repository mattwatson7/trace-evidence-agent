import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from trace.engine import investigate
from trace.model import synthesize


class FakeModel(BaseHTTPRequestHandler):
    reply = {}
    request_body = None
    raw = None
    status = 200
    leaked = False

    def do_POST(self):
        FakeModel.request_body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        data = FakeModel.raw if FakeModel.raw is not None else json.dumps({'response': json.dumps(FakeModel.reply)}).encode()
        self.send_response(FakeModel.status)
        if FakeModel.status == 302:
            self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/leak')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        FakeModel.leaked = True
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeModel)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        FakeModel.raw = None
        FakeModel.status = 200
        FakeModel.leaked = False
        self.endpoint = patch('trace.model.ENDPOINT', f'http://127.0.0.1:{self.server.server_port}/api/generate')
        self.endpoint.start()
        self.addCleanup(self.endpoint.stop)
        self.evidence = [{'id': 'known-1', 'quote': 'Latency is 400 ms.', 'source': 'a'}]

    def test_valid_local_synthesis(self):
        FakeModel.reply = {'summary': 'Reported latency is 400 ms.', 'citations': ['known-1']}
        result = synthesize('latency?', self.evidence, 'local-model')
        self.assertEqual(result['citations'], ['known-1'])
        self.assertFalse(FakeModel.request_body['stream'])
        self.assertEqual(FakeModel.request_body['format'], 'json')
        self.assertIn('untrusted', FakeModel.request_body['system'].lower())

    def test_invalid_citations_and_shape_rejected(self):
        for reply in [{}, [], {'summary': 'x', 'citations': ['invented']},
                      {'summary': '', 'citations': ['known-1']},
                      {'summary': 'x', 'citations': []},
                      {'summary': 'x', 'citations': [42]},
                      {'summary': '\ud800', 'citations': ['known-1']},
                      {'summary': 'x' * 5001, 'citations': ['known-1']}]:
            with self.subTest(reply=str(reply)[:80]):
                FakeModel.reply = reply
                with self.assertRaises(ValueError):
                    synthesize('q', self.evidence, 'local-model')

    def test_bad_model_name(self):
        for name in ['', 'https://remote/model', '../secret', 'a' * 121, 42]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                synthesize('q', self.evidence, name)

    def test_invalid_model_falls_back_to_evidence(self):
        FakeModel.reply = {'summary': 'unverified', 'citations': ['invented']}
        result = investigate('latency', [{'name': 'a', 'text': 'Latency is 400 ms.'}], 'local-model')
        self.assertEqual(result['mode'], 'extractive')
        self.assertIsNotNone(result['warning'])
        self.assertTrue(result['evidence'])

    def test_connection_failure_falls_back(self):
        with patch('trace.model.synthesize', side_effect=OSError('not running')):
            result = investigate('latency', [{'name': 'a', 'text': 'Latency is 400 ms.'}], 'local-model')
        self.assertEqual(result['mode'], 'extractive')
        self.assertIn('not running', result['warning'])

    def test_invalid_envelopes(self):
        for raw in [b'not json', b'[]', b'{}', b'{"response":42}', b'{"response":"[]"}', b'\xff']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                FakeModel.raw = raw
                synthesize('q', self.evidence, 'local-model')

    def test_size_limit(self):
        FakeModel.raw = b' ' * 1000001
        with self.assertRaises(ValueError):
            synthesize('q', self.evidence, 'local-model')

    def test_redirect_cannot_send_documents_elsewhere(self):
        FakeModel.status = 302
        with self.assertRaises(ValueError):
            synthesize('q', self.evidence, 'local-model')
        self.assertFalse(FakeModel.leaked)

    def test_model_http_error_falls_back(self):
        FakeModel.status = 503
        result = investigate('latency', [{'name':'a','text':'Latency is 2 ms.'}], 'local-model')
        self.assertEqual(result['mode'], 'extractive')
        self.assertIsNotNone(result['warning'])

    def test_successful_model_run_is_labeled(self):
        from trace.engine import chunk_documents
        docs = [{'name':'a','text':'Latency is 2 ms.'}]
        id_ = chunk_documents(docs)[0]['id']
        FakeModel.reply = {'summary':'Reported latency is 2 ms.', 'citations':[id_]}
        result = investigate('latency', docs, 'local-model')
        self.assertEqual(result['mode'], 'ollama')
        self.assertEqual(result['synthesis']['citations'], [id_])
        self.assertIsNone(result['warning'])
