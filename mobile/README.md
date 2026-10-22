# AirCursor — Android

Control your **phone** with hand gestures seen by its own camera. React Native UI + Kotlin native layer
(MediaPipe hand tracking, CameraX, accessibility service). Works in the background with any app in front.

> **Status: beta.** Compile-checked against the real React Native / MediaPipe / CameraX / Android APIs, the
> gesture engine is unit-tested, and the app builds, installs and launches on a real phone (Redmi Note 10,
> Android 12). Full hand-control behaviour still needs wider device testing — see
> [Known unverified areas](#known-unverified-areas) and please report what you find.

## Install (no build needed)

Download **`AirCursor-<version>-android.apk`** from the
[latest release](https://github.com/Sanjarbek-2007/airmouse/releases/latest), open it on your phone and allow
*Install unknown apps*. Or: `adb install -r AirCursor-*.apk`. Requires Android 8+ (64-bit ARM). Then follow
[First run on the phone](#first-run-on-the-phone).

The release APK is signed with the debug key committed in this repo (`android/app/debug.keystore`), so any
build of this project can update any other. It is **not** a Play Store signing key.

## What it does

A foreground service reads the camera, finds your hand, recognises gestures (same engine as the desktop app) and
drives the phone through an **accessibility service**: an on-screen cursor, taps, drags, scrolls, and Back / Home.
Prop the phone up (or hold it in one hand) and use your other hand in front of the front camera.

| Gesture | Default |
|---|---|
| ☝️ Point | Move cursor |
| 🤏 Pinch | Tap; hold + move = drag |
| 🖐️ Thumb tuck | Back |
| ✌️ Peace + move | Scroll |
| 🤟 Three fingers + move | Fast scroll |
| 🤘 Rock + circle fingertip | Volume |
| ✊ / ✋ | Rest |

Remap anything in the app. Home, Recents and Notifications are available as actions too.

## Staying in control

* Floating **⏸ / ✕ panel** over every app (draggable).
* **Volume Up + Volume Down together** = pause / resume (hardware, works in any app).
* **Pause** and **Stop** buttons in the notification.
* Safety guard auto-pauses on a burst of taps.
* Android's own accessibility switch removes all control instantly.

## Build from source

Prerequisites: Node ≥ 22, JDK 17, Android SDK (platform 36, build-tools 37, NDK 27.1.12297006 — Android Studio
installs these), a device with USB debugging.

```bash
npm install
npm run check          # typecheck + lint + jest (no Android needed)
npm run android        # build + install on a connected device
```

The MediaPipe hand model (7.8 MB) is downloaded by Gradle on first build (or run `scripts/download-model.sh`).

Kotlin engine tests (no device needed): `cd android && ./gradlew testDebugUnitTest`.

### First run on the phone
1. Open AirCursor → **Setup**: allow the camera and notifications.
2. **Accessibility service → Open**, find *AirCursor*, switch it on. If Android says the setting is restricted
   (sideloaded apps): *App info → ⋮ → Allow restricted settings*, then retry.
3. Back in the app, tap **Start hand control**.

## Project layout

```
App.tsx, src/                       React Native UI (TypeScript)
android/app/src/main/java/com/aircursor/
  engine/                           pure-Kotlin gesture engine (JVM-testable)
  service/                          camera service, accessibility service, overlay views, settings
  rn/                               JS bridge
android/app/src/test/               JUnit tests for the engine (same scenarios as desktop/tests)
```

## Known unverified areas

Things that compile but need a real device to confirm:

* **Drag chains** — drags use continued `GestureDescription` strokes; timing/feel may need tuning.
* **Camera in background** — relies on a foreground service of type `camera` started from the visible app.
* **React Native 0.88 module registration** — uses `BaseReactPackage` + a legacy-style `@ReactMethod` module
  (through RN's interop layer). If the New Architecture rejects it, convert `AirCursorModule` to a TurboModule.
* **OEM quirks** (MIUI, One UI…) around accessibility overlays and background camera.
* **Frame orientation / mirroring** for the back camera.

## iOS

Not included yet. iOS has no public API for injecting touches into other apps, so the design differs
(likely an in-app or AssistiveTouch-style approach). The gesture engine is portable.
