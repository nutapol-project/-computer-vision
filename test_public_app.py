import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from public_app import Registry, public_handler


class PublicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = Registry(self.temp.name)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), public_handler(self.registry))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.registry.close()
        self.temp.cleanup()

    def cookie(self):
        with urlopen(self.url) as r:
            cookie = r.headers['Set-Cookie']
            self.assertIn('HttpOnly; Secure; SameSite=Lax', cookie)
            self.assertNotIn('value="camera"', r.read().decode())
            return cookie.split(';')[0]

    def get(self, path, cookie):
        return urlopen(Request(self.url+path, headers={'Cookie': cookie}))

    def test_sessions_and_history_are_isolated(self):
        a, b = self.cookie(), self.cookie()
        self.assertNotEqual(a, b)
        engine = self.registry.sessions[a.split('=',1)[1]]
        engine.jpeg = b'private frame'
        with engine.db() as db:
            db.execute("INSERT INTO events VALUES ('secret','now','waste',1,'Organic',0.9)")
        with self.get('/api/events', a) as r:
            self.assertEqual(len(json.load(r)), 1)
        with self.get('/api/events', b) as r:
            self.assertEqual(json.load(r), [])
        with self.get('/api/frame', b) as r:
            self.assertEqual(r.status, 204)
        with self.get('/api/export', b) as r:
            self.assertNotIn(b'secret', r.read())

    def test_camera_cross_origin_and_anonymous_are_blocked(self):
        cookie = self.cookie()
        for payload, extra, status in [({'mode':'waste','source':'camera'}, {},400),
            ({'mode':'waste','source':'browser'}, {'Origin':'https://evil.example'},403)]:
            req = Request(self.url+'/api/start', data=json.dumps(payload).encode(),
                headers={'Cookie':cookie,'Content-Type':'application/json',**extra})
            with self.assertRaises(HTTPError) as e:
                urlopen(req)
            self.assertEqual(e.exception.code,status)
        with self.assertRaises(HTTPError) as e:
            urlopen(self.url+'/api/events')
        self.assertEqual(e.exception.code,401)

    def test_capacity_and_expiry(self):
        import time
        a, ea = self.registry.resolve(create=True)
        b, eb = self.registry.resolve(create=True)
        _, ec = self.registry.resolve(create=True)
        with patch.object(ea, 'worker') as wa, patch.object(eb,'worker') as wb:
            wa.is_alive.return_value = wb.is_alive.return_value = True
            with self.assertRaisesRegex(ValueError,'2'):
                ec.start('waste','browser')
        ea.last_seen = time.monotonic()-301
        self.registry.sweep()
        self.assertNotIn(a,self.registry.sessions)
        self.assertIn(b,self.registry.sessions)


if __name__ == '__main__':
    unittest.main()
