"""Isolated local proof of concept. Not a public production server.

POST /convert: raw XLSX bytes, Bearer token required. Returns merged PDF,
padding each visible worksheet to an even number of pages.
"""
import io
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import threading
import zipfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

from pypdf import PdfReader, PdfWriter

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ET.register_namespace('', NS['s'])
LIMIT = 25 * 1024 * 1024
LOCK = threading.Lock()

def inspect_xlsx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if len(z.infolist()) > 5000 or sum(x.file_size for x in z.infolist()) > 100 * 1024 * 1024:
            raise ValueError('Workbook expanded size exceeds limit')
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entries')
        for n in names:
            if n.startswith('/') or '..' in n.replace('\\', '/').split('/'):
                raise ValueError('Invalid workbook path')
            if 'vbaproject' in n.lower() or n.startswith('xl/externalLinks/'):
                raise ValueError('Macros and external links are unsupported')
            if n.endswith('.rels'):
                root = ET.fromstring(z.read(n))
                if any(x.get('TargetMode') == 'External' for x in root):
                    raise ValueError('External relationships are unsupported in this prototype')
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = wb.findall('s:sheets/s:sheet', NS)
        indices = [i for i, s in enumerate(sheets) if s.get('state', 'visible') == 'visible']
        if not indices or len(indices) > 100:
            raise ValueError('Expected 1 to 100 visible worksheets')
        return indices

def single_sheet(data, selected):
    """Keep source formatting/formulas, hide other sheets in a temporary copy."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            payload = src.read(item.filename)
            if item.filename == 'xl/workbook.xml':
                wb = ET.fromstring(payload)
                for i, sheet in enumerate(wb.findall('s:sheets/s:sheet', NS)):
                    sheet.set('state', 'visible' if i == selected else 'hidden')
                for view in wb.findall('s:bookViews/s:workbookView', NS):
                    view.set('activeTab', str(selected))
                    view.set('firstSheet', str(selected))
                payload = ET.tostring(wb, encoding='utf-8', xml_declaration=True)
            dst.writestr(item, payload)
    return out.getvalue()

def convert(data, soffice):
    indices = inspect_xlsx(data)
    writer = PdfWriter()
    counts = []
    workspace = Path(os.environ.get('PDF_WORK_DIR', str(Path(__file__).resolve().parent / 'runtime' / 'jobs')))
    workspace.mkdir(parents=True, exist_ok=True)
    with LOCK, tempfile.TemporaryDirectory(prefix='excel-backend-', dir=workspace) as directory:
        root = Path(directory)
        profile = root / 'profile'
        profile.mkdir()
        # Disable macro execution and link updates in this isolated profile.
        (profile / 'user').mkdir()
        (profile / 'user' / 'registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>2</value></prop></item>
</oor:items>''', encoding='utf-8')
        for index in indices:
            source = root / ('sheet-%03d.xlsx' % index)
            source.write_bytes(single_sheet(data, index))
            command = [
                str(soffice), '-env:UserInstallation=' + profile.as_uri(),
                '--headless', '--nologo', '--nodefault', '--norestore',
                '--convert-to', 'pdf:calc_pdf_Export', '--outdir', str(root), str(source),
            ]
            environment = dict(os.environ, TMP=str(root), TEMP=str(root), TMPDIR=str(root))
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       env=environment, start_new_session=(os.name != 'nt'))
            try:
                stdout, stderr = process.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.communicate()
                raise RuntimeError('LibreOffice conversion timed out')
            result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            pdf = source.with_suffix('.pdf')
            if result.returncode or not pdf.exists():
                raise RuntimeError('LibreOffice conversion failed (exit %s): %s' %
                                   (result.returncode, (result.stderr + result.stdout).decode('utf-8', 'replace')[:2000]))
            reader = PdfReader(pdf)
            if not reader.pages:
                raise RuntimeError('No PDF pages produced')
            counts.append(len(reader.pages))
            for page in reader.pages:
                if page.mediabox.width <= 0 or page.mediabox.height <= 0:
                    raise RuntimeError('Invalid page bounds')
                writer.add_page(page)
            if len(reader.pages) % 2:
                last = reader.pages[-1]
                blank = writer.add_blank_page(float(last.mediabox.width), float(last.mediabox.height))
                blank.mediabox = last.mediabox
                blank.cropbox = last.cropbox
                if last.rotation:
                    blank.rotate(last.rotation)
        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue(), counts

class Handler(BaseHTTPRequestHandler):
    token = ''
    soffice = None

    def log_message(self, *args):
        pass

    def send(self, status, data, mime='application/json', headers=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            self.send(200, b'{"status":"ok","engine":"libreoffice","prototype":true}')
        else:
            self.send(404, b'{"error":"Not found"}')

    def do_POST(self):
        if self.path != '/convert':
            return self.send(404, b'{"error":"Not found"}')
        if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + self.token):
            return self.send(401, b'{"error":"Unauthorized"}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > LIMIT:
                return self.send(413, b'{"error":"File exceeds 25 MB or is empty"}')
            data = self.rfile.read(size)
            if len(data) != size:
                raise ValueError('Incomplete upload')
            pdf, counts = convert(data, self.soffice)
            self.send(200, pdf, 'application/pdf', {'X-Worksheet-Page-Counts': json.dumps(counts)})
        except (ValueError, zipfile.BadZipFile, ET.ParseError, KeyError):
            self.send(400, b'{"error":"Unsupported or malformed XLSX"}')
        except Exception:
            self.send(500, b'{"error":"Conversion failed"}')

def create_server(soffice, token, port=8765):
    if len(token) < 24:
        raise ValueError('Set a token of at least 24 characters')
    Handler.soffice = Path(soffice)
    Handler.token = token
    return HTTPServer(('127.0.0.1', port), Handler)

if __name__ == '__main__':
    executable = os.environ.get('SOFFICE_PATH', 'soffice')
    api = create_server(executable, os.environ.get('PDF_BACKEND_TOKEN', ''))
    print('Local prototype: http://127.0.0.1:8765', flush=True)
    api.serve_forever()
