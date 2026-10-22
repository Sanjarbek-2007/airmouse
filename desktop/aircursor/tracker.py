"""MediaPipe hand landmark detection."""
from __future__ import annotations

import time
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from .models import ensure_model

DETECT_WIDTH = 384  # frames are downscaled to this width for detection (speed)


class HandTracker:
    def __init__(self, progress=None):
        path = ensure_model(progress)
        self._lm = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=1,
            min_hand_detection_confidence=0.6, min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.5))
        self._t0 = time.monotonic()

    def detect(self, frame_bgr: np.ndarray):
        """Returns ((21, 2) image landmarks in 0..1, (21, 3) metric world landmarks), or (None, None)."""
        h, w = frame_bgr.shape[:2]
        small = cv2.resize(frame_bgr, (DETECT_WIDTH, max(int(DETECT_WIDTH * h / w), 1)))
        res = self._lm.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB)),
            int((time.monotonic() - self._t0) * 1000))
        if not res.hand_landmarks:
            return None, None
        pts = np.array([[l.x, l.y] for l in res.hand_landmarks[0]])
        world = (np.array([[l.x, l.y, l.z] for l in res.hand_world_landmarks[0]])
                 if res.hand_world_landmarks else None)
        return pts, world

    def close(self):
        self._lm.close()
