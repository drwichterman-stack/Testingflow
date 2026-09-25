"""Light and dark themes: color tokens, Qt palette, and stylesheet.

All colors are defined once here as tokens. Widgets opt into roles with
objectName or a dynamic "role" property (for example role="primary" on
the main call-to-action button).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from .. import prefs as prefs_mod

LIGHT = {
    "bg": "#f3f5f8", "surface": "#ffffff", "surface2": "#eef2f7", "border": "#d3dae4",
    "text": "#1b2433", "muted": "#5a6a7e", "primary": "#1f5fa8", "primary_hover": "#184d8a",
    "primary_text": "#ffffff", "ok": "#1b7a4b", "ok_bg": "#e3f4ea", "warn": "#8a5d00",
    "warn_bg": "#fff4d6", "danger": "#b42318", "danger_bg": "#fdecea",
    "sidebar": "#14253b", "sidebar_text": "#c5d1e0", "sidebar_active": "#1f5fa8",
    "selection": "#d6e4f5", "selection_text": "#0e2440",
}
DARK = {
    "bg": "#0f141b", "surface": "#171f29", "surface2": "#1e2833", "border": "#2c3846",
    "text": "#e5eaf1", "muted": "#94a3b6", "primary": "#4a8fe0", "primary_hover": "#5c9deb",
    "primary_text": "#0b1220", "ok": "#4cc38a", "ok_bg": "#15301f", "warn": "#e0b04f",
    "warn_bg": "#33280f", "danger": "#f07167", "danger_bg": "#3a1a18",
    "sidebar": "#0a0f15", "sidebar_text": "#a9b6c6", "sidebar_active": "#2a5c96",
    "selection": "#23466f", "selection_text": "#ffffff",
}

_current: dict = LIGHT


def tokens() -> dict:
    return _current


def is_dark(pref: str) -> bool:
    if pref == "dark":
        return True
    if pref == "light":
        return False
    hints = QApplication.styleHints()
    try:
        return hints.colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def stylesheet(t: dict, pt: float) -> str:
    return f"""
    QWidget {{ color: {t['text']}; font-size: {pt:.1f}pt; }}
    QMainWindow, QDialog {{ background: {t['bg']}; }}
    QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']};
               padding: 6px; }}
    QFrame#card, QGroupBox {{ background: {t['surface']}; border: 1px solid {t['border']};
                             border-radius: 10px; }}
    QGroupBox {{ margin-top: 14px; padding: 12px 10px 8px 10px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px;
                       color: {t['primary']}; }}
    QLabel[role="muted"] {{ color: {t['muted']}; }}
    QLabel[role="h1"] {{ font-size: {pt * 1.75:.1f}pt; font-weight: 700; }}
    QLabel[role="h2"] {{ font-size: {pt * 1.3:.1f}pt; font-weight: 600; }}
    QLabel[role="stat"] {{ font-size: {pt * 2.4:.1f}pt; font-weight: 700; color: {t['primary']}; }}
    QLabel[role="banner-warn"] {{ background: {t['warn_bg']}; color: {t['warn']};
                                 border-radius: 6px; padding: 8px 10px; }}
    QLabel[role="banner-ok"] {{ background: {t['ok_bg']}; color: {t['ok']};
                               border-radius: 6px; padding: 8px 10px; }}
    QLabel[role="banner-danger"] {{ background: {t['danger_bg']}; color: {t['danger']};
                                   border-radius: 6px; padding: 8px 10px; font-weight: 600; }}
    QPushButton, QToolButton {{
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
        padding: 8px 16px; min-height: 22px; }}
    QPushButton:hover, QToolButton:hover {{ border-color: {t['primary']}; }}
    QPushButton:disabled, QToolButton:disabled {{ color: {t['muted']}; background: {t['surface2']}; }}
    QPushButton[role="primary"], QToolButton[role="primary"] {{
        background: {t['primary']}; color: {t['primary_text']}; border: none; font-weight: 600; }}
    QPushButton[role="primary"]:hover, QToolButton[role="primary"]:hover {{
        background: {t['primary_hover']}; }}
    QPushButton[role="danger"] {{ color: {t['danger']}; }}
    QPushButton[role="danger"]:hover {{ border-color: {t['danger']}; }}
    QPushButton[role="big"], QToolButton[role="big"] {{ padding: 12px 20px; min-height: 30px; }}
    QToolButton::menu-indicator {{ image: none; width: 0px; }}
    QPushButton[role="seg"] {{ padding: 5px 10px; border-radius: 6px; min-height: 18px; }}
    QPushButton[role="seg"]:checked {{ background: {t['primary']}; color: {t['primary_text']};
        border-color: {t['primary']}; font-weight: 600; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox, QDateEdit, QSpinBox {{
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 6px;
        padding: 6px 8px; selection-background-color: {t['selection']};
        selection-color: {t['selection_text']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
        border: 2px solid {t['primary']}; }}
    QComboBox QAbstractItemView {{ background: {t['surface']};
        selection-background-color: {t['selection']}; selection-color: {t['selection_text']}; }}
    QTableWidget, QListWidget {{ background: {t['surface']}; border: 1px solid {t['border']};
        border-radius: 8px; gridline-color: {t['border']};
        selection-background-color: {t['selection']}; selection-color: {t['selection_text']};
        alternate-background-color: {t['surface2']}; }}
    QTableWidget::item, QListWidget::item {{ padding: 6px; }}
    QHeaderView::section {{ background: {t['surface2']}; color: {t['muted']}; border: none;
        border-bottom: 1px solid {t['border']}; padding: 6px; font-weight: 600; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QStatusBar {{ background: {t['surface']}; border-top: 1px solid {t['border']}; }}
    QMenuBar {{ background: {t['surface']}; }}
    QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; }}
    QMenu::item {{ padding: 6px 20px; }}
    QMenu::item:selected {{ background: {t['selection']}; color: {t['selection_text']}; }}
    QWidget#sidebar {{ background: {t['sidebar']}; }}
    QWidget#sidebar QLabel {{ color: {t['sidebar_text']}; }}
    QWidget#sidebar QPushButton {{ background: transparent; color: {t['sidebar_text']};
        border: none; border-radius: 8px; text-align: left; padding: 12px 14px;
        font-size: {pt * 1.05:.1f}pt; }}
    QWidget#sidebar QPushButton:hover {{ background: rgba(255,255,255,0.07); }}
    QWidget#sidebar QPushButton:checked {{ background: {t['sidebar_active']}; color: #ffffff;
        font-weight: 600; }}
    QSplitter::handle {{ background: {t['bg']}; }}
    """


def apply(app: QApplication, prefs: dict | None = None) -> dict:
    global _current
    prefs = prefs or prefs_mod.load()
    _current = DARK if is_dark(prefs["theme"]) else LIGHT
    t = _current
    app.setStyle("Fusion")
    pal = QPalette()
    for role, key in ((QPalette.ColorRole.Window, "bg"), (QPalette.ColorRole.Base, "surface"),
                      (QPalette.ColorRole.AlternateBase, "surface2"),
                      (QPalette.ColorRole.Text, "text"), (QPalette.ColorRole.WindowText, "text"),
                      (QPalette.ColorRole.ButtonText, "text"),
                      (QPalette.ColorRole.Button, "surface"),
                      (QPalette.ColorRole.Highlight, "selection"),
                      (QPalette.ColorRole.HighlightedText, "selection_text"),
                      (QPalette.ColorRole.ToolTipBase, "surface"),
                      (QPalette.ColorRole.ToolTipText, "text"),
                      (QPalette.ColorRole.PlaceholderText, "muted"),
                      (QPalette.ColorRole.Link, "primary")):
        pal.setColor(role, QColor(t[key]))
    app.setPalette(pal)
    base = 13.0 if app.platformName() == "cocoa" else 10.5
    pt = base * prefs_mod.FONT_SCALES[prefs["font_scale"]]
    f = QFont(app.font())
    f.setPointSizeF(pt)
    app.setFont(f)
    app.setStyleSheet(stylesheet(t, pt))
    return t


def html_table_css() -> str:
    """CSS for score tables rendered in QTextBrowser (follows the theme)."""
    t = _current
    return (f"<style>table {{ border-collapse: collapse; }} "
            f"td, th {{ border: 1px solid {t['border']}; padding: 4px 8px; }} "
            f"th {{ background: {t['surface2']}; color: {t['muted']}; text-align: left; }} "
            f".warn {{ color: {t['warn']}; }} .danger {{ color: {t['danger']}; font-weight: 600; }} "
            f".muted {{ color: {t['muted']}; }}</style>")


def set_role(widget, role: str):
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget
