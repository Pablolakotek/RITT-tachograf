# ritt/ui/views/breaks_tab.py
from __future__ import annotations
from typing import Any, Callable, Optional, Dict
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QSizePolicy
)

# Kolory z motywu (z fallbackiem)
try:
    from ritt.ui.theme import GOLD as COL_GOLD, ACCENT_RED as COL_DANGER
except Exception:
    COL_GOLD   = "#f2c744"
    COL_DANGER = "#d84a4a"

def _make_tr(tr_like: Any) -> Callable[[str], str]:
    if callable(tr_like):
        return tr_like
    if isinstance(tr_like, dict):
        d: Dict[str, str] = tr_like
        return lambda s: d.get(s, s)
    return lambda s: s

def _to_hex(c: Any, fallback: str) -> str:
    """QColor/str -> #rrggbb"""
    try:
        from PySide6.QtGui import QColor
        if isinstance(c, QColor):
            return c.name()
        q = QColor(c)
        if q.isValid():
            return q.name()
    except Exception:
        pass
    s = str(c)
    return s if s.startswith("#") else fallback

class BreaksTab(QWidget):
    """
    Zakładka 'Przerwy' – kompaktowe przyciski (outline), żetony statusu 45′ (15/30),
    blokada 15→30, historia na dole + 'Wyczyść historię'.
    Sygnały: break15Clicked, break30Clicked, break45Clicked,
             breakDaily9Clicked, breakWeekly24Clicked, breakWeekly45Clicked,
             breakStopClicked, clearHistoryClicked
    """

    break15Clicked = Signal()
    break30Clicked = Signal()
    break45Clicked = Signal()
    breakDaily9Clicked = Signal()
    breakWeekly24Clicked = Signal()
    breakWeekly45Clicked = Signal()
    breakStopClicked = Signal()
    clearHistoryClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None, tr: Any = None):
        super().__init__(parent)
        self._tr = _make_tr(tr)
        self._target_min: Optional[int] = None

        # Stany włączania / podświetlenia
        self._global_enabled: bool = True
        self._split_lock_after_15: bool = False
        self._active_key: Optional[str] = None

        # --- Top: status + licznik ---
        self.lbl_status = QLabel(self._tr("Brak przerwy"))
        self.lbl_countdown = QLabel("--:--")
        self.lbl_countdown.setStyleSheet("font-size: 24px; font-weight: 700; letter-spacing: .2px;")

        # --- Pasek statusu 45′: [15′] [30′] ---
        bar = QHBoxLayout(); bar.setSpacing(6)
        self.lbl_split_hdr = QLabel(self._tr("Status 45′:"))
        self.chip15 = QPushButton("15′"); self.chip15.setProperty("kind","chip"); self.chip15.setProperty("chipstate","todo")
        self.chip30 = QPushButton("30′"); self.chip30.setProperty("kind","chip"); self.chip30.setProperty("chipstate","todo")
        for ch in (self.chip15, self.chip30):
            ch.setEnabled(False); ch.setCursor(Qt.ArrowCursor)
            ch.setMinimumHeight(22); ch.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        bar.addWidget(self.lbl_split_hdr); bar.addWidget(self.chip15); bar.addWidget(self.chip30); bar.addStretch(1)

        # --- Przyciski startu przerw (kompaktowe, outline) ---
        self.btn15  = QPushButton(self._tr("⏱ 15′"));  self.btn15.setProperty("kind", "outline"); self.btn15.setProperty("key","15")
        self.btn30  = QPushButton(self._tr("⏱ 30′"));  self.btn30.setProperty("kind", "outline"); self.btn30.setProperty("key","30")
        self.btn45  = QPushButton(self._tr("⏱ 45′"));  self.btn45.setProperty("kind", "outline"); self.btn45.setProperty("key","45")

        self.btnD9  = QPushButton(self._tr("⏳ 9 h"));  self.btnD9.setProperty("kind", "outline");  self.btnD9.setProperty("key","9h")
        self.btnW24 = QPushButton(self._tr("⏳ 24 h")); self.btnW24.setProperty("kind", "outline"); self.btnW24.setProperty("key","24h")
        self.btnW45 = QPushButton(self._tr("⏳ 45 h")); self.btnW45.setProperty("kind", "outline"); self.btnW45.setProperty("key","45h")

        self.btnStop  = QPushButton(self._tr("🛑 Zakończ"));          self.btnStop.setProperty("kind", "danger")
        self.btnClear = QPushButton(self._tr("🧹 Wyczyść historię")); self.btnClear.setProperty("kind", "outline")

        for b in (self.btn15, self.btn30, self.btn45, self.btnD9, self.btnW24, self.btnW45, self.btnStop, self.btnClear):
            b.setMinimumHeight(34); b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); b.setCursor(Qt.PointingHandCursor)

        # --- Layout ---
        lay = QVBoxLayout(self); lay.setSpacing(8)
        lay.addWidget(self.lbl_status); lay.addWidget(self.lbl_countdown); lay.addLayout(bar)

        grid = QGridLayout(); grid.setHorizontalSpacing(6); grid.setVerticalSpacing(6)
        grid.addWidget(self.btn15, 0, 0); grid.addWidget(self.btn30, 0, 1); grid.addWidget(self.btn45, 0, 2)
        grid.addWidget(self.btnD9,  1, 0); grid.addWidget(self.btnW24, 1, 1); grid.addWidget(self.btnW45, 1, 2)
        for i in range(3): grid.setColumnStretch(i, 1)
        lay.addLayout(grid)

        row_actions = QHBoxLayout(); row_actions.addStretch(1); row_actions.addWidget(self.btnStop); lay.addLayout(row_actions)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels([
            self._tr("Start"), self._tr("Koniec"),
            self._tr("Typ"), self._tr("Czas"),
            self._tr("Efekt"), self._tr("Zakończenie"),
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False); self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setColumnWidth(0, 90); self.table.setColumnWidth(1, 90); self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 90); self.table.setColumnWidth(4, 220); self.table.setColumnWidth(5, 160)
        lay.addWidget(self.table, 1)

        footer = QHBoxLayout(); footer.addStretch(1); footer.addWidget(self.btnClear); lay.addLayout(footer)

        # --- Sygnały ---
        self.btn15.clicked.connect(self.break15Clicked.emit)
        self.btn30.clicked.connect(self.break30Clicked.emit)
        self.btn45.clicked.connect(self.break45Clicked.emit)
        self.btnD9.clicked.connect(self.breakDaily9Clicked.emit)
        self.btnW24.clicked.connect(self.breakWeekly24Clicked.emit)
        self.btnW45.clicked.connect(self.breakWeekly45Clicked.emit)
        self.btnStop.clicked.connect(self.breakStopClicked.emit)
        self.btnClear.clicked.connect(self.clearHistoryClicked.emit)

        # delegat zgodności (opcjonalny)
        self.btn15.clicked.connect(lambda: self._delegate_on_break_button(15))
        self.btn30.clicked.connect(lambda: self._delegate_on_break_button(30))
        self.btn45.clicked.connect(lambda: self._delegate_on_break_button(45))
        self.btnD9.clicked.connect(lambda: self._delegate_on_break_button(9*60))
        self.btnW24.clicked.connect(lambda: self._delegate_on_break_button(24*60))
        self.btnW45.clicked.connect(lambda: self._delegate_on_break_button(45*60))
        self.btnStop.clicked.connect(lambda: self._delegate_on_break_button(0))

        self._apply_button_styles()
        self._apply_enabled_states()
        self._apply_active_highlight()
        self.set_split_status(False, False)

    # --- Delegat zgodności ---
    def _delegate_on_break_button(self, minutes: int):
        mw = self.window()
        if hasattr(mw, "on_break_button"):
            try: mw.on_break_button(minutes)
            except Exception: pass

    # --- Pomocnicze formatowanie ---
    def _fmt_amount(self, minutes: int) -> str:
        if minutes >= 60 and minutes % 60 == 0: return f"{minutes // 60} h"
        return f"{minutes}′"

    def set_running_status(self, minutes: int):
        self.lbl_status.setText(self._tr(f"Przerwa {self._fmt_amount(minutes)} trwa"))

    # --- Wywoływane z MainWindow ---
    def show_break_started(self, minutes: int):
        self._target_min = minutes
        self.lbl_status.setText(self._tr(f"Przerwa {self._fmt_amount(minutes)} rozpoczęta"))

    def show_break_stopped(self):
        self._target_min = None
        self.lbl_status.setText(self._tr("Brak przerwy"))
        self.lbl_countdown.setText("--:--")

    def update_countdown(self, remaining_sec: int, target_min: int | None):
        if not target_min or remaining_sec <= 0:
            self.show_break_stopped(); return
        if target_min >= 60:
            hh = remaining_sec // 3600; mm = (remaining_sec % 3600) // 60
            self.lbl_countdown.setText(f"{hh:02d}:{mm:02d}")
        else:
            mm = remaining_sec // 60; ss = remaining_sec % 60
            self.lbl_countdown.setText(f"{mm:02d}:{ss:02d}")
        if self._target_min != target_min:
            self.set_running_status(target_min); self._target_min = target_min

    # --- Logika włączania (global + split lock) ---
    def set_global_enabled(self, enabled: bool):
        self._global_enabled = bool(enabled); self._apply_enabled_states()

    def set_split_lock_after_15(self, locked: bool):
        self._split_lock_after_15 = bool(locked); self._apply_enabled_states()

    def _apply_enabled_states(self):
        enable = self._global_enabled
        for b in (self.btn15, self.btn30, self.btn45, self.btnD9, self.btnW24, self.btnW45):
            b.setEnabled(enable)
        if enable and self._split_lock_after_15:
            self.btn15.setEnabled(False)
            self.btn45.setEnabled(False)
            self.btn30.setEnabled(True)

    # --- Podświetlenie aktywnego przycisku ---
    def highlight_button(self, key: Optional[str]):
        self._active_key = key; self._apply_active_highlight()

    def _apply_active_highlight(self):
        for b in (self.btn15, self.btn30, self.btn45, self.btnD9, self.btnW24, self.btnW45):
            b.setProperty("sel", False); b.style().unpolish(b); b.style().polish(b)
        mapping = {"15": self.btn15, "30": self.btn30, "45": self.btn45, "9h": self.btnD9, "24h": self.btnW24, "45h": self.btnW45}
        if self._active_key in mapping:
            b = mapping[self._active_key]
            b.setProperty("sel", True); b.style().unpolish(b); b.style().polish(b)

    def set_break_button_text(self, active: bool, tr: Any | None = None):
        if tr is not None: self._tr = _make_tr(tr)
        self.set_global_enabled(not active)

    def set_starters_enabled(self, enabled: bool):
        self.set_global_enabled(enabled)

    def reset_countdown(self):
        self.lbl_countdown.setText("--:--")

    # --- Status 45′: ustawienie żetonów (NOWE API) ---
    def set_split_status(self, chip15_done: bool, chip30_done: bool):
        self._set_chip_state(self.chip15, "done" if chip15_done else "todo")
        self._set_chip_state(self.chip30, "done" if chip30_done else "todo")

    def _set_chip_state(self, chip: QPushButton, state: str):
        chip.setProperty("chipstate", state)
        chip.style().unpolish(chip); chip.style().polish(chip)

    # --- Historia ---
    def append_history(self, start_txt: str, end_txt: str, ttxt: str, dur_txt: str, eff_txt: str, end_reason: str):
        row = 0
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(start_txt))
        self.table.setItem(row, 1, QTableWidgetItem(end_txt))
        self.table.setItem(row, 2, QTableWidgetItem(ttxt))
        self.table.setItem(row, 3, QTableWidgetItem(dur_txt))
        self.table.setItem(row, 4, QTableWidgetItem(eff_txt))
        self.table.setItem(row, 5, QTableWidgetItem(end_reason))

    def clear_history(self):
        self.table.setRowCount(0)

    # --- Styl przycisków + żetonów ---
    def _apply_button_styles(self):
        gold   = _to_hex(COL_GOLD,   "#f2c744")
        danger = _to_hex(COL_DANGER, "#d84a4a")
        gold_dim   = "#caa43a"
        gold_light = "#ffe27a"
        black      = "#0b0b0b"
        black_h    = "#111214"
        black_p    = "#090909"

        base = f"""
        QPushButton {{
            border-radius: 10px;
            padding: 6px 10px;
            font-weight: 600;
            letter-spacing: .2px;
        }}
        QPushButton:disabled {{ opacity: .55; }}

        /* Outline: czarne tło, złota obwódka i złoty tekst */
        QPushButton[kind="outline"] {{
            background: {black};
            color: {gold};
            border: 1.5px solid {gold};
        }}
        QPushButton[kind="outline"]:hover {{
            background: {black_h};
            color: {gold_light};
            border-color: {gold_light};
        }}
        QPushButton[kind="outline"]:pressed {{
            background: {black_p};
            color: {gold_dim};
            border-color: {gold_dim};
        }}

        /* Zaznaczenie aktywnego */
        QPushButton[sel="true"][kind="outline"] {{
            border-width: 2px;
            border-color: {gold_light};
        }}

        /* Chipy statusu 45′ */
        QPushButton[kind="chip"] {{
            border-radius: 9px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 12px;
        }}
        QPushButton[kind="chip"][chipstate="todo"] {{
            background: transparent;
            color: {gold};
            border: 1.2px solid {gold};
        }}
        QPushButton[kind="chip"][chipstate="done"] {{
            background: {gold};
            color: {black};
            border: 1.2px solid {gold};
        }}

        /* Zakończ – czerwony */
        QPushButton[kind="danger"] {{
            background: {danger};
            color: white;
            border: 1.5px solid {danger};
        }}
        QPushButton[kind="danger"]:hover {{ filter: brightness(0.96); }}
        QPushButton[kind="danger"]:pressed {{ filter: brightness(0.90); }}
        """
        self.setStyleSheet(base)

    # --- i18n ---
    def apply_tr(self, tr_like: Any):
        self._tr = _make_tr(tr_like)
        self.lbl_status.setText(self._tr("Brak przerwy") if self._target_min is None
                                else self._tr(f"Przerwa {self._fmt_amount(self._target_min)} trwa"))
        self.lbl_split_hdr.setText(self._tr("Status 45′:"))
        self.btn15.setText(self._tr("⏱ 15′"))
        self.btn30.setText(self._tr("⏱ 30′"))
        self.btn45.setText(self._tr("⏱ 45′"))
        self.btnD9.setText(self._tr("⏳ 9 h"))
        self.btnW24.setText(self._tr("⏳ 24 h"))
        self.btnW45.setText(self._tr("⏳ 45 h"))
        self.btnStop.setText(self._tr("🛑 Zakończ"))
        self.btnClear.setText(self._tr("🧹 Wyczyść historię"))
        self.table.setHorizontalHeaderLabels([
            self._tr("Start"), self._tr("Koniec"),
            self._tr("Typ"), self._tr("Czas"),
            self._tr("Efekt"), self._tr("Zakończenie"),
        ])
