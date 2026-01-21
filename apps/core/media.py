# apps/core/media.py
import mimetypes
import os
import re

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.http import http_date
from django.views.decorators.http import require_GET

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

@require_GET
def media_serve(request, path: str):
    # Only serve files inside MEDIA_ROOT
    full_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, path))
    if not full_path.startswith(os.path.normpath(str(settings.MEDIA_ROOT))):
        raise Http404("Invalid path")

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("Not found")

    file_size = os.path.getsize(full_path)
    content_type, _ = mimetypes.guess_type(full_path)
    content_type = content_type or "application/octet-stream"

    range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE")
    if not range_header:
        # Normal full response
        with open(full_path, "rb") as f:
            resp = HttpResponse(f.read(), content_type=content_type)
        resp["Content-Length"] = str(file_size)
        resp["Accept-Ranges"] = "bytes"
        resp["Last-Modified"] = http_date(os.path.getmtime(full_path))
        return resp

    m = _RANGE_RE.match(range_header.strip())
    if not m:
        # Bad Range -> return whole file
        with open(full_path, "rb") as f:
            resp = HttpResponse(f.read(), content_type=content_type)
        resp["Content-Length"] = str(file_size)
        resp["Accept-Ranges"] = "bytes"
        return resp

    start_s, end_s = m.groups()
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1

    if start >= file_size:
        resp = HttpResponse(status=416)
        resp["Content-Range"] = f"bytes */{file_size}"
        return resp

    end = min(end, file_size - 1)
    length = end - start + 1

    with open(full_path, "rb") as f:
        f.seek(start)
        data = f.read(length)

    resp = HttpResponse(data, status=206, content_type=content_type)
    resp["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    resp["Accept-Ranges"] = "bytes"
    resp["Content-Length"] = str(length)
    resp["Last-Modified"] = http_date(os.path.getmtime(full_path))
    return resp
