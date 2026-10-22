#!/usr/bin/env bash
# One-time setup for AirCursor on Linux. Safe to re-run.
#   1. Python virtual environment + dependencies
#   2. libxcb-cursor (lets the always-on-top panic panel work on GNOME/Wayland) - no root needed
#   3. hand-tracking model download
#   4. permission for /dev/uinput (needs sudo; it asks first)
#   5. app-menu launcher
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

say "Python environment"
PY=""
for c in python3.12 python3.11 python3.10 python3.9; do command -v "$c" >/dev/null && PY="$c" && break; done
[ -n "$PY" ] || { echo "Need Python 3.9-3.12 (MediaPipe has no wheels for newer versions yet)."; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

say "libxcb-cursor (for the always-on-top panel)"
if ldconfig -p 2>/dev/null | grep -q libxcb-cursor.so.0; then
  echo "already installed system-wide"
elif [ -f vendor/lib/libxcb-cursor.so.0 ]; then
  echo "already present in vendor/lib"
elif command -v apt >/dev/null; then
  tmp="$(mktemp -d)"
  (cd "$tmp" && apt download libxcb-cursor0 >/dev/null 2>&1 && dpkg -x libxcb-cursor0*.deb ex \
    && mkdir -p "$DIR/vendor/lib" && cp ex/usr/lib/*/libxcb-cursor.so.0 "$DIR/vendor/lib/") \
    && echo "fetched into vendor/lib" \
    || echo "could not fetch it; install with: sudo apt install libxcb-cursor0 (the app still works, the panel may not stay on top)"
  rm -rf "$tmp"
else
  echo "install your distro's libxcb-cursor package for the always-on-top panel"
fi

say "Hand-tracking model"
PYTHONPATH="$DIR" .venv/bin/python -c "from aircursor.models import ensure_model; print(ensure_model())"

say "Cursor permission (/dev/uinput)"
if [ -w /dev/uinput ]; then
  echo "OK: you can already control the cursor"
else
  echo "AirCursor creates a virtual mouse through /dev/uinput. This needs a one-time permission:"
  echo "  sudo setfacl -m u:$USER:rw /dev/uinput                  (works now, lost on reboot)"
  echo "  + a udev rule so it persists (below)"
  read -r -p "Run these with sudo now? [y/N] " yn
  if [[ "${yn:-n}" =~ ^[Yy]$ ]]; then
    sudo setfacl -m "u:$USER:rw" /dev/uinput
    echo 'KERNEL=="uinput", MODE="0660", GROUP="input", TAG+="uaccess"' | sudo tee /etc/udev/rules.d/99-aircursor-uinput.rules >/dev/null
    sudo udevadm control --reload-rules
    echo "done"
  else
    echo "skipped - the app will run in preview-only mode until you do this"
  fi
fi

say "App menu launcher"
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons"
QT_QPA_PLATFORM=offscreen PYTHONPATH="$DIR" .venv/bin/python -c "
from PySide6.QtGui import QGuiApplication
from aircursor.gui.icon import make_pixmap
app = QGuiApplication([]); make_pixmap(256).save('$HOME/.local/share/icons/aircursor.png')"
cat > "$HOME/.local/share/applications/aircursor.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=AirCursor
Comment=Control your cursor with hand gestures
Exec=$DIR/run.sh
Icon=$HOME/.local/share/icons/aircursor.png
Terminal=false
Categories=Utility;Accessibility;
StartupWMClass=aircursor
DESK
echo "added to your app menu"

say "All set. Start it with:  $DIR/run.sh"
