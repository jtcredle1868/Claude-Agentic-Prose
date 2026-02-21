"""
Google Drive Watcher — polls a designated Drive folder for new files,
downloads them to a local staging directory, and yields file paths for
downstream processing.

Supports:
  - Plain text / .txt files
  - Google Docs (exported as plain text)
  - Images (.png, .jpg) — downloaded as-is for OCR downstream
  - PDFs — downloaded as-is for text extraction downstream
"""

import io
import json
import logging
import time
from pathlib import Path
from typing import Generator

from obsidian_agent import config

logger = logging.getLogger(__name__)

# File types we care about and their MIME export mappings
EXPORT_MIME = {
    "application/vnd.google-apps.document": (
        "text/plain",
        ".txt",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "text/csv",
        ".csv",
    ),
}

DOWNLOAD_EXTENSIONS = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

# Track processed file IDs so we don't re-ingest
PROCESSED_TRACKER = Path(config.GDRIVE_STAGING_DIR) / ".processed_ids.json"


def _load_processed_ids() -> set:
    if PROCESSED_TRACKER.exists():
        return set(json.loads(PROCESSED_TRACKER.read_text()))
    return set()


def _save_processed_ids(ids: set) -> None:
    PROCESSED_TRACKER.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_TRACKER.write_text(json.dumps(list(ids)))


def _get_drive_service():
    """Build an authenticated Google Drive API service."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


def list_new_files(service) -> list[dict]:
    """Return metadata for files in the watched folder not yet processed."""
    processed = _load_processed_ids()
    results = (
        service.files()
        .list(
            q=f"'{config.GDRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=50,
        )
        .execute()
    )
    files = results.get("files", [])
    return [f for f in files if f["id"] not in processed]


def download_file(service, file_meta: dict) -> Path | None:
    """Download or export a single Drive file to the staging directory."""
    from googleapiclient.http import MediaIoBaseDownload

    staging = Path(config.GDRIVE_STAGING_DIR)
    staging.mkdir(parents=True, exist_ok=True)

    file_id = file_meta["id"]
    mime = file_meta["mimeType"]
    name = file_meta["name"]

    # Google Workspace files need export
    if mime in EXPORT_MIME:
        export_mime, ext = EXPORT_MIME[mime]
        dest = staging / f"{Path(name).stem}{ext}"
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    elif mime in DOWNLOAD_EXTENSIONS:
        ext = DOWNLOAD_EXTENSIONS[mime]
        dest = staging / f"{Path(name).stem}{ext}"
        request = service.files().get_media(fileId=file_id)
    else:
        # Try generic binary download for unknown types
        dest = staging / name
        request = service.files().get_media(fileId=file_id)

    try:
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        dest.write_bytes(buf.getvalue())
        logger.info("Downloaded %s → %s", name, dest)
        return dest
    except Exception:
        logger.exception("Failed to download %s", name)
        return None


def mark_processed(file_id: str) -> None:
    """Record a file ID so it won't be fetched again."""
    ids = _load_processed_ids()
    ids.add(file_id)
    _save_processed_ids(ids)


def poll_once() -> Generator[tuple[dict, Path], None, None]:
    """
    Single poll cycle: list new files, download each, yield (metadata, local_path).
    """
    service = _get_drive_service()
    new_files = list_new_files(service)
    if not new_files:
        logger.debug("No new files in Drive folder.")
        return

    logger.info("Found %d new file(s) in Drive folder.", len(new_files))
    for meta in new_files:
        local = download_file(service, meta)
        if local:
            yield meta, local
            mark_processed(meta["id"])


def watch(callback) -> None:
    """
    Continuous polling loop.  Calls *callback(meta, local_path)* for every
    new file discovered.  Runs until interrupted.
    """
    logger.info(
        "Starting Drive watcher — folder %s, interval %ds",
        config.GDRIVE_FOLDER_ID,
        config.GDRIVE_POLL_INTERVAL,
    )
    while True:
        try:
            for meta, local_path in poll_once():
                callback(meta, local_path)
        except Exception:
            logger.exception("Error during Drive poll cycle")
        time.sleep(config.GDRIVE_POLL_INTERVAL)
