"""Local/LAN waste dashboard. Run: python web_app.py --port 8080."""
import argparse
import csv
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sqlite3
import ssl
import queue
import threading
import time
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parent
CLASSES = ['Recyclable', 'Organic', 'General', 'Hazardous']
# BGR: yellow, green, blue, red; the website uses the same palette.
BIN_COLORS = {'Recyclable': (8, 179, 234), 'Organic': (94, 197, 34),
              'General': (246, 130, 59), 'Hazardous': (68, 68, 239)}


class Counter:
    """Count each tracker ID once after five consecutive same-class observations."""
    def __init__(self, minimum=5):
        self.minimum = minimum
        self.pending = {}
        self.seen = set()

    def update(self, detections):
        visible = {d['id'] for d in detections if d['id'] is not None}
        self.pending = {k: v for k, v in self.pending.items() if k in visible}
        events = []
        for d in detections:
            key = d['id']
            if key is None:
                continue
            previous, hits = self.pending.get(key, (None, 0))
            hits = hits + 1 if previous == d['class'] else 1
            self.pending[key] = (d['class'], hits)
            if hits >= self.minimum and key not in self.seen:
                self.seen.add(key)
                events.append(dict(d))
        return events


class Engine:
    def __init__(self, weights, database):
        self.weights = Path(weights)
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS events (session TEXT, time TEXT, mode TEXT, track_id INTEGER, class TEXT, confidence REAL)')
        self.lock = threading.RLock()
        self.worker = None
        self.stop_event = threading.Event()
        self.jpeg = None
        self.frame_version = 0
        self.incoming = queue.Queue(maxsize=1)
        self.state = dict(status='idle', error=None, mode='demo', source='sample',
                          session=None, fps=0, detections=[], counts={}, total=0, frames=0)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.database, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def snapshot(self):
        with self.lock:
            state = json.loads(json.dumps(self.state))
            state['frame_version'] = self.frame_version
            state['model_ready'] = self.weights.is_file()
            return state

    def events(self, limit=50):
        with self.db() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute('SELECT * FROM events ORDER BY rowid DESC LIMIT ?', (limit,))]

    def save_feedback(self, category, payload):
        from PIL import Image, ImageOps
        if category not in CLASSES:
            raise ValueError('กรุณาเลือกประเภทขยะที่ถูกต้อง')
        try:
            with Image.open(io.BytesIO(payload)) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > 25000000:
                    raise ValueError('Unsupported image')
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGB')
        except Exception as exc:
            raise ValueError('กรุณาใช้ภาพ JPG, PNG หรือ WebP ไม่เกิน 25 ล้านพิกเซล') from exc
        identifier = uuid.uuid4().hex
        folder = self.database.parent / 'feedback' / category
        folder.mkdir(parents=True, exist_ok=True)
        image.save(folder / (identifier + '.jpg'), quality=95)
        record = {'id': identifier, 'class': category, 'status': 'pending_review',
                  'created_at': datetime.now().astimezone().isoformat(),
                  'image': identifier + '.jpg', 'annotation': 'image_level_only'}
        (folder / (identifier + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        return record

    def start(self, mode, source, camera=0):
        if mode not in ('demo', 'waste') or source not in ('sample', 'camera', 'browser'):
            raise ValueError('โหมดหรือแหล่งภาพไม่ถูกต้อง')
        if type(camera) is not int or not 0 <= camera <= 9:
            raise ValueError('หมายเลขกล้องต้องอยู่ระหว่าง 0–9')
        if mode == 'waste' and not self.weights.is_file():
            raise ValueError('ยังไม่มีโมเดลขยะ กรุณาเทรนและใส่ไฟล์ best.pt ก่อน')
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError('ระบบกำลังทำงานอยู่ กรุณาหยุดก่อนเริ่มรอบใหม่')
            self.stop_event.clear()
            self.jpeg = None
            self.incoming = queue.Queue(maxsize=1)
            self.state = dict(status='starting', error=None, mode=mode, source=source,
                              session=uuid.uuid4().hex, fps=0, detections=[], counts={}, total=0, frames=0)
            self.worker = threading.Thread(target=self.run, args=(mode, source, camera), daemon=True)
            self.worker.start()

    def stop(self):
        with self.lock:
            if self.worker and self.worker.is_alive():
                self.state['status'] = 'stopping'
                self.stop_event.set()

    def upload(self, session, payload):
        import cv2
        import numpy as np
        from PIL import Image
        # Inspect dimensions before allocating the decoded image.
        try:
            with Image.open(io.BytesIO(payload)) as image:
                if image.format != 'JPEG' or max(image.size) > 1920 or min(image.size) < 1:
                    raise ValueError('ภาพต้องเป็น JPEG ขนาดไม่เกิน 1920 พิกเซล')
            frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError('อ่านภาพไม่ได้')
        except Exception as exc:
            raise ValueError('ภาพ JPEG ไม่ถูกต้องหรือมีขนาดใหญ่เกินไป') from exc
        with self.lock:
            if (session != self.state['session'] or self.state['source'] != 'browser'
                    or self.state['status'] not in ('starting', 'running')):
                raise ValueError('รอบกล้องสิ้นสุดแล้ว กรุณาเริ่มใหม่')
            try:
                self.incoming.get_nowait()
            except queue.Empty:
                pass
            self.incoming.put_nowait(frame)

    def run(self, mode, source, camera):
        cap = None
        try:
            import cv2
            import numpy as np
            from ultralytics import YOLO
            model_path = ROOT / 'yolov8n.pt' if mode == 'demo' else self.weights
            if not model_path.is_file():
                raise ValueError('ไม่พบไฟล์โมเดล กรุณาติดตั้งโมเดลก่อนเริ่ม')
            model = YOLO(str(model_path))
            if mode == 'waste' and [model.names[k] for k in sorted(model.names)] != CLASSES:
                raise ValueError('คลาสโมเดลต้องเรียง Recyclable, Organic, General, Hazardous')
            sample = None
            if source == 'sample':
                sample = cv2.imdecode(np.frombuffer((ROOT / 'web/assets/waste-sample.jpg').read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
                if sample is None:
                    raise ValueError('ไม่พบภาพตัวอย่างขยะ')
            elif source == 'camera':
                cap = cv2.VideoCapture(camera)
                if not cap.isOpened():
                    raise ValueError('เปิดกล้องไม่ได้ ตรวจสิทธิ์กล้องหรือปิดแอปอื่นที่ใช้กล้องอยู่')
            counter = Counter()
            last_frame = time.monotonic()
            while not self.stop_event.is_set():
                started = time.perf_counter()
                if source == 'browser':
                    try:
                        frame = self.incoming.get(timeout=0.5)
                        last_frame = time.monotonic()
                    except queue.Empty:
                        if time.monotonic() - last_frame > 30:
                            raise ValueError('ไม่ได้รับภาพจาก iPad นาน 30 วินาที กรุณาเปิดหน้าเว็บแล้วเริ่มใหม่')
                        continue
                elif cap is not None:
                    ok, frame = cap.read()
                    if not ok:
                        raise ValueError('รับภาพจากกล้องไม่ได้ กรุณาตรวจการเชื่อมต่อ')
                else:
                    frame = sample.copy()
                height, width = frame.shape[:2]
                if max(height, width) > 960:
                    frame = cv2.resize(frame, (round(width * 960 / max(height, width)), round(height * 960 / max(height, width))))
                result = model.track(frame, persist=True, tracker='bytetrack.yaml',
                                     conf=0.45, imgsz=640, device='cpu', verbose=False)[0]
                detections = []
                boxes = result.boxes
                if boxes is not None:
                    ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes)
                    for tid, cls, conf in zip(ids, boxes.cls.int().cpu().tolist(), boxes.conf.cpu().tolist()):
                        detections.append(dict(id=tid, **{'class': model.names[cls]}, confidence=round(conf, 4)))
                new = counter.update(detections)
                now = datetime.now().astimezone().isoformat(timespec='seconds')
                if new:
                    with self.db() as db:
                        for d in new:
                            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?)',
                                       (self.state['session'], now, mode, d['id'], d['class'], d['confidence']))
                annotated = result.plot() if mode == 'demo' else frame.copy()
                if mode == 'waste' and boxes is not None:
                    for d, bounds in zip(detections, boxes.xyxy.cpu().tolist()):
                        x1, y1, x2, y2 = map(int, bounds)
                        color = BIN_COLORS[d['class']]
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                        label = f"ID {d['id'] if d['id'] is not None else '?'} | {d['class']} {d['confidence']:.0%}"
                        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, .55, 1)
                        tx = max(0, min(x1, width - tw - 8))
                        ty = max(th + 8, y1)
                        cv2.rectangle(annotated, (tx, ty-th-8), (tx+tw+8, ty+baseline), color, -1)
                        cv2.putText(annotated, label, (tx+4, ty-4), cv2.FONT_HERSHEY_SIMPLEX, .55, (15, 25, 20), 1, cv2.LINE_AA)
                ok, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ok:
                    raise ValueError('แปลงภาพสำหรับเว็บไซต์ไม่สำเร็จ')
                with self.lock:
                    for d in new:
                        counts = self.state['counts']
                        counts[d['class']] = counts.get(d['class'], 0) + 1
                    for d in detections:
                        d['confirmed'] = counter.pending.get(d['id'], (None, 0))[1] >= counter.minimum
                    self.jpeg = encoded.tobytes()
                    self.frame_version += 1
                    self.state.update(status='stopping' if self.stop_event.is_set() else 'running',
                                      detections=detections, total=sum(self.state['counts'].values()),
                                      frames=self.state['frames'] + 1,
                                      fps=round(1 / max(time.perf_counter() - started, 0.001), 1))
                # Browser input already has backpressure; do not add another frame delay.
                self.stop_event.wait(max(0, (0.15 if source == 'sample' else 1 / 30) - (time.perf_counter() - started)))
            with self.lock:
                self.state.update(status='stopped', detections=[], fps=0)
        except Exception as exc:
            with self.lock:
                self.state.update(status='error', error=str(exc), detections=[], fps=0)
        finally:
            if cap is not None:
                cap.release()


def make_handler(engine):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, data, content_type='application/json; charset=utf-8', attachment=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if attachment:
                self.send_header('Content-Disposition', 'attachment; filename="events.csv"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/state':
                self.send(200, engine.snapshot())
            elif path == '/api/events':
                self.send(200, engine.events())
            elif path == '/api/export':
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=['session', 'time', 'mode', 'track_id', 'class', 'confidence'])
                writer.writeheader()
                with engine.db() as db:
                    db.row_factory = sqlite3.Row
                    for row in db.execute('SELECT * FROM events ORDER BY rowid DESC'):
                        writer.writerow(dict(row))
                self.send(200, buffer.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8', True)
            elif path == '/api/frame':
                with engine.lock:
                    jpeg = engine.jpeg
                self.send(200, jpeg, 'image/jpeg') if jpeg else self.send(204, b'')
            else:
                assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
                assets['/assets/waste-bins.png'] = ('assets/waste-bins.png', 'image/png')
                if path not in assets:
                    self.send(404, {'error': 'Not found'})
                    return
                name, mime = assets[path]
                self.send(200, (ROOT / 'web' / name).read_bytes(), mime)

        def do_POST(self):
            # JSON-only, same-origin requests prevent cross-site camera activation.
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                self.send(403, {'error': 'ไม่อนุญาตคำสั่งจากเว็บไซต์อื่น'})
                return
            if self.path == '/api/feedback':
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 12000000:
                        raise ValueError('ไฟล์ต้องมีขนาดไม่เกิน 12 MB')
                    record = engine.save_feedback(self.headers.get('X-Waste-Class'), self.rfile.read(size))
                    self.send(201, record)
                except (ValueError, TypeError) as exc:
                    self.send(400, {'error': str(exc)})
                except OSError:
                    self.send(500, {'error': 'บันทึกไม่สำเร็จ กรุณาตรวจพื้นที่ว่างบนคอม'})
                return
            if self.path == '/api/browser-frame':
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if self.headers.get('Content-Type') != 'image/jpeg' or not 0 < size <= 1500000:
                        raise ValueError('ต้องส่ง JPEG ขนาดไม่เกิน 1.5 MB')
                    engine.upload(self.headers.get('X-Camera-Session'), self.rfile.read(size))
                    self.send(200, {'ok': True})
                except (ValueError, TypeError) as exc:
                    self.send(400, {'error': str(exc)})
                return
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                self.send(415, {'error': 'ต้องส่งข้อมูล JSON'})
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024:
                    raise ValueError('ขนาดคำสั่งไม่ถูกต้อง')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('คำสั่งไม่ถูกต้อง')
                if self.path == '/api/start':
                    engine.start(data.get('mode', 'demo'), data.get('source', 'sample'), data.get('camera', 0))
                elif self.path == '/api/stop':
                    engine.stop()
                else:
                    self.send(404, {'error': 'Not found'})
                    return
                self.send(200, engine.snapshot())
            except (ValueError, TypeError) as exc:
                self.send(400, {'error': str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--cert')
    parser.add_argument('--key')
    parser.add_argument('--weights', default=str(ROOT / 'best.pt'))
    args = parser.parse_args()
    if bool(args.cert) != bool(args.key):
        parser.error('--cert and --key must be provided together')
    engine = Engine(args.weights, ROOT / 'outputs/dashboard.sqlite3')
    server = ThreadingHTTPServer((args.host, args.port), make_handler(engine))
    if args.cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.cert, args.key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f'Dashboard: {"https" if args.cert else "http"}://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        if engine.worker:
            engine.worker.join(timeout=10)
        server.server_close()


if __name__ == '__main__':
    main()
