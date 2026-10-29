"""Temporary public demo: isolated browser sessions, at most two detectors."""
import argparse
from http.cookies import SimpleCookie, CookieError
from http.server import ThreadingHTTPServer
import secrets
import threading
import time
from pathlib import Path
from web_app import Engine, ROOT, make_handler


class PublicEngine(Engine):
    def __init__(self, registry, token):
        self.registry = registry
        self.last_seen = time.monotonic()
        self.feedback_count = 0
        super().__init__(ROOT / 'best.pt', registry.folder / (token + '.sqlite3'))
        self.state.update(mode='waste', source='browser')

    def start(self, mode, source, camera=0):
        if mode != 'waste' or source not in ('browser', 'sample'):
            raise ValueError('ลิงก์สาธารณะรองรับโมเดลขยะกับกล้องอุปกรณ์นี้หรือภาพตัวอย่างเท่านั้น')
        with self.registry.lock:
            active = sum(bool(e.worker and e.worker.is_alive()) for e in self.registry.sessions.values())
            if active >= 2:
                raise ValueError('มีผู้ใช้งานตรวจจับครบ 2 คนแล้ว กรุณารอสักครู่แล้วเริ่มใหม่')
            super().start(mode, source, camera)

    def save_feedback(self, category, payload):
        with self.lock:
            if self.feedback_count >= 10:
                raise ValueError('ส่งภาพครบ 10 ภาพในรอบใช้งานนี้แล้ว')
            record = super().save_feedback(category, payload)
            self.feedback_count += 1
            return record


class Registry:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.sessions = {}

    def sweep(self):
        with self.lock:
            now = time.monotonic()
            for token, engine in list(self.sessions.items()):
                if now - engine.last_seen > 60:
                    engine.stop()
                if now - engine.last_seen > 300 and not (engine.worker and engine.worker.is_alive()):
                    engine.database.unlink(missing_ok=True)
                    del self.sessions[token]

    def resolve(self, token=None, create=False):
        with self.lock:
            if token not in self.sessions:
                if not create:
                    raise ValueError('รอบใช้งานหมดอายุ กรุณารีเฟรชหน้าเว็บ')
                self.sweep()
                if len(self.sessions) >= 30:
                    raise ValueError('มีผู้เข้าชมเต็มแล้ว กรุณาลองใหม่ภายหลัง')
                token = secrets.token_urlsafe(32)
                self.sessions[token] = PublicEngine(self, token)
            engine = self.sessions[token]
            engine.last_seen = time.monotonic()
            return token, engine

    def close(self):
        for engine in list(self.sessions.values()):
            engine.stop()
        for engine in list(self.sessions.values()):
            if engine.worker:
                engine.worker.join(timeout=10)


def public_handler(registry):
    class Handler(make_handler(None)):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def end_headers(self):
            if getattr(self, 'new_cookie', None):
                self.send_header('Set-Cookie', f'sortsense={self.new_cookie}; Path=/; HttpOnly; Secure; SameSite=Lax')
            self.send_header('Permissions-Policy', 'camera=(self), microphone=()')
            self.send_header('Referrer-Policy', 'same-origin')
            super().end_headers()

        def select_engine(self, create=False):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                token = cookie['sortsense'].value if 'sortsense' in cookie else None
                resolved, self.engine = registry.resolve(token, create)
            except (ValueError, CookieError) as exc:
                self.send(503 if create else 401, {'error': str(exc)})
                return False
            if resolved != token:
                self.new_cookie = resolved
            return True

        def do_GET(self):
            self.new_cookie = None
            if self.path == '/':
                if not self.select_engine(create=True):
                    return
                html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
                html = html.replace('<option value="demo">ทดลอง · วัตถุทั่วไป</option>', '')
                html = html.replace('<option value="camera">กล้อง Webcam</option>', '')
                html = html.replace('value="waste" id="waste-option" disabled', 'value="waste" id="waste-option" selected')
                html = html.replace('<option value="browser">', '<option value="browser" selected>')
                html = html.replace('โหมด iPad: เปิดเว็บผ่าน HTTPS บน iPad และเปิดหน้านี้ค้างไว้ • สถิติเริ่มใหม่เมื่อเริ่มรอบใหม่',
                    'ลิงก์ทดลองสาธารณะ • ตรวจจับพร้อมกันได้ 2 คน • ภาพส่งผ่าน Cloudflare ให้คอมเจ้าของประมวลผล • ภาพแจ้งทายผิดจะถูกบันทึกให้เจ้าของตรวจทาน')
                self.send(200, html.encode('utf-8'), 'text/html; charset=utf-8')
            elif self.path.startswith('/api/'):
                if self.select_engine():
                    make_handler(self.engine).do_GET(self)
            else:
                super().do_GET()

        def do_POST(self):
            self.new_cookie = None
            if self.select_engine():
                make_handler(self.engine).do_POST(self)
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8088)
    args = parser.parse_args()
    registry = Registry(ROOT / 'outputs/public-demo' / secrets.token_hex(8))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), public_handler(registry))
    stop = threading.Event()
    def cleanup():
        while not stop.wait(15):
            registry.sweep()
    threading.Thread(target=cleanup, daemon=True).start()
    print(f'Public demo origin: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        registry.close()


if __name__ == '__main__':
    main()
