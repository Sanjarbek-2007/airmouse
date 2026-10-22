# Contributing

Thanks for helping! Bug reports from real phones and webcams are just as valuable as code. A few ground rules keep the two apps consistent.

## Keep the behaviour identical across platforms
The recognition + safety logic exists twice: `desktop/aircursor/{gestures,motion,controller}.py` and
`mobile/android/app/src/main/java/com/aircursor/engine/*.kt`. If you change one, change the other **and**
its tests (`desktop/tests/test_controller.py` ↔ `mobile/android/app/src/test/.../EngineTest.kt`). The test
scenarios are deliberately the same.

## Safety is a feature, not a nicety
Anything that can press a button must be pausable instantly and must release on pause. Don't add an action
that bypasses the confirmation window or the click-storm guard without a very good reason.

## Dev setup
* Desktop: `cd desktop && ./scripts/setup-linux.sh && .venv/bin/python -m pytest`
* Mobile: `cd mobile && npm install && npm run check`

## Style
Match the surrounding code. Keep comments for the *why*. Add a test for every behaviour change.
