# Architecture

```
camera ──► hand landmarks ──► pose classifier ──► confirmation state machine ──► actions
(webcam / phone stream)        (MediaPipe)        (gestures.py / Pose.kt)        (controller.py / Controller.kt)
                                                                                   │
                       ┌───────────────────────────────────────────────────────────┤
                       ▼                                                           ▼
                 cursor motion (smart, relative)                         buttons · scroll · volume · global actions
```

## Desktop (`desktop/aircursor`)

| Module | Role |
|---|---|
| `camera.py` | Local webcams (auto-detected) and MJPEG phone streams. Always serves the newest frame. |
| `tracker.py`, `models.py` | MediaPipe Hand Landmarker; model auto-downloaded on first run. |
| `gestures.py` | `Gesture` / `Action` vocabulary, pose classifier with finger hysteresis. |
| `motion.py` | One-euro filter, `SmartMotion` (hand-size normalisation, speed-up, reach boost), `Dial`. |
| `controller.py` | Confirmation state machine, action execution, pause, click-storm guard. |
| `backends/` | `uinput` (Linux, Wayland + X11), `pynput` (Windows/macOS), volume control per OS. |
| `engine.py` | Threaded camera → tracker → controller loop; thread-safe instant `pause()`. |
| `ipc.py` | Local control socket: `aircursor ctl pause|resume|toggle|quit|show|status`. |
| `gui/` | Qt app: Live, Gestures, Settings, Camera, Guide pages + the always-on-top panic panel. |

Linux note: GNOME's Wayland ignores "always on top" from normal windows but honours it for X11 windows, so the
GUI runs through XWayland (`libxcb-cursor`, fetched without root by `scripts/setup-linux.sh`), and the panel is
marked *sticky + above* so it follows you across workspaces.

## Mobile (`mobile/`)

| Piece | Role |
|---|---|
| `src/` (TypeScript) | React Native UI: Home, Gestures, Settings, Guide. Talks to native via one module. |
| `engine/*.kt` | Pure-Kotlin port of the desktop recognition + safety logic (JVM-testable). |
| `AirCursorService` | Foreground service (type *camera*): CameraX → MediaPipe → engine. Runs with any app in front. |
| `AirAccessibilityService` | Draws the cursor + panic panel over all apps, injects taps / drags / swipes, performs Back/Home, listens for the Volume Up+Down emergency stop. |
| `AirCursorModule` | JS bridge: start/stop/pause, settings JSON, 10 Hz live state events. |
| `SettingsStore` | One live settings object shared by the UI and the services, so changes apply instantly. |

Drags on Android are a chain of continued gesture strokes (`StrokeDescription.continueStroke`), which is why
`minSdk` is 26.
