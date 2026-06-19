"""Local-disk object backend for preserved diagram images (dev).

Writes under DATA_DIR/assets and returns a root-relative "/assets/…" path that
the StaticFiles mount in app/main.py serves. Production uses the S3/R2 backend.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.config import get_settings


class LocalObjects:
    def save_diagram_image(self, lecture_id: str, asset_id: str, ext: str, data: bytes) -> str:
        base = Path(get_settings().data_dir) / "assets" / lecture_id
        base.mkdir(parents=True, exist_ok=True)
        fname = f"{asset_id}.{(ext or 'png').lstrip('.')}"
        (base / fname).write_bytes(data)
        return f"/assets/{lecture_id}/{fname}"

    def delete_lecture_assets(self, lecture_id: str) -> None:
        shutil.rmtree(Path(get_settings().data_dir) / "assets" / lecture_id, ignore_errors=True)

    def read_diagram_bytes(self, asset: dict) -> bytes | None:
        image_ref = asset.get("image_ref") or ""
        if not image_ref:
            return None
        fp = Path(get_settings().data_dir) / image_ref.lstrip("/")
        return fp.read_bytes() if fp.exists() else None

    # --- transient upload handoff (audio + slides between web and worker) ---
    # In local mode this is DATA_DIR/uploads; web+worker share it only when they
    # share a disk (or in eager mode, same process). Production uses the S3 backend
    # so a separate worker host can read what the web service wrote. No audio ever
    # survives a finished pipeline — delete_uploads runs on every terminal outcome.
    def _upload_path(self, lecture_id: str, name: str) -> Path:
        return Path(get_settings().data_dir) / "uploads" / lecture_id / name

    def save_upload(self, lecture_id: str, name: str, src_path: str) -> None:
        dest = self._upload_path(lecture_id, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest)

    def read_upload(self, lecture_id: str, name: str, dest_path: str) -> bool:
        src = self._upload_path(lecture_id, name)
        if not src.exists():
            return False
        shutil.copyfile(src, dest_path)
        return True

    def delete_uploads(self, lecture_id: str) -> None:
        shutil.rmtree(Path(get_settings().data_dir) / "uploads" / lecture_id, ignore_errors=True)
