#!/usr/bin/env bash
# One-time setup for the AirCursor download (Linux). Safe to re-run. Nothing here needs Python.
#   1. permission to create a virtual mouse (/dev/uinput)  - asks for sudo, once
#   2. an "AirCursor" entry in your app menu
# Remove it again with:  ./install.sh --uninstall
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
RULE=/etc/udev/rules.d/99-aircursor-uinput.rules
APPS="$HOME/.local/share/applications"; ICONS="$HOME/.local/share/icons"

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$APPS/aircursor.desktop" "$ICONS/aircursor.png"
  [ -f "$RULE" ] && sudo rm -f "$RULE" && sudo udevadm control --reload-rules
  echo "Removed the menu entry and the udev rule."; exit 0
fi

echo "==> Cursor permission (/dev/uinput)"
if [ -w /dev/uinput ]; then
  echo "OK: you can already control the cursor"
else
  echo "AirCursor moves the real mouse through a virtual device (/dev/uinput). This needs a one-time permission:"
  echo "  sudo setfacl -m u:$USER:rw /dev/uinput     (active now)"
  echo "  + a udev rule so it survives reboots"
  read -r -p "Run these with sudo now? [y/N] " yn
  if [[ "${yn:-n}" =~ ^[Yy]$ ]]; then
    command -v setfacl >/dev/null || { echo "setfacl missing: sudo apt install acl"; exit 1; }
    sudo setfacl -m "u:$USER:rw" /dev/uinput
    echo 'KERNEL=="uinput", MODE="0660", GROUP="input", TAG+="uaccess"' | sudo tee "$RULE" >/dev/null
    sudo udevadm control --reload-rules
    echo "done"
  else
    echo "skipped - AirCursor will run in preview-only mode until you do this"
  fi
fi

echo "==> App menu entry"
mkdir -p "$APPS" "$ICONS"
cp "$DIR/aircursor.png" "$ICONS/aircursor.png"
cat > "$APPS/aircursor.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=AirCursor
Comment=Control your cursor with hand gestures
Exec=$DIR/aircursor
Icon=$ICONS/aircursor.png
Terminal=false
Categories=Utility;Accessibility;
StartupWMClass=aircursor
DESK
echo "added - search for AirCursor in your app menu, or run: $DIR/aircursor"
