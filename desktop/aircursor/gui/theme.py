"""Colours and the application stylesheet."""
BG = "#0A0E14"
SURFACE = "#111823"
SURFACE2 = "#172131"
BORDER = "#222F44"
TEXT = "#E6EDF7"
MUTED = "#8A9BB4"
ACCENT = "#19D3FF"
ACCENT2 = "#7C5CFF"
GREEN = "#2BD67B"
AMBER = "#FFB020"
RED = "#FF4D5E"

QSS = f"""
* {{ font-family: "Inter", "Cantarell", "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#page {{ background: transparent; }}
QToolTip {{ background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; }}

/* sidebar */
QFrame#sidebar {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
QLabel#logo {{ font-size: 20px; font-weight: 800; letter-spacing: 0.5px; }}
QLabel#version {{ color: {MUTED}; font-size: 11px; }}
QPushButton#nav {{ text-align: left; padding: 11px 16px; border: none; border-radius: 10px;
                   background: transparent; color: {MUTED}; font-size: 14px; font-weight: 600; }}
QPushButton#nav:hover {{ background: {SURFACE2}; color: {TEXT}; }}
QPushButton#nav:checked {{ background: {SURFACE2}; color: {ACCENT}; }}

/* cards */
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px; }}
QFrame#card[active="true"] {{ border: 1px solid {ACCENT}; background: {SURFACE2}; }}
QFrame#banner {{ border-radius: 12px; border: 1px solid {BORDER}; background: {SURFACE2}; }}
QFrame#banner[kind="warn"] {{ border: 1px solid {AMBER}; background: #2A2110; }}
QFrame#banner[kind="danger"] {{ border: 1px solid {RED}; background: #2B1217; }}
QLabel#h1 {{ font-size: 24px; font-weight: 800; }}
QLabel#h2 {{ font-size: 15px; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#command {{ font-size: 30px; font-weight: 800; }}
QLabel#emoji {{ font-size: 28px; }}
QLabel#pill {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 11px; padding: 3px 10px; color: {MUTED}; font-size: 12px; font-weight: 600; }}
QLabel#pill[kind="ok"] {{ color: {GREEN}; border-color: #1B5C3A; }}
QLabel#pill[kind="warn"] {{ color: {AMBER}; border-color: #6B4E10; }}
QLabel#pill[kind="danger"] {{ color: {RED}; border-color: #6B1F29; }}

/* buttons */
QPushButton {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 9px 16px; font-weight: 600; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: #566379; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2});
                       border: none; color: #04121A; font-weight: 800; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #5BE0FF, stop:1 #9A82FF); }}
QPushButton#warn {{ background: #2A2110; border: 1px solid {AMBER}; color: {AMBER}; font-weight: 800; }}
QPushButton#danger {{ background: transparent; border: 1px solid #6B1F29; color: {RED}; font-weight: 700; }}
QPushButton#danger:hover {{ background: #2B1217; border-color: {RED}; }}

/* inputs */
QComboBox, QLineEdit {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 9px; padding: 8px 12px; min-height: 18px; }}
QComboBox:hover, QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: {SURFACE2}; border: 1px solid {BORDER}; selection-background-color: {BORDER}; outline: none; padding: 4px; }}
QSlider::groove:horizontal {{ height: 6px; background: {BORDER}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2}); border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #FFFFFF; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}
QProgressBar {{ background: {BORDER}; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QProgressBar[kind="ok"]::chunk {{ background: {GREEN}; }}
QProgressBar[kind="warn"]::chunk {{ background: {AMBER}; }}
QRadioButton {{ spacing: 10px; font-weight: 600; }}
QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 9px; border: 2px solid {MUTED}; background: transparent; }}
QRadioButton::indicator:checked {{ border-color: {ACCENT}; background: qradialgradient(cx:.5,cy:.5,radius:.5, stop:0 {ACCENT}, stop:.55 {ACCENT}, stop:.6 transparent); }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QTextBrowser {{ background: transparent; border: none; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 5px 2px; color: {MUTED}; }}
QListWidget::item:first {{ color: {TEXT}; font-weight: 700; }}
"""
