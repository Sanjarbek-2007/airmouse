#!/usr/bin/env bash
# Downloads the MediaPipe hand-landmarker model into the Android assets (Gradle also does this on build).
set -euo pipefail
DEST="$(cd "$(dirname "$0")/.." && pwd)/android/app/src/main/assets"
mkdir -p "$DEST"
curl -fL -o "$DEST/hand_landmarker.task" \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
echo "saved to $DEST/hand_landmarker.task"
