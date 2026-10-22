"""The MediaPipe hand-landmarker model (7.8 MB), downloaded on first run."""
from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
       "hand_landmarker/float16/latest/hand_landmarker.task")
NAME = "hand_landmarker.task"


def model_path() -> Path:
    bundled = Path(__file__).resolve().parents[1] / "models" / NAME
    if bundled.exists() or os.access(bundled.parent, os.W_OK):
        return bundled
    from .config import config_dir
    return config_dir() / NAME


def ensure_model(progress=None) -> Path:
    path = model_path()
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("Downloading hand model (7.8 MB)…")
    with urllib.request.urlopen(URL, timeout=60) as r, tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as f:
        shutil.copyfileobj(r, f)
    os.replace(f.name, path)
    return path
