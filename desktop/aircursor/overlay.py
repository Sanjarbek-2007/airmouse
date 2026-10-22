"""Draws the tracked hand on the preview frame."""
import cv2
import numpy as np

from .gestures import CONNECTIONS, palm_point

ACCENT = (255, 209, 0)     # BGR of the UI cyan
GREEN = (123, 214, 43)


def draw_hand(img: np.ndarray, pts, pressed: bool = False) -> None:
    if pts is None:
        return
    h, w = img.shape[:2]
    p = (pts * (w, h)).astype(int)
    color = GREEN if pressed else ACCENT
    for a, b in CONNECTIONS:
        cv2.line(img, tuple(p[a]), tuple(p[b]), color, 2, cv2.LINE_AA)
    for q in p:
        cv2.circle(img, tuple(q), 4, (255, 255, 255), -1, cv2.LINE_AA)
    c = (palm_point(pts) * (w, h)).astype(int)
    cv2.circle(img, tuple(c), 16, color, 2, cv2.LINE_AA)
    cv2.circle(img, tuple(c), 4, color, -1, cv2.LINE_AA)
