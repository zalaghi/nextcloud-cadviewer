#!/usr/bin/env python3
"""Private CADViewer gateway: one fresh, offline rootless container per drawing.

Run as a dedicated unprivileged Linux user. HTTP credentials, other requests
and host directories are never mounted in the parser. No container API socket.
"""
import argparse
import hmac
import http.server
import json
import os
from pathlib import Path
import re
import signal
import selectors
import time
import subprocess
import tempfile
import uuid

MAX_INPUT = 32 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024
FORMATS = frozenset(('dwg', 'dxf'))


def validate_config(config):
    if not re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', config['image']):
        raise ValueError('Use a locally installed immutable image ID, not a mutable tag')
    parent = config.get('cgroup_parent', '')
    if parent and not re.fullmatch(r'/[A-Za-z0-9_/-]{1,150}', parent):
        raise ValueError('Invalid delegated cgroup path')
    for key in ('fonts', 'scratch'):
        path = Path(config[key])
        if not path.is_absolute() or any(c in str(path) for c in ':,\n\r') or path.is_symlink() or not path.is_dir():
            raise ValueError('Expected absolute directory paths without special mount characters')


def container_command(config, name, drawing, extension, layout_index=0):
    if extension not in FORMATS or not isinstance(layout_index, int) or not 0 <= layout_index <= 31:
        raise ValueError('Unsupported drawing or layout')
    command = ['podman', 'run', '--rm', '--pull=never', '--name', name,
            '--network=none', '--read-only', '--read-only-tmpfs=false', '--image-volume=ignore',
            '--user=65534:65534', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--memory=2g', '--cpus=2', '--pids-limit=64',
            '--ulimit', 'cpu=60:60', '--ulimit', 'fsize=134217728:134217728',
            '--ulimit', 'nofile=128:128', '--tmpfs', '/scratch:rw,size=768m,mode=1777',
            '-v', f"{config['fonts']}:/fonts:ro,z",
            '-v', f'{drawing}:/input.{extension}:ro,z',
            '--workdir=/scratch', '--entrypoint=/usr/bin/env', config['image'], '-i',
            'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME=/scratch', 'TMPDIR=/scratch',
            'PYTHONPATH=/opt/python', 'PYTHONDONTWRITEBYTECODE=1',
            'OPENBLAS_NUM_THREADS=1', 'LANG=C.UTF-8',
            '/usr/local/bin/python3', '/opt/cadviewer/render.py', f'/input.{extension}',
            '--layout', str(layout_index)]
    if config.get('cgroup_parent'):
        command[2:2] = ['--cgroup-parent=' + config['cgroup_parent']]
    return command


def convert(config, content, extension, layout_index=0):
    if extension not in FORMATS or not 0 < len(content) <= MAX_INPUT:
        raise ValueError('Invalid input')
    name = 'cadviewer-job-' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='job-', dir=config['scratch']) as directory:
        drawing = Path(directory) / ('drawing.' + extension)
        drawing.write_bytes(content)
        drawing.chmod(0o644)  # Containing host directory remains private (0700).
        process = None
        try:
            process = subprocess.Popen(container_command(config, name, drawing, extension, layout_index),
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 80
            output = bytearray()
            with selectors.DefaultSelector() as ready:
                ready.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not ready.select(remaining):
                        raise TimeoutError('Conversion deadline')
                    chunk = os.read(process.stdout.fileno(), min(65536, MAX_OUTPUT + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        raise ValueError('Preview exceeds output limit')
            if process.wait(timeout=max(0.1, deadline - time.monotonic())) != 0 or not output:
                raise RuntimeError('Conversion failed')
            return bytes(output)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
            try:
                subprocess.run(['podman', 'rm', '-f', '-v', name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=15, check=False)
            finally:
                if process is not None:
                    process.wait(timeout=5)
                    process.stdout.close()



class Gateway(http.server.BaseHTTPRequestHandler):
    server_version = 'CADViewer'
    sys_version = ''
    protocol_version = 'HTTP/1.0'

    def log_message(self, *_):
        pass

    def respond(self, code, body=b'', content_type='text/plain'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def handle_one_request(self):
        self.connection.settimeout(5)
        signal.setitimer(signal.ITIMER_REAL, 15)
        try:
            super().handle_one_request()
        except (TimeoutError, BrokenPipeError, ConnectionError):
            self.close_connection = True
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def do_POST(self):
        if self.path != '/convert':
            return self.respond(404)
        expected = 'Bearer ' + self.server.token
        auth = self.headers.get_all('Authorization', [])
        if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), expected.encode()):
            return self.respond(401)
        sizes = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') is not None or len(sizes) != 1 or not re.fullmatch(r'[0-9]{1,9}', sizes[0]):
            return self.respond(400)
        size = int(sizes[0])
        if not 0 < size <= MAX_INPUT:
            return self.respond(413)
        formats = self.headers.get_all('X-CAD-Format', [])
        layouts = self.headers.get_all('X-CAD-Layout', ['0'])
        if len(formats) != 1 or len(layouts) != 1 or not re.fullmatch(r'(?:[0-9]|[12][0-9]|3[01])', layouts[0]):
            return self.respond(400)
        layout_index = int(layouts[0])
        extension = formats[0]
        if extension not in FORMATS:
            return self.respond(415)
        content = self.rfile.read(size)
        if len(content) != size:
            return self.respond(400)
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            output = convert(self.server.config, content, extension, layout_index)
        except (RuntimeError, ValueError, subprocess.SubprocessError, OSError):
            return self.respond(422)
        self.respond(200, output, 'image/svg+xml')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8090)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as a dedicated unprivileged user with rootless Podman')
    config = json.loads(args.config.read_text())
    validate_config(config)
    token = args.token_file.read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', token):
        parser.error('Token must contain at least 43 URL-safe random characters')
    def deadline(*_):
        raise TimeoutError('Request deadline')
    signal.signal(signal.SIGALRM, deadline)
    server = http.server.HTTPServer((args.bind, args.port), Gateway)
    server.config, server.token = config, token
    server.serve_forever()


if __name__ == '__main__':
    main()
