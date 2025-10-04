# ritt/ui/theme.py
from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# --- Kolory brandu i akcenty (zachowana kompatybilność API) ---
GOLD = QColor("#D4AF37")          # główny złoty kolor tekstu
GOLD_DIM = QColor("#9C7F2A")      # złoto zgaszone (disabled)
BLACK_BG = QColor("#0B0B0B")      # tło okna
BASE_BG = QColor("#101010")       # tło pól
MID_BG = QColor("#161616")        # tło wyróżnień/hover

BORDER = QColor("#2B2B2B")        # neutralna ramka
ACCENT_BORDER = GOLD              # ramka aktywna

# Akcenty statusów (na potrzeby istniejących importów)
ACCENT_OK = QColor("#1FA87A")     # zielony OK
ACCENT_INFO = QColor("#3A78C2")   # niebieski info
ACCENT_WARN = QColor("#D39E2E")   # bursztynowe ostrzeżenie (kompatybilny alias)
ACCENT_RED = QColor("#D35454")    # czerwony błąd (kompatybilny alias)

# Zaznaczenie
SELECTION = QColor(212, 175, 55, 76)  # ~30% alpha złota
SELECTION_TEXT = QColor("#000000")

def _set_palette(app: QApplication) -> None:
    pal = QPalette()

    # Tła
    pal.setColor(QPalette.Window, BLACK_BG)
    pal.setColor(QPalette.Base, BASE_BG)
    pal.setColor(QPalette.AlternateBase, MID_BG)
    pal.setColor(QPalette.ToolTipBase, MID_BG)
    pal.setColor(QPalette.ToolTipText, GOLD)

    # Teksty
    pal.setColor(QPalette.WindowText, GOLD)
    pal.setColor(QPalette.Text, GOLD)
    pal.setColor(QPalette.ButtonText, GOLD)
    pal.setColor(QPalette.BrightText, GOLD)
    pal.setColor(QPalette.Link, GOLD)
    pal.setColor(QPalette.LinkVisited, GOLD)

    # PlaceholderText (jeśli dostępny)
    try:
        pal.setColor(QPalette.PlaceholderText, QColor(GOLD.red(), GOLD.green(), GOLD.blue(), 160))
    except Exception:
        pass

    # Zaznaczenie
    pal.setColor(QPalette.Highlight, SELECTION)
    pal.setColor(QPalette.HighlightedText, SELECTION_TEXT)

    # Disabled wariant
    pal.setColor(QPalette.Disabled, QPalette.WindowText, GOLD_DIM)
    pal.setColor(QPalette.Disabled, QPalette.Text, GOLD_DIM)
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, GOLD_DIM)

    app.setPalette(pal)

def _build_qss() -> str:
    return f"""
/* ========== GLOBAL ========== */
QWidget {{
    color: {GOLD.name()};
    background-color: {BLACK_BG.name()};
}}

QToolTip {{
    color: {GOLD.name()};
    background: {MID_BG.name()};
    border: 1px solid {ACCENT_BORDER.name()};
}}

/* ========== TYPOGRAFIA ========== */
QLabel {{
    color: {GOLD.name()};
}}

/* ========== PRZYCISKI ========== */
QPushButton {{
    color: {GOLD.name()};
    background: transparent;
    border: 1px solid {BORDER.name()};
    border-radius: 8px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    border-color: {ACCENT_BORDER.name()};
    background: {MID_BG.name()};
}}
QPushButton:pressed {{
    background: {BASE_BG.name()};
}}
QPushButton:disabled {{
    color: {GOLD_DIM.name()};
    border-color: {BORDER.name()};
}}

/* ========== POLA WEJŚCIOWE ========== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    color: {GOLD.name()};
    background: {BASE_BG.name()};
    selection-background-color: {SELECTION.name()};
    selection-color: {SELECTION_TEXT.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 6px;
    padding: 6px 8px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT_BORDER.name()};
    background: {MID_BG.name()};
}}
/* Placeholder */
QLineEdit[echoMode="0"]::placeholder, QLineEdit::placeholder {{
    color: rgba({GOLD.red()}, {GOLD.green()}, {GOLD.blue()}, 160);
}}

/* ========== CHECKBOX/RADIO ========== */
QCheckBox, QRadioButton {{
    color: {GOLD.name()};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
}}
QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {{
    border: 1px solid {BORDER.name()};
    background: transparent;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    border: 1px solid {ACCENT_BORDER.name()};
    background: {ACCENT_BORDER.name()};
}}

/* ========== COMBOBOX ========== */
QComboBox {{
    color: {GOLD.name()};
    background: {BASE_BG.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 6px;
    padding: 6px 8px;
}}
QComboBox:hover {{
    border-color: {ACCENT_BORDER.name()};
}}
QComboBox QAbstractItemView {{
    color: {GOLD.name()};
    background: {BASE_BG.name()};
    selection-background-color: {SELECTION.name()};
    selection-color: {SELECTION_TEXT.name()};
    border: 1px solid {ACCENT_BORDER.name()};
}}

/* ========== TABS ========== */
QTabWidget::pane {{
    border: 1px solid {BORDER.name()};
    top: -1px;
}}
QTabBar::tab {{
    color: {GOLD.name()};
    background: {BLACK_BG.name()};
    border: 1px solid {BORDER.name()};
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    border-color: {ACCENT_BORDER.name()};
    background: {MID_BG.name()};
}}
QTabBar::tab:hover {{
    border-color: {ACCENT_BORDER.name()};
}}

/* ========== MENU / TOOLBAR ========== */
QMenuBar, QMenu, QToolBar {{
    color: {GOLD.name()};
    background: {BLACK_BG.name()};
}}
QMenu::item:selected {{
    background: {SELECTION.name()};
    color: {SELECTION_TEXT.name()};
}}

/* ========== GROUPBOX ========== */
QGroupBox {{
    color: {GOLD.name()};
    border: 1px solid {BORDER.name()};
    border-radius: 8px;
    margin-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 6px;
    color: {GOLD.name()};
}}

/* ========== STATUSY (opcjonalne klasy) ========== */
.Qpill-ok, .ok {{
    color: {ACCENT_OK.name()};
}}
.Qpill-warn, .warn {{
    color: {ACCENT_WARN.name()};
}}
.Qpill-err, .err {{
    color: {ACCENT_RED.name()};
}}
"""

def apply_theme(app: QApplication, *, base_font_point_size: int = 10) -> None:
    """
    Nakłada czarno‑złoty motyw R‑I‑T‑T na całą aplikację.
    Wywołanie: w main.py tuż po stworzeniu QApplication.
    """
    _set_palette(app)
    app.setStyleSheet(_build_qss())
    font = QFont()
    font.setPointSize(base_font_point_size)
    app.setFont(font)
