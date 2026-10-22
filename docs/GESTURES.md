# Gesture specification

Both apps implement exactly this. A **gesture** is what your hand does; an **action** is what the device does
about it. Every gesture can be mapped to any action.

## Recognition

Input: 21 hand landmarks per frame (MediaPipe Hand Landmarker). Distances are measured in camera pixels and
normalised by the hand size `size = |wrist → middle-finger knuckle|`.

A finger counts as **extended** when `|tip → wrist| > 1.15 × |PIP → wrist|` to become extended, and stays
extended until the ratio falls below `1.0` (hysteresis, so edge cases don't flicker).

Checked in this order (first match wins):

| # | Gesture | Rule |
|---|---|---|
| 1 | **Fist** | no finger extended — checked first, so a fist can never be mistaken for a pinch |
| 2 | **Pinch** | `|thumb tip → index tip| / size < 0.30` (release at 0.42) × sensitivity |
| 3 | **Thumb tuck** | all four fingers extended **and** `min(|thumb tip → knuckles 9, 13, 17|) / size < 0.55` (release 0.75) × sensitivity |
| 4 | **Rock** | index + pinky extended, middle + ring not |
| 5 | **Three** | index + middle + ring extended, pinky not |
| 6 | **Peace** | index + middle extended, ring + pinky not |
| 7 | **Point** | index extended, middle not |
| 8 | **Open palm** | everything else |

## Confirmation (anti-misfire)

A new gesture replaces the current one only after it has been seen for **at least 2 consecutive frames** and for
its confirmation time (× the user's *confirmation time* setting):

| Action | Seconds |
|---|---|
| move, button / tap, none | 0.10 |
| scroll, fast scroll | 0.12 |
| right button, middle button, back/home/recents/notifications | 0.15 – 0.20 |
| volume | 0.25 |
| hand lost | 0.30 |

While a *different* gesture is being confirmed, cursor motion and scrolling are suspended. After a button goes down
the cursor holds still for 0.15 s so the click lands where you aimed.

## Pointer motion

* Tracked point: midpoint of the index and middle knuckles (doesn't move when fingers curl), smoothed with a
  one-euro filter.
* **Relative**, like a mouse: only displacement matters. Lift the hand (open palm / leave the frame) to reposition.
* `cursor Δ = Δhand / handSize × base × speed × speedUp × reachBoost` — by default `accel = boost = 0`, so
  `speedUp = reachBoost = 1` (plain 1:1). Both are opt-in:
  * `speedUp = 1 + accel × smoothstep((speed − 0.25) / 2.75)` (speed in hand-lengths per second)
  * `reachBoost = 1 + boost × smoothstep(run / 2.5)` where `run` is the distance travelled in a consistent
    direction (decays with a 2 s time constant; resets when you stop for 0.25 s or reverse direction).

## Dial

While the *volume* action is active, the index fingertip is tracked against the centre of its last 10 positions.
Signed angle change accumulates; **one clockwise turn = +10 %** (configurable), counter-clockwise lowers it.
Circles smaller than 18 % of the hand size are ignored as jitter.

## Safety

* **Pause** releases every button / touch and drops queued cursor motion, then ignores all gestures.
* **Guard**: ≥ 6 button presses within 2 s auto-pauses (configurable).
* **Dropouts**: a hand missing for < 0.3 s keeps a drag alive; longer releases it.

## Defaults

| Gesture | Desktop | Android |
|---|---|---|
| Point | move | move |
| Pinch | left button | tap / touch & drag |
| Thumb tuck | right button | back |
| Peace | scroll | scroll |
| Three | fast scroll (3×) | fast scroll (3×) |
| Rock | volume dial | volume dial |
| Fist | nothing | nothing |
| Open palm | nothing | nothing |
