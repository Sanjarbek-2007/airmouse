"""Camera sources: any local webcam, or a phone streaming MJPEG (e.g. the Android
"IP Webcam" app). By default the first working local camera is used."""
from __future__ import annotations

import glob
import os
import re
import ssl
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass
class CameraInfo:
    index: int
    name: str

    @property
    def label(self) -> str:
        return f"{self.name}  (#{self.index})"


def list_local_cameras() -> list[CameraInfo]:
    """Local capture devices, built-in/USB first. Cheap on Linux (reads sysfs, opens nothing)."""
    cams: list[CameraInfo] = []
    if sys.platform.startswith("linux"):
        for node in sorted(glob.glob("/sys/class/video4linux/video*"),
                           key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0)):
            try:
                idx = int(re.sub(r"\D", "", os.path.basename(node)))
                name = open(f"{node}/name").read().strip().split(":")[0].strip()
                kind = open(f"{node}/index").read().strip() if os.path.exists(f"{node}/index") else "0"
            except (OSError, ValueError):
                continue
            if kind == "0":  # index > 0 are metadata nodes of the same camera
                cams.append(CameraInfo(idx, name))
    else:
        for i in range(4):
            cap = cv2.VideoCapture(i)
            ok = cap.isOpened()
            cap.release()
            if ok:
                cams.append(CameraInfo(i, f"Camera {i}"))
    return cams


class FrameSource:
    """A background thread keeps ``latest()`` pointing at the newest frame."""

    name = ""

    def __init__(self):
        self.frame: Optional[np.ndarray] = None
        self.seq = 0
        self.error: Optional[str] = None
        self._stop = False
        self._lock = threading.Lock()

    def _publish(self, img):
        with self._lock:
            self.frame, self.seq = img, self.seq + 1

    def latest(self) -> Tuple[Optional[np.ndarray], int]:
        with self._lock:
            return self.frame, self.seq

    def wait_first_frame(self, timeout: float) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            if self.frame is not None:
                return True
            time.sleep(0.03)
        return False

    def stop(self):
        self._stop = True


class LocalCamera(FrameSource):
    def __init__(self, index: int, name: str = "", width=1280, height=720):
        super().__init__()
        self.index, self.name = index, name or f"Camera {index}"
        self.size = (width, height)
        threading.Thread(target=self._run, daemon=True).start()

    def _open(self):
        backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _run(self):
        cap, fails = None, 0
        while not self._stop:
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                cap = self._open()
                if not cap.isOpened():
                    self.error = f"Cannot open camera #{self.index} (in use by another app?)"
                    time.sleep(1.0)
                    continue
            ok, img = cap.read()
            if ok and img is not None:
                self.error, fails = None, 0
                self._publish(img)
            else:
                fails += 1
                if fails > 30:
                    self.error = f"Lost camera #{self.index}"
                    cap.release()
                    cap = None
                time.sleep(0.02)
        if cap is not None:
            cap.release()


class MjpegStream(FrameSource):
    """Reads an MJPEG-over-HTTP(S) stream. Self-signed certificates (phones) are accepted."""

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.name = "Phone stream (" + re.sub(r"^https?://|/.*$", "", url) + ")"
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop:
            try:
                with urllib.request.urlopen(self.url, context=self._ctx, timeout=8) as resp:
                    self.error, buf = None, b""
                    while not self._stop:
                        chunk = resp.read(16384)
                        if not chunk:
                            break
                        buf += chunk
                        end = buf.rfind(b"\xff\xd9")
                        if end == -1:
                            continue
                        start = buf.rfind(b"\xff\xd8", 0, end)
                        if start != -1:
                            img = cv2.imdecode(np.frombuffer(buf[start:end + 2], np.uint8), cv2.IMREAD_COLOR)
                            if img is not None:
                                self._publish(img)
                        buf = buf[end + 2:]
            except Exception as e:  # network hiccup: retry
                self.error = f"Stream error: {e}"
                time.sleep(1)


def normalize_stream_url(url: str) -> str:
    """Accept "192.168.0.5:8080" or "https://192.168.0.5:8080" and add the /video path."""
    url = url.strip()
    if not url:
        return url
    if not re.match(r"^https?://", url):
        url = "http://" + url
    if re.match(r"^https?://[^/]+/?$", url):
        url = url.rstrip("/") + "/video"
    return url


def open_source(cfg) -> Optional[FrameSource]:
    """Open the camera chosen in settings. "auto" = first working local camera, then the
    saved phone URL. Returns None if nothing works (``describe_failure`` explains)."""
    choice = cfg.camera_source
    if choice == "url":
        return MjpegStream(normalize_stream_url(cfg.phone_url)) if cfg.phone_url else None
    if choice.startswith("local:"):
        try:
            idx = int(choice.split(":", 1)[1])
        except ValueError:
            idx = 0
        names = {c.index: c.name for c in list_local_cameras()}
        return LocalCamera(idx, names.get(idx, ""))
    for cam in list_local_cameras():  # auto
        src = LocalCamera(cam.index, cam.name)
        if src.wait_first_frame(3.0):
            return src
        src.stop()
    if cfg.phone_url:
        return MjpegStream(normalize_stream_url(cfg.phone_url))
    return None
