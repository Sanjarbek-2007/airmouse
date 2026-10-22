# AirCursor — desktop

Control your computer's cursor with hand gestures seen by any camera. Python · MediaPipe · Qt.

## Install

**Easiest — Linux download (no Python needed):** get `AirCursor-<version>-linux-x86_64.tar.gz` from the
[latest release](https://github.com/Sanjarbek-2007/airmouse/releases/latest), extract, run `./install.sh` once
(cursor permission + app-menu entry), then `./aircursor`. `./install.sh --uninstall` removes both.
Build it yourself: `pip install -r requirements.txt pyinstaller && python packaging/build.py`
(needs a Python with a shared libpython: python.org, `uv`, or pyenv `--enable-shared`).

**From source —**
**Linux** (tested on Ubuntu / GNOME, Wayland and X11):

```bash
./scripts/setup-linux.sh     # venv, deps, hand model, /dev/uinput permission, app-menu entry
./run.sh                     # open the app
```

The script asks before using `sudo`, and only for one thing: permission to create a virtual mouse
(`/dev/uinput`). Without it the app still runs in preview-only mode and tells you what to do.

**Windows / macOS (experimental, untested):** Python 3.9 – 3.12, then
`pip install -r requirements.txt && python -m aircursor`. Uses `pynput` for the mouse.

## Using it

1. Put your camera where it can see your hand above the keyboard.
2. Raise your **index finger** and move: the cursor follows your hand's *motion*.
3. **Pinch** thumb + index to click; hold and move to drag.
4. **Open palm** = lift the mouse. Move your hand back and point again.

| Gesture | Default action |
|---|---|
| ☝️ Point | Move |
| 🤏 Pinch | Left click / drag |
| 🖐️ Thumb tuck | Right click / drag |
| ✌️ Peace + move | Scroll (any direction) |
| 🤟 Three fingers + move | Fast scroll |
| 🤘 Rock + circle fingertip | Volume (10 % per turn) |
| ✊ Fist / ✋ Open palm | Nothing (rest) |

Everything is remappable on the **Gestures** page, and every number is tunable on **Settings** (changes apply
instantly). The built-in **Guide** page covers the rest.

### Pointer feel
By default the cursor follows your hand **1:1** and is hand-size aware (feels the same near or far). Two optional
boosts are available under *Settings → Pointer*: **Speed-up on fast moves** and **Long-reach boost** (extra
travel while you keep moving one way, for corners). They are off by default because any extra gain makes the
cursor overshoot where camera lag is already largest.

## Staying in control

* **Floating panel** — always on top, on every workspace: ⏸ Pause / ▶ Resume, ▣ Show window, ✕ Quit. Drag it
  anywhere; right-click for a menu.
* **Space** in the window pauses / resumes. **Ctrl+Q** quits. Closing the window quits (it never keeps running hidden).
* **From anywhere:** `./run.sh ctl toggle` (pause/resume), `./run.sh ctl quit`, `./run.sh ctl status`.
  *Settings → Add shortcuts* binds **Ctrl+Alt+P** / **Ctrl+Alt+Q** on GNOME for you (only when you click it).
* **Lost the window?** Run `./run.sh` again — it raises the running instance.
* **Safety guard:** a burst of clicks (6 in 2 s by default) auto-pauses and sends a notification.
* Your real mouse and keyboard keep working the whole time.

## Cameras

Default is **Automatic**: the first working local camera. Pick a specific one, or use a phone, on the **Camera**
page. For a phone, install **IP Webcam** (Android), tap *Start server*, enter the address it shows
(`192.168.1.50:8080`) and press *Test connection*. Any MJPEG stream URL works. List cameras: `./run.sh cameras`.

## Command line

```
aircursor                 open the app (or raise the running one)
aircursor gui --dry-run   preview only: never touches the cursor
aircursor run             headless; prints recognised commands
aircursor ctl <cmd>       pause | resume | toggle | quit | show | status
aircursor cameras         list cameras
aircursor reset-config    restore default settings
```

Settings live in `~/.config/aircursor/config.json` (`%APPDATA%\aircursor`, `~/Library/Application Support/aircursor`).

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cursor control is not active" | Run `scripts/setup-linux.sh` (grants `/dev/uinput`). |
| Panic panel doesn't stay on top | `sudo apt install libxcb-cursor0` (or re-run the setup script) so the app can use XWayland. |
| Hand not detected | More light, hand fully visible, plain background. Watch the *Recognised* meter on Live. |
| Clicks too hard / too easy | *Settings → Pinch sensitivity*. |
| Accidental actions | Raise *Gesture confirmation time*. |
| Cursor too fast / slow | *Settings → Pointer speed*. |

## Development

```bash
.venv/bin/python -m pytest            # 33 tests: gestures, safety, config, GUI (offscreen)
QT_QPA_PLATFORM=offscreen ...         # GUI tests need no display
```
Architecture: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md). Gesture rules: [../docs/GESTURES.md](../docs/GESTURES.md).
