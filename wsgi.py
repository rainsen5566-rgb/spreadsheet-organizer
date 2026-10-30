"""Cloud WSGI adapter. Bearer token stays on the calling Site's server."""
import json
import os
import secrets
import shutil
import zipfile
import xml.etree.ElementTree as ET
from server import convert, LIMIT

def application(environ, start_response):
    def respond(code, body, mime='application/json', extra=()):
        labels = {200:'OK', 400:'Bad Request', 401:'Unauthorized', 404:'Not Found',
                  405:'Method Not Allowed', 413:'Content Too Large', 500:'Internal Server Error', 503:'Service Unavailable'}
        start_response('%s %s' % (code, labels[code]), [
            ('Content-Type', mime), ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), *extra])
        return [body]
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', '')
    token = os.environ.get('PDF_BACKEND_TOKEN', '')
    executable = shutil.which(os.environ.get('SOFFICE_PATH', 'soffice'))
    if path == '/health' and method == 'GET':
        ready = len(token) >= 24 and bool(executable)
        return respond(200 if ready else 503, json.dumps({'ready':ready,'engine':'libreoffice'}).encode())
    if path != '/convert':
        return respond(404, b'{"error":"Not found"}')
    if method != 'POST':
        return respond(405, b'{"error":"POST required"}')
    if len(token) < 24 or not executable:
        return respond(503, b'{"error":"Backend not configured"}')
    auth = environ.get('HTTP_AUTHORIZATION', '')
    if not secrets.compare_digest(auth, 'Bearer ' + token):
        return respond(401, b'{"error":"Unauthorized"}')
    try:
        size = int(environ.get('CONTENT_LENGTH') or '0')
        if size < 1 or size > LIMIT:
            return respond(413, b'{"error":"Expected an XLSX of 1 byte to 25 MB"}')
        source = environ['wsgi.input'].read(size)
        if len(source) != size:
            raise ValueError('Incomplete upload')
        pdf, counts = convert(source, executable)
        return respond(200, pdf, 'application/pdf', [
            ('Content-Disposition', 'attachment; filename="converted.pdf"'),
            ('X-Worksheet-Page-Counts', json.dumps(counts))])
    except (ValueError, zipfile.BadZipFile, ET.ParseError, KeyError):
        return respond(400, b'{"error":"Unsupported or malformed XLSX"}')
    except Exception:
        return respond(500, b'{"error":"Conversion failed"}')
