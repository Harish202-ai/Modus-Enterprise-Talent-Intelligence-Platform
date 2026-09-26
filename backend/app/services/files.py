"""Candidate uploads: resumes, case documents, communication videos.

Stored on a local volume (Docker: /data/uploads) behind this module, so moving to object storage
later only changes `_path`/`_write`. Every file is checked by its *content* (magic bytes), not just
its extension, size-capped while streaming, fingerprinted (sha256) and recorded in `files`.
"""
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Iterable, Optional

from fastapi import UploadFile

from app import database
from app.config import get_settings
from app.models.common import new_id, utcnow
from app.services.content import ContentError, NotFound

CHUNK = 1024 * 1024

# kind -> (content type, family)
KINDS = {
    "pdf": ("application/pdf", "document"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document"),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "document"),
    "mp4": ("video/mp4", "video"),
    "mov": ("video/quicktime", "video"),
    "webm": ("video/webm", "video"),
}


class UploadRejected(ContentError):
    status_code = 422


def _sniff(kind: str, head: bytes, data_for_zip: Optional[bytes]) -> bool:
    if kind == "pdf":
        return head.startswith(b"%PDF-")
    if kind in ("docx", "pptx"):
        if not head.startswith(b"PK\x03\x04") or data_for_zip is None:
            return False
        try:
            names = set(zipfile.ZipFile(io.BytesIO(data_for_zip)).namelist())
        except zipfile.BadZipFile:
            return False
        return ("word/document.xml" if kind == "docx" else "ppt/presentation.xml") in names
    if kind in ("mp4", "mov"):
        return head[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"free")
    if kind == "webm":
        return head.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _root() -> Path:
    return Path(get_settings().uploads_dir)


def _path(doc: dict) -> Path:
    return _root() / doc["tenant_id"] / doc["user_id"] / f"{doc['_id']}.{doc['kind']}"


def max_bytes(kind: str, override_mb: Optional[int] = None) -> int:
    s = get_settings()
    mb = override_mb or (s.upload_max_mb_video if KINDS[kind][1] == "video" else s.upload_max_mb_document)
    return mb * 1024 * 1024


async def save(tenant_id: str, user_id: str, upload: UploadFile, allowed: Iterable[str], purpose: str, max_mb: Optional[int] = None) -> dict:
    allowed = [k for k in allowed if k in KINDS]
    name = (upload.filename or "upload").strip()
    kind = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if kind not in allowed:
        raise UploadRejected("This file type isn't accepted here", [{"field": "file", "message": f"upload a {' / '.join(k.upper() for k in allowed)} file"}])
    limit = max_bytes(kind, max_mb)
    doc = {
        "_id": new_id(), "tenant_id": tenant_id, "user_id": user_id, "kind": kind, "content_type": KINDS[kind][0],
        "filename": name[:200], "purpose": purpose, "created_at": utcnow(),
    }
    path = _path(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest, size, head = hashlib.sha256(), 0, b""
    keep_all = KINDS[kind][1] == "document"  # small; needed to inspect zip-based formats
    buffered = bytearray()
    try:
        with open(path, "wb") as out:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise UploadRejected("File too large", [{"field": "file", "message": f"must be under {limit // (1024 * 1024)} MB"}])
                if len(head) < 16:
                    head = (head + chunk)[:16]
                if keep_all:
                    buffered += chunk
                digest.update(chunk)
                out.write(chunk)
        if size == 0 or not _sniff(kind, head, bytes(buffered) if keep_all else None):
            raise UploadRejected("That file doesn't look like a valid " + kind.upper(), [{"field": "file", "message": "file content doesn't match its type"}])
    except Exception:
        path.unlink(missing_ok=True)
        raise
    doc.update(size=size, sha256=digest.hexdigest())
    await database.files().insert_one(doc)
    return doc


async def get(tenant_id: str, file_id: str) -> dict:
    doc = await database.files().find_one({"_id": file_id, "tenant_id": tenant_id})
    if doc is None:
        raise NotFound("File not found")
    return doc


def read_bytes(doc: dict) -> bytes:
    return _path(doc).read_bytes()


def path_of(doc: dict) -> Path:
    return _path(doc)


def public(doc: dict) -> dict:
    return {k: doc.get(k) for k in ("kind", "content_type", "filename", "size", "purpose", "created_at")} | {"id": doc["_id"]}
