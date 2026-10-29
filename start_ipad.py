"""Start the LAN dashboard with HTTPS and a certificate-only setup page."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
from pathlib import Path
import socket
import ssl
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from web_app import Engine, make_handler, ROOT


def certificates(folder, addresses):
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    def save_key(key, name):
        (folder / name).write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    if (folder / 'ca-key.pem').exists():
        ca_key = serialization.load_pem_private_key((folder / 'ca-key.pem').read_bytes(), None)
        ca = x509.load_pem_x509_certificate((folder / 'ca.pem').read_bytes())
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SortSense Local Camera CA')])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
              .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=3650))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
              .sign(ca_key, hashes.SHA256()))
        save_key(ca_key, 'ca-key.pem')
        (folder / 'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (folder / 'SortSense-CA.cer').write_bytes(ca.public_bytes(serialization.Encoding.DER))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SortSense Camera')]))
            .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(hours=1)).not_valid_after(now+timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')] +
                           [x509.IPAddress(ipaddress.ip_address(a)) for a in addresses]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, hashes.SHA256()))
    save_key(key, 'server-key.pem')
    (folder / 'server.pem').write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    return ca


def main():
    addresses = sorted(set(['127.0.0.1'] + socket.gethostbyname_ex(socket.gethostname())[2]))
    folder = ROOT / 'outputs/ipad-tls'
    ca = certificates(folder, addresses)
    class Setup(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            if self.path == '/SortSense-CA.cer':
                body = (folder / 'SortSense-CA.cer').read_bytes()
                mime = 'application/x-x509-ca-cert'
            elif self.path == '/':
                links = ''.join(f'<p><a href="https://{a}:8443">Open camera: https://{a}:8443</a></p>' for a in addresses if a != '127.0.0.1')
                body = ('<meta name="viewport" content="width=device-width, initial-scale=1"><h1>SortSense iPad setup</h1>'
                        '<p>1. <a href="/SortSense-CA.cer">Download camera certificate</a></p>'
                        '<p>2. Settings &gt; General &gt; VPN &amp; Device Management: install SortSense Local Camera CA.</p>'
                        '<p>3. Settings &gt; General &gt; About &gt; Certificate Trust Settings: enable SortSense Local Camera CA.</p>'
                        '<p>4. Open the HTTPS link matching this computer IP:</p>'+links).encode()
                mime = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    engine = Engine(ROOT / 'best.pt', ROOT / 'outputs/dashboard.sqlite3')
    server = ThreadingHTTPServer(('0.0.0.0', 8443), make_handler(engine))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(folder / 'server.pem', folder / 'server-key.pem')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    setup = ThreadingHTTPServer(('0.0.0.0', 8085), Setup)
    threading.Thread(target=setup.serve_forever, daemon=True).start()
    for address in addresses:
        if address != '127.0.0.1':
            print(f'iPad setup: http://{address}:8085  |  Camera: https://{address}:8443', flush=True)
    print('Certificate SHA256: ' + ca.fingerprint(hashes.SHA256()).hex(), flush=True)
    print('Keep this window open. Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        if engine.worker:
            engine.worker.join(timeout=10)
        setup.shutdown()
        setup.server_close()
        server.server_close()


if __name__ == '__main__':
    main()
