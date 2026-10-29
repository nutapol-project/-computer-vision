import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from web_app import Counter, Engine, make_handler


def item(tid=1, cls='General'):
    return {'id': tid, 'class': cls, 'confidence': 0.9}


class CountingTests(unittest.TestCase):
    def test_counts_once(self):
        counter = Counter(3)
        self.assertEqual(counter.update([item()]), [])
        self.assertEqual(counter.update([item()]), [])
        self.assertEqual(len(counter.update([item()])), 1)
        self.assertEqual(counter.update([item()]), [])
        counter.update([])
        for _ in range(5):
            self.assertEqual(counter.update([item()]), [])

    def test_requires_consecutive_same_class(self):
        counter = Counter(3)
        counter.update([item()])
        counter.update([])
        counter.update([item()])
        counter.update([item(cls='Organic')])
        self.assertEqual(counter.update([item(cls='Organic')]), [])
        self.assertEqual(len(counter.update([item(cls='Organic')])), 1)
        self.assertEqual(counter.update([item(cls='General')]), [])
        self.assertEqual(counter.pending[1][1], 1)

    def test_no_id_and_multiple_objects(self):
        counter = Counter(2)
        counter.update([item(None), item(1), item(2)])
        self.assertEqual(len(counter.update([item(None), item(1), item(2)])), 2)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = Engine(Path(self.temp.name) / 'missing.pt', Path(self.temp.name) / 'events.db')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.engine))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_initial_state_and_pages(self):
        with urlopen(self.url+'/api/state') as response:
            state = json.load(response)
            self.assertEqual(state['status'], 'idle')
            self.assertFalse(state['model_ready'])
        for path in ['/', '/style.css', '/app.js', '/api/export', '/api/events']:
            with urlopen(self.url+path) as response:
                self.assertEqual(response.status, 200)

    def test_feedback_upload_and_validation(self):
        import io
        from PIL import Image
        buffer = io.BytesIO()
        Image.new('RGB', (40, 30), 'green').save(buffer, format='PNG')
        def submit(payload, category):
            return urlopen(Request(self.url+'/api/feedback', data=payload,
                headers={'Content-Type':'image/png', 'X-Waste-Class':category}))
        with submit(buffer.getvalue(), 'Organic') as response:
            self.assertEqual(response.status, 201)
            record = json.load(response)
        folder = Path(self.temp.name) / 'feedback' / 'Organic'
        self.assertEqual(record['status'], 'pending_review')
        self.assertEqual(json.loads((folder/(record['id']+'.json')).read_text())['class'], 'Organic')
        with Image.open(folder/record['image']) as image:
            self.assertEqual(image.size, (40, 30))
        for payload, category in [(b'not an image','Organic'), (buffer.getvalue(),'../invalid')]:
            with self.assertRaises(HTTPError) as exc:
                submit(payload, category)
            self.assertEqual(exc.exception.code, 400)
        self.assertEqual(len(list(folder.glob('*.jpg'))), 1)

    def test_missing_model_and_cross_origin_rejected(self):
        request = Request(self.url+'/api/start', data=b'{"mode":"waste"}', headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as exc:
            urlopen(request)
        self.assertEqual(exc.exception.code, 400)
        request = Request(self.url+'/api/start', data=b'{}', headers={'Content-Type':'application/json', 'Origin':'http://other.example'})
        with self.assertRaises(HTTPError) as exc:
            urlopen(request)
        self.assertEqual(exc.exception.code, 403)
        self.assertIsNone(self.engine.worker)

    def test_browser_upload_latest_frame_and_session(self):
        import io
        from PIL import Image
        self.engine.state.update(source='browser', session='current', status='starting')
        def jpeg(color, size=(32, 24)):
            buffer = io.BytesIO()
            Image.new('RGB', size, color).save(buffer, format='JPEG')
            return buffer.getvalue()
        def upload(payload, session='current'):
            return urlopen(Request(self.url+'/api/browser-frame', data=payload,
                headers={'Content-Type':'image/jpeg','X-Camera-Session':session}))
        with upload(jpeg('red')) as response:
            self.assertEqual(response.status, 200)
        with upload(jpeg('blue')):
            pass
        self.assertEqual(self.engine.incoming.qsize(), 1)
        frame = self.engine.incoming.get_nowait()
        self.assertGreater(int(frame[0, 0, 0]), 240)
        for payload, session in [(jpeg('red'), 'stale'), (b'not a jpeg', 'current'),
                                  (jpeg('red', (1921, 1)), 'current')]:
            with self.assertRaises(HTTPError) as exc:
                upload(payload, session)
            self.assertEqual(exc.exception.code, 400)
        self.engine.state['status'] = 'stopped'
        with self.assertRaises(HTTPError):
            upload(jpeg('red'))


if __name__ == '__main__':
    unittest.main()
