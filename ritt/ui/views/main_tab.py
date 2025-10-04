# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ritt.ui.widgets import CircularProgress
from ritt.ui.theme import GOLD, ACCENT_WARN, ACCENT_RED
from ritt.ui.gold_text import GoldLabel


class StatusChip(QLabel):
    """Lekki „chip” statusu: JAZDA/PRZERWA/OK/WARN/ALERT."""
    def __init__(self, text="OK", color_hex=GOLD, parent=None):
        super().__init__(text, parent)
        self._last_text = None
        self._last_color = None
        self.setAlignment(Qt.AlignCenter)
        f = self.font(); f.setBold(True); self.setFont(f)
        self.setMinimumHeight(28)
        self.setState(text, color_hex)

    def setState(self, text: str, color_hex: str):
        if text == self._last_text and color_hex == self._last_color:
            return
        self._last_text = text; self._last_color = color_hex
        self.setText(text)
        self.setStyleSheet(
            f"color:{color_hex}; background: rgba(212,175,55,0.06); "
            f"border:1px solid {color_hex}; border-radius:14px; padding:6px 12px;"
        )


class MetricTile(QWidget):
    """
    Kafelek metryki:
     - po lewej okrągły wskaźnik (donut),
     - po prawej tytuł (dim) i 2 wiersze treści (wartość + 'pozostało').
    """
    def __init__(self, title: str, base_diameter: int = 150, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._base_d = base_diameter

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        self.g = CircularProgress(max_value=1, value=0, thickness=16, fg=GOLD, text="00:00")
        self.g.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setProperty("dim", True)
        ft = self.lbl_title.font(); ft.setBold(True); self.lbl_title.setFont(ft)
        self.lbl_title.setWordWrap(True)

        self.lbl_value = QLabel("—")
        fv = self.lbl_value.font(); fv.setBold(True); fv.setPointSize(max(12, fv.pointSize()+1))
        self.lbl_value.setFont(fv)

        self.lbl_sub = QLabel(" ")
        self.lbl_sub.setProperty("dim", True)
        self.lbl_sub.setWordWrap(True)

        rl.addWidget(self.lbl_title)
        rl.addWidget(self.lbl_value)
        rl.addWidget(self.lbl_sub)

        lay.addWidget(self.g, 0, Qt.AlignVCenter)
        lay.addWidget(right, 1)

        self._last_factor = None

    def update_metric(self, maxv: int, value: int, text_main: str, text_sub: str, color_fg: str | None = None):
        self.g.setMaximum(maxv)
        self.g.setValue(value)
        self.g.setText(text_main)
        if color_fg:
            self.g.setColors(fg=color_fg)
            self.lbl_value.setStyleSheet(f"color: {color_fg};")
        self.lbl_value.setText(text_main.replace("\n", " "))
        self.lbl_sub.setText(text_sub)

    def setTitle(self, text: str):
        self.lbl_title.setText(text)

    def apply_scale(self, factor: float):
        if self._last_factor is not None and abs(factor - self._last_factor) < 0.03:
            return
        self._last_factor = factor

        d = int(max(110, min(260, self._base_d * factor)))
        th = max(8, int(d * 0.10))
        self.g.setMinimumSize(d, d)
        self.g.setMaximumSize(d, d)
        self.g.setThickness(th)

        f_title = self.lbl_title.font(); f_title.setPointSize(int(max(9, min(14, 12 * factor)))); self.lbl_title.setFont(f_title)
        f_val = self.lbl_value.font();  f_val.setPointSize(int(max(12, min(18, 14 * factor)))); self.lbl_value.setFont(f_val)
        f_sub = self.lbl_sub.font();    f_sub.setPointSize(int(max(10, min(13, 11 * factor)))); self.lbl_sub.setFont(f_sub)


class MainTab(QWidget):
    """
    Layout v2:
     - HERO BAR w JEDNEJ LINII (poziomo): label "Zegar gry" + GoldLabel (dzień, godzina), po prawej chipy.
     - GRID 2x2: 4 kafelki (od przerwy, dzienna, tygodniowa, 2-tyg.).
     - STOPKA: dwie linie (czas jazdy / czas pracy) + ukryty label state.
    API zgodne z wcześniejszymi wersjami.
    """
    def __init__(self, tr: dict):
        super().__init__()
        self.tr = tr
        self._last_clock_full = None
        self._last_factor = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # === HERO BAR (poziomy) ===
        hero = QWidget(); hero.setObjectName("Card")
        hl = QHBoxLayout(hero); hl.setContentsMargins(14, 12, 14, 12); hl.setSpacing(10)

        # lewa część: tytuł + wartość w JEDNEJ linii (poziomo)
        left_row = QWidget(); lr = QHBoxLayout(left_row); lr.setContentsMargins(0,0,0,0); lr.setSpacing(8)
        self.lbl_clock_title = QLabel(self.tr["game_clock"])
        self.lbl_clock_title.setProperty("dim", True)
        ft = self.lbl_clock_title.font(); ft.setBold(True); self.lbl_clock_title.setFont(ft)
        self.lbl_clock_title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lbl_game_clock = GoldLabel("—")
        fbig = QFont(self.lbl_game_clock.font()); fbig.setPointSize(26); fbig.setBold(True)
        self.lbl_game_clock.setFont(fbig)
        self.lbl_game_clock.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_game_clock.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # brak zawijania – wielkość kontrolujemy fontem (patrz _apply_responsive_scale)

        lr.addWidget(self.lbl_clock_title, 0, Qt.AlignVCenter)
        lr.addWidget(self.lbl_game_clock, 1, Qt.AlignVCenter)

        # prawa część: chipy w jednej linii
        right = QWidget(); rl = QHBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(8)
        self.chip_state = StatusChip(self.tr["ok"], GOLD)
        self.chip_speed = StatusChip("0 km/h", GOLD)
        rl.addWidget(self.chip_state)
        rl.addWidget(self.chip_speed)

        hl.addWidget(left_row, 1)
        hl.addWidget(right, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addWidget(hero)

        # === METRICS GRID ===
        grid = QWidget(); grid.setObjectName("Card")
        gl = QGridLayout(grid); gl.setContentsMargins(12,12,12,12); gl.setHorizontalSpacing(12); gl.setVerticalSpacing(12)
        gl.setColumnStretch(0, 1); gl.setColumnStretch(1, 1)

        self.tile_since = MetricTile(f"ℹ️ {self.tr['since_break']}", base_diameter=160)
        self.tile_day   = MetricTile(f"⛽ {self.tr['day_limit']} (9h / 10h×2)", base_diameter=150)
        self.tile_week  = MetricTile(f"📅 {self.tr['week_limit']} (56h)", base_diameter=150)
        self.tile_fort  = MetricTile(f"🗓️ {self.tr['fortnight_limit']} (90h)", base_diameter=150)

        gl.addWidget(self.tile_since, 0, 0)
        gl.addWidget(self.tile_day,   0, 1)
        gl.addWidget(self.tile_week,  1, 0)
        gl.addWidget(self.tile_fort,  1, 1)

        root.addWidget(grid, 1)

        # === FOOTER ===
        footer = QWidget(); footer.setObjectName("Card")
        fl = QHBoxLayout(footer); fl.setContentsMargins(12, 8, 12, 8); fl.setSpacing(10)

        left_f = QWidget(); lfl = QVBoxLayout(left_f); lfl.setContentsMargins(0,0,0,0); lfl.setSpacing(2)
        self.lbl_drive = QLabel("—")
        self.lbl_work  = QLabel("—")
        fsmall = self.lbl_drive.font(); fsmall.setPointSize(max(12, fsmall.pointSize()))
        self.lbl_drive.setFont(fsmall); self.lbl_work.setFont(fsmall)
        lfl.addWidget(self.lbl_drive); lfl.addWidget(self.lbl_work)

        self.lbl_state = QLabel(self.tr["ok"])  # ukryty nośnik zgodności z istniejącą logiką
        self.lbl_state.setVisible(False)

        fl.addWidget(left_f, 1)
        fl.addWidget(self.lbl_state, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addWidget(footer)

        self._apply_responsive_scale(force=True)

    # ========= API wywoływane z main_window =========
    def set_clock_text(self, text: str):
        if text == self._last_clock_full:
            return
        self._last_clock_full = text
        shown = text.split(": ", 1)[1] if (": " in text) else text
        if shown != self.lbl_game_clock.text():
            self.lbl_game_clock.setText(shown)

    def set_since_break(self, maxv: int, value: int, text: str, color_fg: str):
        main = text.split("\n")[0]
        rem  = text.split("\n")[-1] if "\n" in text else ""
        self.tile_since.update_metric(maxv, value, main, rem, color_fg)

    def set_daily(self, maxv: int, value: int, text: str, color_fg: str):
        main = text.split("\n")[0]
        rem  = text.split("\n")[-1] if "\n" in text else ""
        self.tile_day.update_metric(maxv, value, main, rem, color_fg)

    def set_week(self, maxv: int, value: int, text: str):
        main = text.split("\n")[0]
        rem  = text.split("\n")[-1] if "\n" in text else ""
        self.tile_week.update_metric(maxv, value, main, rem, None)

    def set_fortnight(self, maxv: int, value: int, text: str):
        main = text.split("\n")[0]
        rem  = text.split("\n")[-1] if "\n" in text else ""
        self.tile_fort.update_metric(maxv, value, main, rem, None)

    def set_info(self, drive_txt: str, work_txt: str, state_txt: str, state_color: str):
        if drive_txt != self.lbl_drive.text(): self.lbl_drive.setText(drive_txt)
        if work_txt  != self.lbl_work.text():  self.lbl_work.setText(work_txt)
        if state_txt != self.lbl_state.text(): self.lbl_state.setText(state_txt)
        self.lbl_state.setStyleSheet(f"color: {state_color};")

        txt_upper = state_txt.upper()
        if "PRZERWA" in txt_upper:
            self.chip_state.setState(self.tr.get("break", "PRZERWA"), GOLD)
        elif "JAZDA" in txt_upper:
            self.chip_state.setState(self.tr.get("drive", "JAZDA"), GOLD)
        elif "OVER" in txt_upper:
            self.chip_state.setState(state_txt, ACCENT_RED)
        elif "WARN" in txt_upper or "OSTRZ" in txt_upper:
            self.chip_state.setState(state_txt, ACCENT_WARN)
        else:
            self.chip_state.setState(state_txt, GOLD)

    def apply_tr(self, tr: dict):
        self.tr = tr
        self.lbl_clock_title.setText(self.tr["game_clock"])
        self.tile_since.setTitle(f"ℹ️ {self.tr['since_break']}")
        self.tile_day.setTitle(f"⛽ {self.tr['day_limit']} (9h / 10h×2)")
        self.tile_week.setTitle(f"📅 {self.tr['week_limit']} (56h)")
        self.tile_fort.setTitle(f"🗓️ {self.tr['fortnight_limit']} (90h)")

    # ========= Responsywne skalowanie =========
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._apply_responsive_scale()

    def _apply_responsive_scale(self, force: bool = False):
        ref_w, ref_h = 1200.0, 780.0
        w = max(1, self.width()); h = max(1, self.height())
        factor = min(w / ref_w, h / ref_h)
        factor = max(0.65, min(1.8, factor))

        if not force and self._last_factor is not None and abs(factor - self._last_factor) < 0.03:
            return
        self._last_factor = factor

        for t in (self.tile_since, self.tile_day, self.tile_week, self.tile_fort):
            t.apply_scale(factor)

        f = self.lbl_game_clock.font()
        f.setPointSize(int(max(18, min(34, 26 * factor))))
        self.lbl_game_clock.setFont(f)

        # tytuł po lewej – drobna korekta, żeby zmieścił się w poziomie
        ft = self.lbl_clock_title.font()
        ft.setPointSize(int(max(10, min(13, 12 * factor))))
        self.lbl_clock_title.setFont(ft)

    # ======= opcjonalnie (jeśli main_window to wywołuje) =======
    def set_speed(self, kmh: float):
        try:
            v = int(round(kmh))
        except Exception:
            v = 0
        self.chip_speed.setState(f"{v} km/h", GOLD)
