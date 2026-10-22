"""GUI smoke + behaviour tests, run offscreen (no display needed)."""
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from aircursor.config import Config
from aircursor.engine import EngineState
from aircursor.gestures import Action, Gesture
from aircursor.gui import theme
from aircursor.gui.app import AppContext
from aircursor.gui.floating import FloatPanel
from aircursor.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(theme.QSS)
    return a


@pytest.fixture()
def ctx(app, monkeypatch):
    monkeypatch.setattr(Config, "save", lambda self, *a, **k: None)  # never touch the real settings file
    c = AppContext(app, Config(), live=False)   # engine is created but never started
    c.window, c.panel = MainWindow(c), FloatPanel()
    return c


def state(**kw):
    return EngineState(status="running", live=True, hand=True, **kw)


def test_all_pages_build(ctx):
    assert len(ctx.window.pages) == 5


def test_paused_state_reaches_every_surface(ctx):
    ctx.tick.emit(None, state(paused=True, pause_reason="Safety guard: 6 clicks in 2s", label="PAUSED"))
    ctx.panel.set_state(True, "PAUSED", "Safety guard: 6 clicks in 2s")
    assert ctx.window.pill.text() == "PAUSED"
    assert "Resume" in ctx.window.btn_pause.text()
    assert "PAUSED" in ctx.panel.state.text() and "Resume" in ctx.panel.btn_pause.text()
    ctx.panel.set_state(False, "MOVE", "")
    assert "ACTIVE" in ctx.panel.state.text() and "Pause" in ctx.panel.btn_pause.text()


def test_panic_buttons_are_wired(ctx):
    hits = []
    ctx.panel.pause_toggled.connect(lambda: hits.append("pause"))
    ctx.panel.quit_requested.connect(lambda: hits.append("quit"))
    ctx.panel.show_requested.connect(lambda: hits.append("show"))
    ctx.panel.btn_pause.click(); ctx.panel.btn_quit.click(); ctx.panel.btn_show.click()
    assert hits == ["pause", "quit", "show"]


def test_float_panel_flags_keep_it_on_top(ctx):
    from PySide6.QtCore import Qt
    f = ctx.panel.windowFlags()
    assert f & Qt.WindowStaysOnTopHint and f & Qt.FramelessWindowHint


def test_gesture_mapping_persists_to_config(ctx):
    page = ctx.window.pages[1][1]
    cb = page.combos[Gesture.FIST]
    cb.setCurrentIndex(cb.findData(Action.LEFT.value))
    assert ctx.cfg.gestures["fist"] == "left"
    assert ctx.cfg.action_for(Gesture.FIST) == Action.LEFT


def test_gesture_card_lights_up_for_current_gesture(ctx):
    page = ctx.window.pages[1][1]
    ctx.tick.emit(None, state(gesture="pinch"))
    assert page.cards[Gesture.PINCH].property("active") is True
    assert page.cards[Gesture.FIST].property("active") is False
    ctx.tick.emit(None, state(gesture="pinch", paused=True))
    assert page.cards[Gesture.PINCH].property("active") is False


def test_settings_slider_updates_config_and_reset_restores(ctx):
    page = ctx.window.pages[2][1]
    page.rows["speed"].slider.setValue(page.rows["speed"].slider.maximum())
    assert ctx.cfg.speed == pytest.approx(3.0)
    page.on_toggle("smart_motion", False)
    assert ctx.cfg.smart_motion is False
    page.reset()
    assert ctx.cfg.speed == 1.0 and ctx.cfg.smart_motion is True
    assert page.rows["speed"].value_label.text().startswith("1.00")


def test_camera_page_choice_sets_source(ctx):
    page = ctx.window.pages[3][1]
    page.on_choice(page.phone)
    assert ctx.cfg.camera_source == "url"
    page.on_choice(page.auto)
    assert ctx.cfg.camera_source == "auto"


def test_live_page_shows_no_camera_error(ctx):
    live = ctx.window.pages[0][1]
    ctx.tick.emit(None, EngineState(status="no_camera", message="No camera found.", live=True))
    assert "NO CAMERA" in live.pill_state.text()


def test_mouse_wheel_over_a_dropdown_or_slider_never_changes_a_setting(ctx, app):
    """Scrolling a page must not silently change the combo / slider under the cursor."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    page = ctx.window.pages[1][1]
    cb = page.combos[Gesture.PINCH]
    before = cb.currentIndex()
    ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    app.sendEvent(cb, ev)
    assert cb.currentIndex() == before and ctx.cfg.action_for(Gesture.PINCH) == Action.LEFT
    row = ctx.window.pages[2][1].rows["speed"]
    v = row.slider.value()
    app.sendEvent(row.slider, ev)
    assert row.slider.value() == v


def test_new_gestures_and_commands_have_cards(ctx):
    page = ctx.window.pages[1][1]
    assert Gesture.HOOK in page.cards and len(page.cmd_cards) == 7
    ctx.tick.emit(None, state(command="swipe_right", command_at=__import__("time").time()))
    from aircursor.gestures import Command
    assert page.cmd_cards[Command.SWIPE_RIGHT].property("active") is True
    assert page.cmd_cards[Command.SWIPE_LEFT].property("active") is False


def test_command_mapping_persists_to_config(ctx):
    from aircursor.gestures import Command
    page = ctx.window.pages[1][1]
    cb = page.cmd_combos[Command.WAVE]
    cb.setCurrentIndex(cb.findData(Action.MUTE.value))
    assert ctx.cfg.command_action(Command.WAVE) == Action.MUTE
