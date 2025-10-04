# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import threading
from datetime import datetime
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSizeGrip, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, QSettings, QEvent, QStandardPaths

from ritt.ui.effects import install_3d_effects
from ritt.ui.brand import BrandHeader
from ritt.telemetry.factory import build_provider

from ritt.config import CFG
from ritt.i18n import get_tr, LANGS
from ritt.api import NetSignals, NetClient

from ritt.breaks import (
    BreakManager, DRIVE_BEFORE_BREAK_MAX, WARN_REMAIN_BREAK_MIN,
)

from ritt.overlay import MiniOverlay
from ritt.telemetry.service import TelemetryService
from ritt.telemetry.store import TelemetryDB
from ritt.telemetry.mappers.funbit_v9 import normalize_funbit_v9

from ritt.ui.theme import GOLD, ACCENT_WARN, ACCENT_RED
from ritt.ui.views.main_tab import MainTab
from ritt.ui.views.breaks_tab import BreaksTab
from ritt.ui.views.overlay_tab import OverlayTab
from ritt.ui.widgets import CircularProgress

DAILY_DRIVE_LIMIT_SEC = 9 * 3600
WARN_REMAIN_DAILY_MIN = 15 * 60  # sekundy

WDAY = {
    "pl": ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"],
    "en": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
    "de": ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"],
    "es": ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"],
    "it": ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"],
}

def _wday_name(lang: str, idx: int | None) -> str:
    if idx is None: return "—"
    arr = WDAY.get(lang, WDAY["en"])
    return arr[int(idx) % 7]

def fmt_hm(sec: int) -> str:
    if sec < 0: sec = 0
    h = sec // 3600; m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"

def fmt_mmss(sec: int) -> str:
    if sec < 0: sec = 0
    m = sec // 60; s = sec % 60
    return f"{m:02d}:{s:02d}"


class TachographWindow(QMainWindow):
    def __init__(self, lang="pl"):
        super().__init__()
        self.lang = lang if lang in LANGS else "pl"
        self.tr = get_tr(self.lang)

        # cache tekstów do statusu
        self._last_clock_text = None
        self._last_drive_txt = ""
        self._last_work_txt = ""
        self._last_status_code = None  # do throttlingu komunikatów

        # okno
        self.setWindowTitle("RITT Tachograph — PRO")
        self.resize(1200, 780); self.setMinimumSize(900, 600)
        self.statusBar().addPermanentWidget(QSizeGrip(self))

        # TELEMETRIA: provider -> service(mapper+db)
        base_provider = build_provider()
        self.telemetry_service = TelemetryService(
            provider=base_provider,
            mapper=normalize_funbit_v9,
            db=TelemetryDB("telemetry.sqlite")
        )

        self.speed_kmh = 0.0
        self.game_time_unix = 0
        self._last_game_time_unix = 0
        self.game_minutes: int | None = None
        self._last_game_minutes: int | None = None
        self.game_time_iso: str | None = None
        self._last_game_iso_dt: datetime | None = None  # Fallback do liczenia dt z ISO

        # sygnały do twardych przerw
        self.engine_on = False
        self.parking_brake = False

        # Liczniki
        self.driving_seconds = 0
        self.working_seconds = 0
        self.break_seconds = 0
        self.daily_drive_sec = 0
        self.week_drive_sec = 0
        self.fortnight_drive_sec = 0

        # Przerwy
        self.breaks = BreakManager()
        self.active_break_total = 0
        self.active_break_remaining = 0

        # --- znacznik czasu START przerwy (do historii) ---
        self._break_start_display: str | None = None  # np. "14:37"
        self._break_start_iso: str | None = None      # ISO czasu gry / UTC

        # --- historia w pamięci + ścieżka pliku ---
        self._history: List[Dict[str, Any]] = []
        self._history_file = self._history_path()

        # === UI ===
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(14,10,14,10); root.setSpacing(10)
        self.brand = BrandHeader()
        root.addWidget(self.brand, 0)

        self._show_logged_user_on_brand()

        # Topbar
        top_card = QWidget(); top_card.setObjectName("Card")
        top = QHBoxLayout(top_card); top.setContentsMargins(10,8,10,8)
        self.lang_box = QComboBox()
        for code in LANGS: self.lang_box.addItem(code.upper(), code)
        self.lang_box.setCurrentIndex(LANGS.index(self.lang))
        self.lang_box.currentIndexChanged.connect(self.change_lang)
        lbl_lang = QLabel(self.tr["lang"])
        self.ping_btn = QPushButton("🚦 " + self.tr["ping"]); self.ping_btn.setProperty("gold", True)
        self.ping_btn.clicked.connect(self.test_connection)
        top.addWidget(lbl_lang); top.addWidget(self.lang_box); top.addStretch(1); top.addWidget(self.ping_btn)
        root.addWidget(top_card)

        # Zakładki
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        self.mainTab = MainTab(self.tr)
        self.breaksTab = BreaksTab(self)
        self.overlayTab = OverlayTab(self.tr)
        self.tabs.addTab(self.mainTab, self.tr["tab_main"])
        self.tabs.addTab(self.breaksTab, self.tr["tab_breaks"])
        self.tabs.addTab(self.overlayTab, self.tr["tab_overlay"])
        install_3d_effects(self)

        # Sygnały z BreaksTab
        self.breaksTab.break15Clicked.connect(lambda: self.start_fixed_break(15*60))
        self.breaksTab.break30Clicked.connect(lambda: self.start_fixed_break(30*60))
        self.breaksTab.break45Clicked.connect(lambda: self.start_fixed_break(45*60))
        self.breaksTab.breakDaily9Clicked.connect(lambda: self.start_fixed_break(9*3600))
        self.breaksTab.breakWeekly24Clicked.connect(lambda: self.start_fixed_break(24*3600))
        self.breaksTab.breakWeekly45Clicked.connect(lambda: self.start_fixed_break(45*3600))
        self.breaksTab.breakStopClicked.connect(self.stop_break)
        self.breaksTab.clearHistoryClicked.connect(self._history_clear)

        # Overlay
        self.overlayTab.openOverlayClicked.connect(self.handle_overlay)

        # API
        self.netSignals = NetSignals()
        self.net = NetClient(self.netSignals)
        self.netSignals.pointsUpdated.connect(self.on_points_updated)
        self.netSignals.netError.connect(lambda err: self.statusBar().showMessage(f"Sieć: {err}", 3000))

        # Timery
        self.game_tick = QTimer(self); self.game_tick.timeout.connect(self.tick_from_game); self.game_tick.start(250)
        self.telemetry_timer = QTimer(self); self.telemetry_timer.timeout.connect(self.send_status_bg); self.telemetry_timer.start(2000)
        self.points_timer = QTimer(self); self.points_timer.timeout.connect(self.fetch_points_bg); self.points_timer.start(5000)

        self.overlay = None
        self.refresh_labels(force=True)

        # QSettings
        self._settings = QSettings("RITT", "Tachograph")
        self._restore_window()

        # Wczytaj historię z pliku
        self._history_load()

        # Płynniejszy resize
        self._interactive_resizing = False
        self._resize_idle = QTimer(self); self._resize_idle.setSingleShot(True)
        self._resize_idle.setInterval(160)
        self._resize_idle.timeout.connect(self._end_interactive_resize)
        self.installEventFilter(self)

    # ---------- Pomocnicze ----------
    def _refresh_telemetry_now(self):
        try:
            d: dict[str, Any] = self.telemetry_service.poll_normalized() or {}
            self.speed_kmh = float(d.get("speed_kmh") or 0.0)
            self.engine_on = bool(d.get("engine_on", self.engine_on))
            self.parking_brake = bool(d.get("parking_brake", self.parking_brake))
            if d.get("game_time_iso") is not None:
                self.game_time_iso = d.get("game_time_iso")
        except Exception as e:
            print(f"[click-refresh] {e}")

    # --- Historia: ścieżka / load / save / append / clear ---
    def _history_path(self) -> str:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.getcwd()
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        return os.path.join(base, "break_history.json")

    def _history_load(self):
        self.breaksTab.clear_history()
        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, "r", encoding="utf-8") as f:
                    data = json.load(f) or []
                if isinstance(data, list):
                    self._history = data
                else:
                    self._history = []
            else:
                self._history = []
        except Exception as e:
            print(f"[history_load] {e}")
            self._history = []

        # Odśwież tabelę z pamięci
        for rec in reversed(self._history):  # najnowsze na górze
            self.breaksTab.append_history(
                rec.get("start_display","—"),
                rec.get("end_display","—"),
                rec.get("type_text","—"),
                rec.get("duration_text","—"),
                rec.get("effects_text","—"),
                rec.get("end_reason","—"),
            )

    def _history_save(self):
        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[history_save] {e}")

    def _history_append(self, record: Dict[str, Any]):
        self._history.insert(0, record)
        self._history_save()

    def _history_clear(self):
        self._history = []
        self._history_save()
        self.breaksTab.clear_history()
        self.statusBar().showMessage("Historia przerw wyczyszczona.", 2000)

    # ---------- Zapamiętywanie okna ----------
    def _restore_window(self):
        try:
            geom = self._settings.value("geometry")
            state = self._settings.value("windowState")
            last_lang = self._settings.value("lang")
            last_tab = self._settings.value("tab_index")
            if geom is not None: self.restoreGeometry(geom)
            if state is not None: self.restoreState(state)
            if last_lang in LANGS:
                self.lang = last_lang
                self.tr = get_tr(self.lang)
                self.lang_box.setCurrentIndex(LANGS.index(self.lang))
            if isinstance(last_tab, int) and 0 <= last_tab < self.tabs.count():
                self.tabs.setCurrentIndex(last_tab)
        except Exception:
            pass

    def set_logged_user(self, login: str, name: str | None = None, driver_id: str | None = None):
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("RITT", "Auth")
            if login: s.setValue("username", login)
            if name: s.setValue("display_name", name)
            s.sync()
        except Exception:
            pass

        try:
            from ritt.config import CFG
            if driver_id is None:
                driver_id = CFG.get("driver_id")
        except Exception:
            pass

        try:
            self.brand.set_user_display(login=login, name=name, driver_id=driver_id)
        except Exception:
            pass

    def _show_logged_user_on_brand(self):
        from PySide6.QtCore import QSettings

        login = None; name = None; driver_id = None
        s_auth = QSettings("RITT", "Auth")
        for k in ("username","login","user_login","remember_username","remember_login"):
            v = s_auth.value(k);  login = login or (str(v) if v else None)
        for k in ("display_name","name","fullname"):
            v = s_auth.value(k);  name = name or (str(v) if v else None)

        s_app = QSettings("RITT", "Tachograph")
        for k in ("auth_username","username","login"):
            v = s_app.value(k);  login = login or (str(v) if v else None)
        for k in ("auth_display_name","display_name","name"):
            v = s_app.value(k);  name = name or (str(v) if v else None)

        try:
            from ritt.config import CFG
            driver_id = CFG.get("driver_id") or driver_id
            login = login or CFG.get("driver_login") or CFG.get("username") or CFG.get("login")
            name = name or CFG.get("driver_name") or CFG.get("name")
        except Exception:
            pass

        try:
            self.brand.set_user_display(login=login, name=name, driver_id=driver_id)
        except Exception:
            pass

    def closeEvent(self, e):
        try:
            self._settings.setValue("geometry", self.saveGeometry())
            self._settings.setValue("windowState", self.saveState())
            self._settings.setValue("lang", self.lang)
            self._settings.setValue("tab_index", self.tabs.currentIndex())
            self._settings.sync()
        except Exception:
            pass
        super().closeEvent(e)

    # ---------- Event filter (płynny resize) ----------
    def eventFilter(self, obj, ev):
        et = ev.type()
        if et in (QEvent.NonClientAreaMouseButtonPress, QEvent.NonClientAreaMouseButtonDblClick):
            self._begin_interactive_resize()
        elif et == QEvent.NonClientAreaMouseButtonRelease:
            self._end_interactive_resize()
        return super().eventFilter(obj, ev)

    def resizeEvent(self, ev):
        self._begin_interactive_resize()
        self._resize_idle.start()
        super().resizeEvent(ev)

    def _begin_interactive_resize(self):
        if self._interactive_resizing:
            return
        self._interactive_resizing = True
        if self.game_tick.isActive():
            self.game_tick.stop()
        try:
            for g in self.findChildren(CircularProgress):
                g.setAntialiasing(False)
        except Exception:
            pass

    def _end_interactive_resize(self):
        if not self._interactive_resizing:
            return
        self._interactive_resizing = False
        try:
            for g in self.findChildren(CircularProgress):
                g.setAntialiasing(True)
        except Exception:
            pass
        if not self.game_tick.isActive():
            self.game_tick.start(250)
        self.refresh_labels()
        self.update_game_clock()

    # ---------- Pętla gry ----------
    def tick_from_game(self):
        try:
            d: dict[str, Any] = self.telemetry_service.poll_normalized() or {}
        except Exception as e:
            print(f"[tick] provider exception: {e}")
            d = {}

        # dane po normalizacji
        self.speed_kmh = float(d.get("speed_kmh") or 0.0)
        paused = bool(d.get("paused", False))
        self.engine_on = bool(d.get("engine_on", self.engine_on))
        self.parking_brake = bool(d.get("parking_brake", self.parking_brake))

        if hasattr(self.mainTab, "set_speed"):
            self.mainTab.set_speed(self.speed_kmh)

        dt = 0

        # preferowane: game_minutes -> sekundy
        gm = d.get("game_minutes")
        if gm is not None:
            try:
                gm = int(gm)
                if self._last_game_minutes is not None:
                    dt = max(0, (gm - self._last_game_minutes) * 60)
                self._last_game_minutes = gm
                self.game_minutes = gm
            except Exception:
                pass
        else:
            # alternatywa: game_time_unix
            gt = int(d.get("game_time_unix") or 0)
            if gt > 0:
                if self._last_game_time_unix > 0:
                    dt = max(0, gt - self._last_game_time_unix)
                self._last_game_time_unix = gt
                self.game_time_unix = gt

        # zapis ISO (do wyświetlania i fallbacku)
        if d.get("game_time_iso") is not None:
            self.game_time_iso = d.get("game_time_iso")

        # fallback: dt z ISO, gdy brak gm/gt lub dt==0
        if (dt == 0) and self.game_time_iso:
            try:
                cur = datetime.fromisoformat(self.game_time_iso.replace("Z", "+00:00"))
                if self._last_game_iso_dt is not None:
                    delta = (cur - self._last_game_iso_dt).total_seconds()
                    dt = max(0, int(delta))
                self._last_game_iso_dt = cur
            except Exception:
                pass

        # --- Auto-kończenie przerwy przy naruszeniu warunków ---
        if self.breaks.on_break and (self.engine_on or (not self.parking_brake) or self.speed_kmh > 0.1):
            res = self.breaks.end_break()
            reason = ("AUTO: pojazd ruszył" if self.speed_kmh > 0.1
                      else ("AUTO: silnik włączony" if self.engine_on
                            else "AUTO: hamulec zwolniony"))
            self._apply_break_result(res, end_reason=reason)
            self.statusBar().showMessage(self.tr.get("break_cancelled_guard", "Przerwa przerwana: silnik włączony lub hamulec ręczny zwolniony."), 3000)

        # --- Naliczenia i odliczanie ---
        if dt > 0 and not paused:
            if not self.breaks.on_break and self.speed_kmh > 0.1:
                self.driving_seconds += dt
                self.working_seconds += dt
                self.daily_drive_sec += dt
                self.week_drive_sec += dt
                self.fortnight_drive_sec += dt
                self.breaks.tick_drive(dt)
            else:
                if self.breaks.on_break:
                    self.break_seconds += dt
                    self.working_seconds += dt
                    self.breaks.tick_break(dt)
                else:
                    self.working_seconds += dt

            # licznik przerw + aktualizacja UI
            if self.breaks.on_break and self.active_break_remaining > 0:
                self.active_break_remaining = max(0, self.active_break_remaining - dt)

                try:
                    target_min = int(self.active_break_total // 60) if self.active_break_total > 0 else None
                    if target_min:
                        self.breaksTab.update_countdown(self.active_break_remaining, target_min)
                        self.breaksTab.set_running_status(target_min)
                except Exception:
                    pass

                if self.active_break_remaining == 0:
                    res = self.breaks.complete_break(self.active_break_total)
                    if res and res.get("kind") == "WEEKLY_45H":
                        res["reset_fortnight"] = True
                    self._apply_break_result(res, end_reason="AUTO: limit osiągnięty")

        if not self._interactive_resizing:
            self.update_game_clock()
            self.refresh_labels()

        # --- Feedback / ostrzeżenia (throttling) ---
        status_code = "OK"
        if self.breaks.since_break_seconds > DRIVE_BEFORE_BREAK_MAX:
            status_code = "OVER_BREAK"
        elif DRIVE_BEFORE_BREAK_MAX - self.breaks.since_break_seconds <= WARN_REMAIN_BREAK_MIN:
            status_code = "WARN_BREAK"
        elif self.daily_drive_sec >= DAILY_DRIVE_LIMIT_SEC:
            status_code = "OVER_DAILY"

        if status_code != self._last_status_code:
            if status_code == "OVER_BREAK":
                self.statusBar().showMessage(self.tr.get("over_break", "Przekroczono 4h30 bez przerwy!"), 5000)
            elif status_code == "WARN_BREAK":
                self.statusBar().showMessage(self.tr.get("warn_break", "Zbliżasz się do 4h30 — czas na przerwę."), 3000)
            elif status_code == "OVER_DAILY":
                self.statusBar().showMessage(self.tr.get("over_daily", "Przekroczono dzienny limit 9h!"), 5000)
            else:
                self.statusBar().clearMessage()
            self._last_status_code = status_code

    def update_game_clock(self):
        new_text = None
        if self.game_time_iso:
            try:
                dt = datetime.fromisoformat(self.game_time_iso.replace("Z", "+00:00"))
                name = _wday_name(self.lang, dt.weekday())
                new_text = f"{self.tr['game_clock']}: {name}, {dt.hour:02d}:{dt.minute:02d}"
            except Exception:
                new_text = None
        if new_text is None and self.game_minutes is not None:
            try:
                gm = int(self.game_minutes)
                day_idx = (gm // 1440) % 7
                hour = (gm % 1440) // 60
                minute = gm % 60
                name = _wday_name(self.lang, day_idx)
                new_text = f"{self.tr['game_clock']}: {name}, {hour:02d}:{minute:02d}"
            except Exception:
                new_text = None
        if new_text is None:
            new_text = f"{self.tr['game_clock']}: —"

        if self._last_clock_text != new_text:
            self.mainTab.set_clock_text(new_text)
            self._last_clock_text = new_text

    # ---------- Czas gry (formaty do historii) ----------
    def _current_game_display_time(self) -> str:
        # zwraca HH:MM z zegara gry
        if self.game_time_iso:
            try:
                dt = datetime.fromisoformat(self.game_time_iso.replace("Z", "+00:00"))
                return f"{dt.hour:02d}:{dt.minute:02d}"
            except Exception:
                pass
        if self.game_minutes is not None:
            try:
                gm = int(self.game_minutes)
                hour = (gm % 1440) // 60
                minute = gm % 60
                return f"{hour:02d}:{minute:02d}"
            except Exception:
                pass
        # fallback – czas lokalny (gdy brak danych gry)
        now = datetime.now()
        return f"{now.hour:02d}:{now.minute:02d}"

    def _current_game_iso(self) -> str:
        if self.game_time_iso:
            return self.game_time_iso
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # ---------- Przerwy ----------
    def stop_break(self):
        if not self.breaks.on_break and self.active_break_total == 0:
            return
        res = self.breaks.end_break()
        if res and res.get("seconds", 0) == 0 and self.active_break_total > 0:
            elapsed = self.active_break_total - max(0, self.active_break_remaining)
            res = self.breaks.complete_break(int(elapsed))
            if res and res.get("kind") == "WEEKLY_45H":
                res["reset_fortnight"] = True
        self._apply_break_result(res, end_reason="RĘCZNIE")
        self.statusBar().showMessage(self.tr.get("break_stopped", "Przerwa zakończona."), 2000)


    def start_fixed_break(self, seconds: int):
        if self.breaks.on_break:
            QMessageBox.information(self, "Przerwa", self.tr.get("break_already_running", "Przerwa już trwa. Zakończ, aby rozpocząć inną."))
            return

        self._refresh_telemetry_now()
        ok = self.breaks.start_break(engine_on=self.engine_on, parking_brake=self.parking_brake)
        if not ok:
            reason = self.breaks.get_status().get("break_blocked_reason", "") or \
                     "Nie można rozpocząć przerwy: wyłącz silnik i zaciągnij hamulec ręczny."
            QMessageBox.warning(self, "Przerwa zablokowana", reason)
            self.statusBar().showMessage(reason, 4000)
            return

        # zapamiętaj czas startu (do historii)
        self._break_start_display = self._current_game_display_time()
        self._break_start_iso = self._current_game_iso()

        self.active_break_total = int(seconds)
        self.active_break_remaining = int(seconds)

        # UI: blokada + podświetlenie odpowiedniego klawisza
        key = None
        if seconds == 15*60: key = "15"
        elif seconds == 30*60: key = "30"
        elif seconds == 45*60: key = "45"
        elif seconds == 9*3600: key = "9h"
        elif seconds == 24*3600: key = "24h"
        elif seconds == 45*3600: key = "45h"

        self.breaksTab.set_global_enabled(False)
        self.breaksTab.highlight_button(key)
        self.breaksTab.show_break_started(int(seconds // 60))
        self.breaksTab.reset_countdown()
        self.breaksTab.update_countdown(self.active_break_remaining, int(seconds // 60))
        self.breaksTab.set_running_status(int(seconds // 60))
        self.statusBar().showMessage(self.tr.get("break_started", "Rozpoczęto przerwę."), 2000)


    def _apply_break_result(self, res: dict, *, end_reason: str = "RĘCZNIE"):
        end_display = self._current_game_display_time()
        end_iso = self._current_game_iso()

        # odblokuj UI, wyczyść licznik i highlight
        self.active_break_total = 0
        self.active_break_remaining = 0
        self.breaksTab.set_global_enabled(True)
        self.breaksTab.highlight_button(None)
        self.breaksTab.reset_countdown()
        self.breaksTab.show_break_stopped()

        if not res:
            return

        # resety liczników wg wyniku
        if res.get("reset_daily"):
            self.daily_drive_sec = 0
            self.working_seconds = 0
            self.breaks.counters.since_last_qual_break_drive = 0
        if res.get("reset_weekly"):
            self.week_drive_sec = 0
        if res.get("reset_fortnight"):
            self.fortnight_drive_sec = 0

        # opis typu / efektów
        kind = res.get("kind","")
        if   kind == "SHORT_15": ttxt = self.tr["type_short15"]
        elif kind == "SHORT_30": ttxt = self.tr["type_short30"]
        elif kind == "SHORT_45": ttxt = self.tr["type_short45"]
        elif kind == "DAILY_9H": ttxt = self.tr["type_daily9"]
        elif kind == "WEEKLY_24H": ttxt = self.tr["type_weekly24"]
        elif kind == "WEEKLY_45H": ttxt = self.tr["type_weekly45"]
        else: ttxt = "—"

        dur_txt = fmt_hm(int(res.get("seconds",0)))
        effs=[]
        if res.get("reset_daily"): effs.append(self.tr["effect_reset_daily"])
        if res.get("reset_weekly"): effs.append(self.tr["effect_reset_weekly"])
        if res.get("reset_fortnight"): effs.append(self.tr["effect_reset_fortnight"])
        eff_txt = " + ".join(effs) if effs else self.tr["effect_none"]

        # Historia UI + zapis
        start_display = self._break_start_display or "—"
        self.breaksTab.append_history(start_display, end_display, ttxt, dur_txt, eff_txt, end_reason)

        record = {
            "start_display": start_display,
            "end_display": end_display,
            "start_iso": self._break_start_iso,
            "end_iso": end_iso,
            "type_text": ttxt,
            "seconds": int(res.get("seconds",0)),
            "duration_text": dur_txt,
            "effects_text": eff_txt,
            "end_reason": end_reason,
            "kind": kind,
        }
        self._history_append(record)

        self._break_start_display = None
        self._break_start_iso = None

        # === LOGIKA 15 → 30 / 45 ===
        # Jeżeli zakończono 15', blokujemy 15 i 45 – zostaje tylko 30'
        if kind == "SHORT_15":
            self.breaksTab.set_split_lock_after_15(True)
        else:
            # jeśli zaliczono 30' (druga część) lub pełne 45' lub długi odpoczynek – resetujemy lock
            if kind in ("SHORT_30", "SHORT_45", "DAILY_9H", "WEEKLY_24H", "WEEKLY_45H"):
                self.breaksTab.set_split_lock_after_15(False)

        self.refresh_labels(force=True)


    # ---------- UI odświeżanie ----------
    def refresh_labels(self, force=False):
        sb = self.breaks.since_break_seconds
        rem45 = max(0, DRIVE_BEFORE_BREAK_MAX - sb)
        since_text = fmt_hm(sb) + f"\n(−{fmt_hm(rem45)})"
        clr = ACCENT_RED if sb > DRIVE_BEFORE_BREAK_MAX else (ACCENT_WARN if rem45 <= WARN_REMAIN_BREAK_MIN else GOLD)
        self.mainTab.set_since_break(DRIVE_BEFORE_BREAK_MAX, sb, since_text, clr)

        rem_day = max(0, DAILY_DRIVE_LIMIT_SEC - self.daily_drive_sec)
        day_text = fmt_hm(self.daily_drive_sec) + f"\n(−{fmt_hm(rem_day)})"
        clr_d = ACCENT_RED if rem_day == 0 else (ACCENT_WARN if rem_day <= WARN_REMAIN_DAILY_MIN else GOLD)
        self.mainTab.set_daily(DAILY_DRIVE_LIMIT_SEC, self.daily_drive_sec, day_text, clr_d)

        rem_w = max(0, 56*3600 - self.week_drive_sec)
        self.mainTab.set_week(56*3600, self.week_drive_sec, fmt_hm(self.week_drive_sec) + f"\n(−{fmt_hm(rem_w)})")
        rem_f = max(0, 90*3600 - self.fortnight_drive_sec)
        self.mainTab.set_fortnight(90*3600, self.fortnight_drive_sec, fmt_hm(self.fortnight_drive_sec) + f"\n(−{fmt_hm(rem_f)})")

        drive_txt = f"{self.tr['drive_time']}: {fmt_hm(self.driving_seconds)} | {self.tr['since_break']}: {fmt_hm(sb)} (−{fmt_hm(rem45)})"
        work_txt  = f"{self.tr['work_time']}: {fmt_hm(self.working_seconds)}"
        self._last_drive_txt = drive_txt
        self._last_work_txt  = work_txt

        try:
            col = self.mainTab.lbl_state.palette().color(self.mainTab.lbl_state.foregroundRole()).name()
        except Exception:
            col = GOLD

        self.mainTab.set_info(drive_txt, work_txt, self.mainTab.lbl_state.text(), col)

    # ---------- Overlay ----------
    def handle_overlay(self):
        opened = self.overlay and self.overlay.isVisible()
        if opened:
            self.overlay.close(); self.overlay = None
            self.overlayTab.set_opened(False, self.tr); return

        opts = self.overlayTab.overlay_options()
        def text_provider():
            rem45 = max(0, DRIVE_BEFORE_BREAK_MAX - self.breaks.since_break_seconds)
            rem_day = max(0, DAILY_DRIVE_LIMIT_SEC - self.daily_drive_sec)
            return (f"RITT • 4h30: {fmt_hm(self.breaks.since_break_seconds)} (−{fmt_hm(rem45)})\n"
                    f"9h: {fmt_hm(self.daily_drive_sec)} (−{fmt_hm(rem_day)}) | v={int(self.speed_kmh)} km/h | "
                    f"{'PRZERWA' if self.breaks.on_break else 'JAZDA'}")
        self.overlay = MiniOverlay(text_provider)
        self.overlay.bg_enabled = bool(opts["bg"])
        self.overlay.setWindowFlag(Qt.WindowStaysOnTopHint, bool(opts["on_top"]))
        self.overlay.opacity = float(opts["opacity"])
        self.overlay.show()
        self.overlayTab.set_opened(True, self.tr)

    # ---------- I18N ----------
    def change_lang(self):
        code = self.lang_box.currentData()
        self.lang = code if code in LANGS else "pl"
        self.tr = get_tr(self.lang)
        self.setWindowTitle("RITT Tachograph — PRO")
        self.tabs.setTabText(0, self.tr["tab_main"])
        self.tabs.setTabText(1, self.tr["tab_breaks"])
        self.tabs.setTabText(2, self.tr["tab_overlay"])
        self.ping_btn.setText("🚦 " + self.tr["ping"])
        self.mainTab.apply_tr(self.tr); self.breaksTab.apply_tr(self.tr); self.overlayTab.apply_tr(self.tr)
        # odśwież aktualne stany przycisków
        self.breaksTab.set_global_enabled(not self.breaks.on_break)
        # split lock zostaje taki, jaki był (BreaksTab pamięta flagę)
        self.refresh_labels(force=True); self.update_game_clock()


    # ---------- Sieć ----------
    def test_connection(self):
        threading.Thread(target=self._ping_bg, daemon=True).start()

    def _ping_bg(self):
        _ = self.net.get_json("/ping", timeout=2)

    def send_status_bg(self):
        payload = {
            "driver_id": CFG["driver_id"],
            "driving_seconds": int(self.driving_seconds),
            "working_seconds": int(self.working_seconds),
            "break_seconds": int(self.break_seconds),
            "on_break": self.breaks.on_break,
            "speed_kmh": float(self.speed_kmh),
            "game_time_unix": int(self.game_time_unix),
        }
        threading.Thread(target=lambda: self.net.post_json("/telemetry", payload, timeout=1.2), daemon=True).start()

    def fetch_points_bg(self):
        def run():
            data = self.net.get_json(f"/points/{CFG['driver_id']}", timeout=1.2)
            if data: self.netSignals.pointsUpdated.emit(int(data.get("points", 0)))
        threading.Thread(target=run, daemon=True).start()

    def on_points_updated(self, pts: int):
        self.tabs.setTabText(2, self.tr["tab_overlay"])
