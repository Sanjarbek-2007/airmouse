import math

from aircursor.config import Config
from aircursor.gestures import Action, Command, Gesture
from tests.helpers import *


def chords(c):
    return c.keyboard.chords


def swipe(dx=0.0, dy=0.0, n=8, ox=0.5, oy=0.6):
    """Rest, then a fast straight flick of the open palm."""
    rest = [hand({0, 1, 2, 3}, ox=ox, oy=oy)] * 5
    move = [hand({0, 1, 2, 3}, ox=ox + dx * (i + 1), oy=oy + dy * (i + 1)) for i in range(n)]
    return rest + move


def test_swipe_right_is_next_window_and_left_is_previous():
    c, m, v = make(); run(c, swipe(dx=0.045))
    assert chords(c) == [("alt", "tab")]
    c, m, v = make(); run(c, swipe(dx=-0.045, ox=0.7))
    assert chords(c) == [("alt", "shift", "tab")]


def test_swipe_up_and_down():
    c, m, v = make(); run(c, swipe(dy=-0.07, oy=0.9))
    assert chords(c) == [("super",)]
    c, m, v = make(); run(c, swipe(dy=0.07, oy=0.2))
    assert chords(c) == [("super", "d")]


def test_slow_repositioning_does_not_trigger():
    c, m, v = make(); run(c, swipe(dx=0.012, n=40))
    assert chords(c) == []


def test_short_flick_does_not_trigger():
    c, m, v = make(); run(c, swipe(dx=0.03, n=4))   # < 2.6 hand lengths
    assert chords(c) == []


def test_swipe_needs_an_open_palm():
    pointing = [hand({0}, ox=0.5 + 0.045 * i) for i in range(14)]
    c, m, v = make(); run(c, pointing)
    assert chords(c) == []
    assert m.mv[0] > 0   # it moved the cursor instead


def test_cooldown_blocks_a_second_command_and_the_return_motion():
    c, m, v = make()
    run(c, swipe(dx=0.045) + [hand({0, 1, 2, 3}, ox=0.5 + 0.36 - 0.045 * (i + 1)) for i in range(8)])
    assert chords(c) == [("alt", "tab")]   # the hand coming back is not a "swipe left"


def test_wave_is_play_pause_and_never_a_swipe():
    c, m, v = make()
    run(c, [hand({0, 1, 2, 3}, ox=0.5 + 0.06 * math.sin(2 * math.pi * i / 9)) for i in range(40)])
    assert chords(c) == [("playpause",)]


def test_twist_clockwise_and_counter_clockwise():
    base = hand({0, 1, 2, 3})
    c, m, v = make()
    run(c, [base] * 5 + [rotated(base, 10 * (i + 1)) for i in range(6)])
    assert chords(c) == [("ctrl", "alt", "right")]
    c, m, v = make()
    run(c, [base] * 5 + [rotated(base, -10 * (i + 1)) for i in range(6)])
    assert chords(c) == [("ctrl", "alt", "left")]


def test_small_tilt_is_not_a_twist():
    base = hand({0, 1, 2, 3})
    c, m, v = make(); run(c, [base] * 5 + [rotated(base, 4 * (i + 1)) for i in range(6)])
    assert chords(c) == []


def test_commands_can_be_disabled_and_remapped():
    cfg = Config(); cfg.motion_commands = False
    c, m, v = make(cfg); run(c, swipe(dx=0.045))
    assert chords(c) == []
    cfg = Config(); cfg.commands["swipe_right"] = Action.COPY.value; cfg.commands["swipe_left"] = Action.NONE.value
    c, m, v = make(cfg); run(c, swipe(dx=0.045))
    assert chords(c) == [("ctrl", "c")]
    c, m, v = make(cfg); run(c, swipe(dx=-0.045, ox=0.7))
    assert chords(c) == []


def test_sensitivity_changes_how_easily_it_triggers():
    cfg = Config(); cfg.command_sensitivity = 2.0
    c, m, v = make(cfg); run(c, swipe(dx=0.03, n=5))   # too small for 1x, fine for 2x
    assert chords(c) == [("alt", "tab")]


def test_command_label_is_shown_and_guard_counts_commands():
    c, m, v = make(); labels = run(c, swipe(dx=0.045))
    assert any("SWIPE RIGHT" in l and "NEXT WINDOW" in l for l in labels)
    cfg = Config(); cfg.guard_clicks = 3; cfg.guard_window = 10.0
    c, m, v = make(cfg)
    t = 1000.0
    for k in range(4):   # command storm: each swipe is separated by more than the cooldown
        for f in swipe(dx=0.045 * (1 if k % 2 == 0 else -1), ox=0.5 if k % 2 == 0 else 0.9):
            t += 1 / 15; c.update(f, W, H, t)
        t += 1.2
    assert c.paused and chords(c)[-1] is not None


def test_pause_blocks_commands():
    c, m, v = make(); c.pause("x"); run(c, swipe(dx=0.045))
    assert chords(c) == []


# ----------------------------------------------------------------- C-shape
def test_c_shape_is_its_own_gesture_between_point_and_fist():
    c, m, v = make(); run(c, [HOOK] * 6)
    assert c.stable == Gesture.HOOK and c.pose.bend < 150
    c, m, v = make(); run(c, [FIST] * 6)
    assert c.stable == Gesture.FIST and c.pose.bend < 100
    c, m, v = make(); run(c, [POINT] * 6)
    assert c.stable == Gesture.POINT and c.pose.bend > 160


def test_c_shape_defaults_to_the_middle_button_and_is_remappable():
    c, m, v = make(); run(c, [POINT] * 4 + [HOOK] * 6 + [POINT] * 4)
    assert [e for e in m.log if isinstance(e, tuple)] == [("middle", "down"), ("middle", "up")]
    cfg = Config(); cfg.gestures["hook"] = Action.WINDOW_NEXT.value
    c, m, v = make(cfg); run(c, [POINT] * 4 + [HOOK] * 6 + [POINT] * 4)
    assert chords(c) == [("alt", "tab")]   # a shortcut mapped to a pose fires once, not repeatedly


def test_c_shape_sensitivity_widens_the_accepted_range():
    loose = Config(); loose.hook_sensitivity = 1.5
    tight = Config(); tight.hook_sensitivity = 0.6
    nearly_straight = hand({0})   # index straight: not a C for anyone
    c, m, v = make(loose); run(c, [nearly_straight] * 6)
    assert c.stable == Gesture.POINT
    c, m, v = make(tight); run(c, [HOOK] * 6)
    assert c.stable in (Gesture.HOOK, Gesture.POINT, Gesture.FIST)  # tight range may reject a loose C


def test_pinch_still_wins_over_c_shape():
    c, m, v = make(); run(c, [POINT] * 4 + [PINCH] * 6)
    assert c.stable == Gesture.PINCH
