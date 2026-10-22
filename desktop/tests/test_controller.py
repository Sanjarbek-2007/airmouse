import numpy as np

from aircursor.config import Config
from aircursor.gestures import Action, Gesture
from tests.helpers import *


def buttons(m):
    return [e for e in m.log if isinstance(e, tuple) and e[0] in ("left", "right", "middle")]


def test_fist_never_clicks_even_with_thumb_on_index():
    c, m, v = make()
    run(c, [POINT] * 4 + [FIST] * 12)
    assert buttons(m) == []


def test_pinch_click():
    c, m, v = make()
    run(c, [POINT] * 4 + [PINCH] * 5 + [POINT] * 4)
    assert buttons(m) == [("left", "down"), ("left", "up")]


def test_single_frame_glitch_ignored():
    c, m, v = make()
    run(c, [POINT] * 4 + [PINCH] + [POINT] * 4)
    assert buttons(m) == []


def test_left_drag_moves_cursor_while_held():
    c, m, v = make()
    seq = [POINT] * 3 + [PINCH] * 4 + [hand({1, 2, 3}, thumb="pinch", ox=0.5 + 0.01 * i) for i in range(1, 12)] + [POINT] * 4
    run(c, seq)
    assert buttons(m) == [("left", "down"), ("left", "up")]
    assert m.mv[0] > 100


def test_right_click_and_right_drag():
    c, m, v = make()
    run(c, [OPEN] * 3 + [TUCK] * 6 + [OPEN] * 4)
    assert buttons(m) == [("right", "down"), ("right", "up")]
    c, m, v = make()
    seq = [OPEN] * 2 + [TUCK] * 4 + [hand({0, 1, 2, 3}, thumb="tuck", ox=0.5 - 0.01 * i) for i in range(1, 10)] + [OPEN] * 4
    run(c, seq)
    assert buttons(m) == [("right", "down"), ("right", "up")]
    assert m.mv[0] < -100


def test_open_palm_lifts_the_mouse():
    c, m, v = make()
    run(c, [POINT] * 4 + [hand({0, 1, 2, 3}, ox=0.3 + 0.02 * i) for i in range(12)])
    moved_before = m.mv.copy()
    run(c, [hand({0, 1, 2, 3}, ox=0.5 + 0.01 * i) for i in range(10)], t0=2000.0)
    assert np.allclose(m.mv, moved_before)


def test_movement_is_independent_of_hand_position():
    res = []
    for ox, oy in ((0.25, 0.8), (0.7, 0.6)):
        c, m, v = make()
        run(c, [hand({0}, ox=ox + 0.004 * i, oy=oy) for i in range(25)])
        res.append(m.mv[0])
    assert res[0] > 50 and abs(res[0] - res[1]) / res[0] < 0.1


def test_movement_is_independent_of_distance_to_camera():
    """Same real hand motion, hand twice as far = half the pixels: cursor travel should match."""
    def far_hand(scale, i):
        p = hand({0}, ox=0.5, oy=0.75)
        p = 0.5 + (p - 0.5) * scale
        return p + (0.004 * i * scale, 0)
    res = []
    for sc in (1.0, 0.5):
        c, m, v = make()
        run(c, [far_hand(sc, i) for i in range(25)])
        res.append(m.mv[0])
    assert abs(res[0] - res[1]) / res[0] < 0.15


def _steady_sweep(cfg, frames=60):
    c, m, v = make(cfg)
    t, gains = 1000.0, []
    for i in range(frames):
        t += 1 / 15
        before = m.mv[0]
        c.update(hand({0}, ox=0.2 + 0.006 * i), W, H, t)
        gains.append(m.mv[0] - before)
    return gains


def test_defaults_are_a_plain_one_to_one_cursor():
    cfg = Config()
    assert cfg.accel_strength == 0 and cfg.long_move_boost == 0
    g = _steady_sweep(cfg)
    assert abs(np.mean(g[45:60]) - np.mean(g[8:16])) / np.mean(g[8:16]) < 0.1  # no speed-up


def test_long_reach_boost_keeps_ramping_up_when_enabled():
    cfg = Config(); cfg.long_move_boost = 0.8
    g = _steady_sweep(cfg)
    assert np.mean(g[45:60]) > 1.4 * np.mean(g[8:16])


def test_constant_speed_when_smart_motion_off():
    cfg = Config(); cfg.smart_motion = False
    g = _steady_sweep(cfg)
    assert abs(np.mean(g[45:60]) - np.mean(g[8:16])) / np.mean(g[8:16]) < 0.1


def test_fast_speed_up_when_enabled():
    cfg = Config(); cfg.accel_strength = 1.0
    slow = _steady_sweep(cfg, 40)[10:30]
    fast = []
    c, m, v = make(cfg); t = 1000.0
    for i in range(40):
        t += 1 / 15; b = m.mv[0]
        c.update(hand({0}, ox=0.2 + 0.02 * i), W, H, t); fast.append(m.mv[0] - b)
    assert np.mean(fast[10:30]) > 3.3 * np.mean(slow)  # 3.3x the hand speed -> more than 3.3x the cursor


def test_boost_resets_after_stopping():
    cfg = Config(); cfg.long_move_boost = 0.8
    c, m, v = make(cfg)
    t = 1000.0
    for i in range(50):
        t += 1 / 15
        c.update(hand({0}, ox=0.2 + 0.006 * i), W, H, t)
    for _ in range(15):  # hold still for a second
        t += 1 / 15
        c.update(hand({0}, ox=0.2 + 0.006 * 50), W, H, t)
    assert c.motion.run < 0.2


def test_peace_slides_vertically_and_horizontally():
    c, m, v = make()
    run(c, [hand({0, 1}, oy=0.75 - 0.01 * i) for i in range(14)])
    assert any(e[:2] == ("scroll", "V") and e[2] > 0 for e in m.log if isinstance(e, tuple))
    c, m, v = make()
    run(c, [hand({0, 1}, ox=0.3 + 0.012 * i) for i in range(14)])
    assert any(e[:2] == ("scroll", "H") for e in m.log if isinstance(e, tuple))


def test_volume_dial_both_directions():
    c, m, v = make()
    run(c, [hand({0, 3})] * 6 + circle(2))
    assert v.sets and v.sets[-1] > 0.30 + 0.12
    c, m, v = make()
    run(c, [hand({0, 3})] * 6 + circle(1, cw=False))
    assert v.sets and v.sets[-1] < 0.30 - 0.05


def test_volume_step_setting():
    cfg = Config(); cfg.volume_step = 25
    c, m, v = make(cfg)
    run(c, [hand({0, 3})] * 6 + circle(1))
    assert v.sets[-1] > 0.30 + 0.15


def test_dropout_keeps_drag_but_long_loss_releases():
    c, m, v = make()
    run(c, [POINT] * 3 + [PINCH] * 4 + [None] * 2 + [PINCH] * 3)
    assert buttons(m) == [("left", "down")]
    c, m, v = make()
    run(c, [POINT] * 3 + [PINCH] * 4 + [None] * 10)
    assert buttons(m) == [("left", "down"), ("left", "up")]


def test_pause_releases_buttons_and_blocks_actions():
    c, m, v = make()
    run(c, [POINT] * 3 + [PINCH] * 5)
    assert buttons(m) == [("left", "down")]
    c.pause("test")
    assert buttons(m)[-1] == ("left", "up") and "cancel" in m.log
    n = len(m.log)
    labels = run(c, [PINCH] * 6 + [POINT] * 6, t0=3000.0)
    assert len(m.log) == n and labels[-1] == "PAUSED"
    c.resume()
    run(c, [POINT] * 6, t0=4000.0)
    assert c.stable == Gesture.POINT


def test_click_storm_guard_auto_pauses():
    c, m, v = make()
    tripped = []
    c.on_trip = tripped.append
    seq = []
    for _ in range(10):
        seq += [POINT] * 5 + [PINCH] * 5
    run(c, seq, dt=1 / 30)
    assert c.paused and tripped
    assert buttons(m)[-1] == ("left", "up")
    n_down = sum(1 for e in buttons(m) if e[1] == "down")
    assert n_down <= 6  # stopped at the threshold


def test_guard_can_be_disabled():
    cfg = Config(); cfg.guard_enabled = False
    c, m, v = make(cfg)
    seq = []
    for _ in range(10):
        seq += [POINT] * 5 + [PINCH] * 5
    run(c, seq, dt=1 / 30)
    assert not c.paused


def test_custom_mapping_pinch_to_right_and_fist_to_left():
    cfg = Config()
    cfg.gestures["pinch"] = Action.RIGHT.value
    cfg.gestures["fist"] = Action.LEFT.value
    c, m, v = make(cfg)
    run(c, [POINT] * 4 + [PINCH] * 5 + [POINT] * 4)
    assert buttons(m)[:2] == [("right", "down"), ("right", "up")]
    c, m, v = make(cfg)
    run(c, [POINT] * 4 + [FIST] * 6 + [POINT] * 4)
    assert buttons(m)[:2] == [("left", "down"), ("left", "up")]


def test_hold_scale_makes_confirmation_slower():
    cfg = Config(); cfg.hold_scale = 2.5
    c, m, v = make(cfg)
    run(c, [POINT] * 4 + [PINCH] * 3)
    assert buttons(m) == []  # 3 frames @15fps = 0.2 s < 0.25 s
    run(c, [PINCH] * 4, t0=1100.0)
