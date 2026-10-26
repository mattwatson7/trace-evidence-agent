import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from trace.server import Handler
from trace.server import SLOTS


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def post(self, data, headers=None):
        return self.request('POST', '/api/investigate', json.dumps(data), headers or {'Content-Type': 'application/json'})

    def test_health(self):
        status, headers, body = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['status'], 'ok')
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')

    def test_static_assets(self):
        for path, content_type in [('/', 'text/html'), ('/app.js', 'text/javascript'),
                                   ('/style.css', 'text/css'), ('/favicon.svg', 'image/svg+xml')]:
            with self.subTest(path=path):
                status, headers, body = self.request('GET', path)
                self.assertEqual(status, 200)
                self.assertIn(content_type, headers['Content-Type'])
                self.assertTrue(body)

    def test_unknown_and_traversal_paths(self):
        for path in ['/missing', '/trace/engine.py', '/.git/config', '/../README.md', '/%2e%2e/README.md']:
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_demo_can_be_investigated(self):
        status, _, body = self.request('GET', '/api/demo')
        self.assertEqual(status, 200)
        demo = json.loads(body)
        status, _, body = self.post({'question': demo['questions'][0], 'documents': demo['documents']})
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertEqual(report['status'], 'complete')
        self.assertGreater(len(report['evidence']), 2)
        self.assertTrue(report['discrepancies'])

    def test_schema_rejection(self):
        for data in [[], None, {}, {'question': 5, 'documents': []},
                     {'question': 'latency', 'documents': [{'name': 'x', 'text': 'x'}], 'model': {}},
                     {'question': 'latency', 'documents': [{'name': 'x', 'text': 'x'}], 'model': 'http://evil'}]:
            with self.subTest(data=data):
                status, _, body = self.post(data)
                self.assertEqual(status, 400)
                self.assertIn('error', json.loads(body))

    def test_bad_json(self):
        self.assertEqual(self.request('POST', '/api/investigate', '{', {'Content-Type': 'application/json'})[0], 400)

    def test_invalid_utf8(self):
        self.assertEqual(self.request('POST', '/api/investigate', b'\xff', {'Content-Type': 'application/json'})[0], 400)

    def test_wrong_content_type(self):
        self.assertEqual(self.request('POST', '/api/investigate', '{}', {'Content-Type': 'text/plain'})[0], 415)

    def test_cross_origin_rejected(self):
        self.assertEqual(self.post({}, {'Content-Type': 'application/json', 'Origin': 'https://evil.example'})[0], 403)

    def test_same_origin_accepted(self):
        status, _, _ = self.post({'question': 'latency', 'documents': [{'name': 'x', 'text': 'Latency is 42 ms.'}]},
                                 {'Content-Type': 'application/json', 'Origin': f'http://127.0.0.1:{self.server.server_port}'})
        self.assertEqual(status, 200)

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.request('GET', '/api/health', headers={'Host': 'evil.example'})[0], 403)

    def test_oversized_body_rejected_before_reading(self):
        self.assertEqual(self.request('POST', '/api/investigate', '{}', {'Content-Type': 'application/json', 'Content-Length': '3000000'})[0], 413)

    def test_negative_length(self):
        self.assertEqual(self.request('POST', '/api/investigate', None, {'Content-Type': 'application/json', 'Content-Length': '-1'})[0], 400)

    def test_chunked_request_rejected(self):
        self.assertEqual(self.request('POST', '/api/investigate', '{}', {'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'})[0], 400)

    def test_missing_length(self):
        self.assertEqual(self.request('POST', '/api/investigate', None, {'Content-Type': 'application/json', 'Content-Length': ''})[0], 400)

    def test_unsupported_methods(self):
        for method in ['PUT', 'DELETE', 'PATCH', 'OPTIONS']:
            self.assertEqual(self.request(method, '/api/investigate')[0], 405)

    def test_wrong_post_endpoint(self):
        self.assertEqual(self.request('POST', '/api/health', '{}', {'Content-Type': 'application/json'})[0], 404)

    def test_early_rejections_preserve_http_response(self):
        for _ in range(40):
            self.assertEqual(self.request('POST', '/api/health', '{"payload":"discard me"}', {'Content-Type':'application/json'})[0], 404)
            self.assertEqual(self.request('POST', '/api/investigate', 'discard me', {'Content-Type':'text/plain'})[0], 415)

    def test_head(self):
        status, _, body = self.request('HEAD', '/')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')

    def test_busy_server_is_bounded(self):
        SLOTS.acquire()
        SLOTS.acquire()
        try:
            self.assertEqual(self.post({})[0], 429)
        finally:
            SLOTS.release()
            SLOTS.release()

    def test_json_charset(self):
        data = {'question':'latency', 'documents':[{'name':'a', 'text':'Latency is 8 ms.'}]}
        self.assertEqual(self.post(data, {'Content-Type':'application/json; charset=utf-8'})[0], 200)

    def test_surrogates_rejected(self):
        for data in [{'question':'latency', 'documents':[{'name':'a', 'text':'\ud800'}]},
                     {'question':'latency\ud800', 'documents':[{'name':'a', 'text':'Latency is 2 ms.'}]}]:
            self.assertEqual(self.post(data)[0], 400)

    def test_no_server_error_after_invalid_request(self):
        self.post(None)
        self.assertEqual(self.request('GET', '/api/health')[0], 200)
