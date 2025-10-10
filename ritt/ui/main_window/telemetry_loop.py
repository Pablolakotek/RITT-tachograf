# -*- coding: utf-8 -*-
from datetime import datetime
from ritt.breaks import DRIVE_BEFORE_BREAK_MAX, WARN_REMAIN_BREAK_MIN
from ritt.ui.theme import GOLD, ACCENT_WARN, ACCENT_RED
from .ui_helpers import fmt_hm
from ritt.integrations.events import send_event_to_n8n
DAILY_DRIVE_LIMIT_SEC = 9 * 3600
WARN_REMAIN_DAILY_MIN = 15 * 60
from ritt.ui.main_window.ui_helpers import fmt_game_clock
class TelemetryMixin:


    def tick_from_game(self):
        """Odczytuje dane z gry i aktualizuje interfejs."""
        try:
            d = self.telemetry_service.poll_normalized() or {}
        except Exception as e:
            print(f"[tick] provider exception: {e}")
            d = {}

        # --- dane podstawowe ---
        paused = bool(d.get("paused", False))
        self.engine_on = bool(d.get("engine_on", self.engine_on))
        self.parking_brake = bool(d.get("parking_brake", self.parking_brake))
        self.speed_kmh = float(d.get("speed_kmh", 0.0))

        # 🔹 pobierz czas gry z możliwych źródeł (różne wersje Funbit)
        game_time_val = (
                d.get("game_time_unix")
                or (d.get("game", {}).get("time", {}).get("value") if isinstance(d.get("game"), dict) else None)
                or d.get("game_time_iso")
                or self.game_time_iso
        )
        self.game_time_iso = game_time_val

        # --- aktualizacja GUI ---
        if hasattr(self.mainTab, "set_speed"):
            self.mainTab.set_speed(self.speed_kmh)

        if hasattr(self.mainTab, "set_clock_text"):
            readable = fmt_game_clock(game_time_val, self.lang)
            clock_txt = f"{self.tr['game_clock']}: {readable}"
            self.mainTab.set_clock_text(clock_txt)

        # --- liczniki czasu jazdy / pracy ---
        if not paused and self.engine_on:
            if self.speed_kmh > 1.0:
                self.driving_seconds += 1
                self.working_seconds += 1
            else:
                self.working_seconds += 1

        # --- diagnostyka (jeśli chcesz zobaczyć dane) ---
        # print(f"[TACHO] speed={self.speed_kmh:.1f} km/h, engine={self.engine_on}, time={readable}")

        # --- odśwież etykiety w GUI ---
        self.refresh_labels(force=False)

    def refresh_labels(self, force=False):
        sb = self.breaks.since_break_seconds
        rem45 = max(0, DRIVE_BEFORE_BREAK_MAX - sb)
        since_text = fmt_hm(sb) + f"\n(−{fmt_hm(rem45)})"
        clr = ACCENT_RED if sb > DRIVE_BEFORE_BREAK_MAX else (ACCENT_WARN if rem45 <= WARN_REMAIN_BREAK_MIN else GOLD)
        self.mainTab.set_since_break(DRIVE_BEFORE_BREAK_MAX, sb, since_text, clr)
