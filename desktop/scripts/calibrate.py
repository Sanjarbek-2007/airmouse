#!/usr/bin/env python3
"""Guided hand calibration: records short clips of each pose / motion and reports what the
recogniser measured, so thresholds can be tuned to a real hand.

    ./run.sh calibrate-script      (or:  .venv/bin/python scripts/calibrate.py)

Prompts appear as desktop notifications (and in the terminal). AirCursor must not be running
(the camera can only be opened once). Nothing here touches the cursor or keyboard.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from aircursor.camera import open_source
from aircursor.commands import CommandDetector, hand_tilt
from aircursor.config import Config
from aircursor.gestures import PoseClassifier, Gesture, palm_point
from aircursor.tracker import HandTracker

PHASES = [  # key, instruction, seconds
    ("fist", "Make a FIST and hold it", 4),
    ("hook", "Make a C-SHAPE: index finger bent halfway (like a hook), other fingers curled", 5),
    ("hook2", "C-SHAPE again, a little MORE bent than before", 4),
    ("hook3", "C-SHAPE again, a little LESS bent than before", 4),
    ("point", "Point with the INDEX finger straight, others curled", 4),
    ("open", "OPEN PALM, fingers spread, hold still", 4),
    ("reposition", "OPEN PALM: slowly move your hand left and right, like repositioning a mouse", 6),
    ("swipe_right", "OPEN PALM: flick RIGHT quickly, come back slowly. Repeat 3 times", 9),
    ("swipe_left", "OPEN PALM: flick LEFT quickly, come back slowly. Repeat 3 times", 9),
    ("swipe_up", "OPEN PALM: flick UP quickly, come back slowly. Repeat 3 times", 9),
    ("wave", "OPEN PALM: WAVE side to side, 4-5 swings", 6),
    ("twist_cw", "OPEN PALM: TILT your hand to the RIGHT (clockwise) and back. Repeat 3 times", 9),
    ("twist_ccw", "OPEN PALM: TILT your hand to the LEFT (counter-clockwise) and back. Repeat 3 times", 9),
]
COUNTDOWN = 3


def say(msg):
    print(msg, flush=True)
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-t", "3500", "-u", "critical", "AirCursor calibration", msg], check=False)
    snd = "/usr/share/sounds/freedesktop/stereo/message.oga"
    if shutil.which("paplay") and os.path.exists(snd):
        subprocess.Popen(["paplay", snd], stderr=subprocess.DEVNULL)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/aircursor_calibration.json")
    quick = "--quick" in sys.argv
    cfg = Config.load()
    src = open_source(cfg)
    if src is None or not src.wait_first_frame(5):
        sys.exit("No camera frame (is AirCursor still running? `aircursor ctl quit`)")
    tracker = HandTracker()
    clf = PoseClassifier()
    phases = PHASES[:1] if quick else PHASES
    data = {}
    say(f"Calibration starts in {COUNTDOWN} s. Sit as you normally do, hand ~arm's length from the camera.")
    time.sleep(COUNTDOWN)
    for key, text, secs in phases:
        say(f"NEXT: {text}")
        t_end = time.time() + COUNTDOWN
        while time.time() < t_end:   # keep the camera drained during the countdown
            src.latest(); time.sleep(0.02)
        say(f"GO ({secs} s): {text}")
        rows, last, t0 = [], -1, time.time()
        while time.time() - t0 < secs:
            frame, seq = src.latest()
            if frame is None or seq == last:
                time.sleep(0.004); continue
            last = seq
            import cv2
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            pts, world = tracker.detect(frame)
            now = time.time() - t0
            if pts is None:
                rows.append({"t": now, "hand": False}); continue
            pose = clf.classify(pts, w, h, Gesture.NONE, 1.0, 1.0, 1.0, world)
            rows.append({
                "t": now, "hand": True, "gesture": pose.gesture.value, "bend": pose.bend,
                "pinch": pose.pinch, "tuck": pose.tuck, "ext": list(map(bool, clf.ext)),
                "size": pose.motion_size, "palm": (palm_point(pts) * (w, h)).tolist(),
                "tilt": hand_tilt(pts, w, h), "wh": [w, h],
            })
        data[key] = rows
        hands = [r for r in rows if r["hand"]]
        print(f"   {key}: {len(rows)} frames, hand in {len(hands)}", flush=True)
    say("Done. Thank you!")
    out.write_text(json.dumps(data))
    src.stop(); tracker.close()
    print("saved", out)


if __name__ == "__main__":
    main()
