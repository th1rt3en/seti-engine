"""Where the game archive is written (docs/PLAN.md decision D25).

The Worker sends every archive file to the service (`PUT /archive`) and the service writes it to Google Cloud Storage with the
credentials of
the Cloud Run service account (the metadata server), so no key is stored anywhere. This is the only I/O in the service, and it lives outside
the rules engine, which stays pure. For development, set ARCHIVE_DIR to write the files into a local folder instead.

Settings (environment): ARCHIVE_BUCKET (default "temp-common-storage"), ARCHIVE_DIR (development only).
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BUCKET = "temp-common-storage"
ROOT = "seti-engine/games/"  # the bucket is shared, so everything of this project lives under one folder
_PATH = re.compile(
    r"^seti-engine/games/\d{4}/\d{2}/\d{2}/[A-Za-z0-9_-]{1,80}/(header\.json|result\.json|replay\.json|actions/\d{7}\.json)$"
)
_METADATA_TOKEN = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"


class ArchiveError(Exception):
    pass


def valid_path(path: str) -> bool:
    """Only the paths the Worker writes are accepted: nothing else in the bucket can be touched through this service."""
    return _PATH.match(path) is not None


def _access_token() -> str:
    req = urllib.request.Request(_METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=5) as res:  # noqa: S310 (a fixed https-less metadata address)
        return str(json.load(res)["access_token"])


def write(path: str, body: Any) -> None:
    """Write one JSON document, overwriting an earlier one at the same path."""
    if not valid_path(path):
        raise ArchiveError(f"not an archive path: {path!r}")
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    folder = os.environ.get("ARCHIVE_DIR")
    if folder:
        target = Path(folder) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return
    bucket = os.environ.get("ARCHIVE_BUCKET", DEFAULT_BUCKET)
    base = f"https://storage.googleapis.com/upload/storage/v1/b/{urllib.parse.quote(bucket, safe='')}/o"
    url = f"{base}?uploadType=media&name={urllib.parse.quote(path, safe='')}"
    try:
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20):  # noqa: S310
            pass
    except OSError as e:  # URLError, HTTPError, timeouts
        raise ArchiveError(f"could not write {path} to gs://{bucket}: {e}") from e
