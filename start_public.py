"""Keep the public demo and its temporary HTTPS tunnel running together."""
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 8088)) == 0:
            raise SystemExit('Public server is already running. See outputs/public-link.txt or stop_public.cmd first.')
    output = ROOT / 'outputs'
    output.mkdir(exist_ok=True)
    stop = output / 'public-stop.flag'
    link = output / 'public-link.txt'
    stop.unlink(missing_ok=True)
    link.unlink(missing_ok=True)
    binary = ROOT / 'tools/cloudflared.exe'
    if not binary.is_file():
        raise SystemExit('Install tools/cloudflared.exe first; see PUBLIC_LINK.md')
    env = dict(os.environ, PYTHONIOENCODING='utf-8', YOLO_CONFIG_DIR=str(output / 'ultralytics-config'))
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    children = []
    try:
        with (output / 'public-server.log').open('w', encoding='utf-8') as serverlog, (output / 'public-tunnel.log').open('w', encoding='utf-8') as tunnellog:
            server = subprocess.Popen([sys.executable, '-u', str(ROOT/'public_app.py')], cwd=ROOT,
                env=env, stdout=serverlog, stderr=subprocess.STDOUT, creationflags=flags)
            children.append(server)
            time.sleep(2)
            if server.poll() is not None:
                raise RuntimeError('Server could not start; check outputs/public-server.log')
            tunnel = subprocess.Popen([str(binary), 'tunnel', '--url', 'http://127.0.0.1:8088', '--protocol', 'http2'],
                cwd=ROOT, env=env, stdout=tunnellog, stderr=subprocess.STDOUT, creationflags=flags)
            children.append(tunnel)
            print('Starting HTTPS link. Keep this computer awake. Use stop_public.cmd to stop.', flush=True)
            announced = False
            while not stop.exists():
                if any(p.poll() is not None for p in children):
                    raise RuntimeError('Public service stopped; check outputs/public-*.log')
                if not announced:
                    log = (output / 'public-tunnel.log').read_text(encoding='utf-8', errors='replace')
                    match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', log)
                    if match:
                        link.write_text(match[0]+'\n', encoding='utf-8')
                        print('Share this link: '+match[0], flush=True)
                        announced = True
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        link.unlink(missing_ok=True)
        stop.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
