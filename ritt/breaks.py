# ritt/breaks.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from collections import deque
from typing import Deque, Tuple, Optional, Dict

"""
RITT Tachograph – EU breaks/limits logic
• 4h30 jazdy → przerwa 45 min (może być split 15 + 30, w tej kolejności).
• Odpoczynek dzienny ≥ 9 h → reset dzienny.
• Odpoczynek tygodniowy ≥24 h (zredukowany) lub ≥45 h (regularny) → reset tygodniowy.

Kompatybilność ze starym UI:
  .on_break (bool)
  start_break(engine_on=None, parking_brake=None) -> bool
  end_break() -> dict
  tick_drive(seconds: int)
  tick_break(seconds: int)
  complete_break(total_seconds: int) -> dict
  since_break_seconds (property) -> int

Twarde warunki przerwy:
  – można rozpocząć/utrzymać tylko, gdy hamulec ręczny = ON i silnik = OFF.
"""

# --- Stałe i aliasy (jednostki!) ---

# 4h30 w MINUTACH (logika)
DRIVE_BEFORE_BREAK_MAX_MINUTES = 4 * 60 + 30
# alias (minuty) dla zgodności
DRIVE_BEFORE_BREAK_MAX_MIN = DRIVE_BEFORE_BREAK_MAX_MINUTES
# 4h30 w SEKUNDACH (UI używa sekund)
DRIVE_BEFORE_BREAK_MAX = DRIVE_BEFORE_BREAK_MAX_MINUTES * 60

# Progi przerw (minuty)
BREAK_SPLIT_FIRST_MIN = 15
BREAK_SPLIT_SECOND_MIN = 30
BREAK_TOTAL_TARGET_MIN = 45

# Odpoczynki (minuty)
DAILY_REST_MIN = 9 * 60
WEEKLY_REST_REDUCED_MIN = 24 * 60
WEEKLY_REST_REGULAR_MIN = 45 * 60

# Ostrzeżenie 15 minut przed limitem 4h30:
WARN_REMAIN_BREAK_MINUTES = 15
# alias w SEKUNDACH dla UI:
WARN_REMAIN_BREAK_MIN = WARN_REMAIN_BREAK_MINUTES * 60

# Soft-limity (informacyjne)
DAILY_DRIVE_MAX_H = 9
WEEK_DRIVE_MAX_H = 56
FORTNIGHT_DRIVE_MAX_H = 90

SEC = 1
MIN = 60 * SEC
H = 60 * MIN
FORTNIGHT_WINDOW_SEC = 14 * 24 * H


class ActivityState(Enum):
    DRIVING = auto()
    WORKING = auto()
    REST = auto()


@dataclass
class Counters:
    drive_today: int = 0
    work_today: int = 0
    drive_this_week: int = 0
    work_this_week: int = 0

    drive_14days: int = 0
    since_last_qual_break_drive: int = 0
    continuous_rest: int = 0


class BreakManager:
    """
    Logika przerw/odpoczynków (EU) + zgodność ze starym UI.
    """

    def __init__(self, speed_threshold_ms: float = 0.4):
        self.speed_threshold_ms = speed_threshold_ms
        self.counters = Counters()

        # 14-dniowe okno jazdy
        self._drive_window: Deque[Tuple[int, int]] = deque()

        # Ostatnie stany „sprzętowe”
        self._last_engine_on: bool = False
        self._last_parking_brake: bool = False

        # Stan ogólny
        self._state: ActivityState = ActivityState.REST
        self._prev_state: ActivityState = ActivityState.REST
        self._last_game_unix_sec: Optional[int] = None

        # Bieżący blok REST
        self._rest_block_active: bool = False
        self._rest_block_len_sec: int = 0

        # Split 15 + 30
        self._split_first_done: bool = False

        # Resety one-shot w bieżącym REST
        self._daily_reset_done_this_rest: bool = False
        self._weekly_reset_done_this_rest: bool = False

        # --- Warstwa kompatybilności dla UI ---
        self.on_break: bool = False
        self._current_break_sec: int = 0
        self._break_blocked_reason: str = ""

    # ================= NOWE API (opcjonalne) =================

    def tick(self, game_unix_sec: int, speed_ms: float, engine_on: bool,
             parking_brake: bool, break_flag: bool) -> None:
        """
        Tick 1 Hz – jeśli kiedyś podłączysz bezpośrednio telemetrię do breaks.py.
        """
        self._last_engine_on = engine_on
        self._last_parking_brake = parking_brake

        if self._last_game_unix_sec is not None and game_unix_sec < self._last_game_unix_sec:
            return
        self._last_game_unix_sec = game_unix_sec

        # REST tylko jeśli break_flag i spełnione twarde warunki:
        if break_flag and self._hard_break_ok(engine_on, parking_brake):
            new_state = ActivityState.REST
        elif speed_ms > self.speed_threshold_ms:
            new_state = ActivityState.DRIVING
        elif engine_on:
            new_state = ActivityState.WORKING
        else:
            new_state = ActivityState.REST

        self._state = new_state
        self._handle_state_transitions()

        if self._state == ActivityState.DRIVING:
            self._tick_driving(1, game_unix_sec)
        elif self._state == ActivityState.WORKING:
            self._tick_working(1)
        else:
            self._tick_rest(1)

        self._prune_14day_window(game_unix_sec)
        self._prev_state = self._state

    # ================= STARE API (UI) =================

    def start_break(self, engine_on: Optional[bool] = None, parking_brake: Optional[bool] = None) -> bool:
        """
        UI: próba rozpoczęcia przerwy. Wymaga: ręczny=ON i silnik=OFF.
        Jeśli brak parametrów, używa ostatnio znanych stanów z telemetrii.
        """
        if engine_on is None:
            engine_on = self._last_engine_on
        if parking_brake is None:
            parking_brake = self._last_parking_brake

        if not self._hard_break_ok(engine_on, parking_brake):
            self._break_blocked_reason = self._compose_block_reason(engine_on, parking_brake)
            self.on_break = False
            return False

        self.on_break = True
        self._rest_block_active = True
        self._rest_block_len_sec = 0
        self._current_break_sec = 0
        self._daily_reset_done_this_rest = False
        self._weekly_reset_done_this_rest = False
        self._break_blocked_reason = ""
        return True

    def end_break(self) -> Dict:
        """
        UI: zakończ przerwę. Zwraca dict z 'kind' i flagami resetów.
        """
        res = self._finalize_break_dict(self._current_break_sec)
        self.on_break = False
        self._rest_block_active = False
        self._rest_block_len_sec = 0
        self._current_break_sec = 0
        self.counters.continuous_rest = 0
        return res

    def tick_drive(self, seconds: int) -> None:
        seconds = max(0, int(seconds))
        if seconds <= 0:
            return
        self.counters.drive_today += seconds
        self.counters.work_today += seconds
        self.counters.drive_this_week += seconds
        self.counters.work_this_week += seconds
        self.counters.since_last_qual_break_drive += seconds
        ts = self._last_game_unix_sec or 0
        self._drive_window.append((ts, seconds))
        self._recalc_14days_sum()

    def tick_break(self, seconds: int) -> None:
        seconds = max(0, int(seconds))
        if seconds <= 0:
            return

        self.counters.continuous_rest += seconds
        if self._rest_block_active:
            self._rest_block_len_sec += seconds
            self._current_break_sec += seconds

        # pełne 45
        if self._rest_block_len_sec >= BREAK_TOTAL_TARGET_MIN * MIN:
            self._qualify_45_break()

        # split 15 + 30
        if not self._split_first_done and self._rest_block_len_sec >= BREAK_SPLIT_FIRST_MIN * MIN:
            self._split_first_done = True
        if self._split_first_done and self._rest_block_len_sec >= BREAK_SPLIT_SECOND_MIN * MIN:
            self._qualify_45_break()

        # resety
        if (not self._daily_reset_done_this_rest) and self.counters.continuous_rest >= DAILY_REST_MIN * MIN:
            self._reset_daily()
            self._daily_reset_done_this_rest = True
            self._split_first_done = False

        if not self._weekly_reset_done_this_rest and self.counters.continuous_rest >= WEEKLY_REST_REDUCED_MIN * MIN:
            self._reset_weekly()
            self._weekly_reset_done_this_rest = True

    def complete_break(self, total_seconds: int) -> Dict:
        total_seconds = max(0, int(total_seconds))
        self._rest_block_active = True
        self._rest_block_len_sec = total_seconds
        self._current_break_sec = total_seconds

        if total_seconds >= BREAK_TOTAL_TARGET_MIN * MIN:
            self._qualify_45_break()
        elif (not self._split_first_done) and total_seconds >= BREAK_SPLIT_FIRST_MIN * MIN:
            self._split_first_done = True
        elif self._split_first_done and total_seconds >= BREAK_SPLIT_SECOND_MIN * MIN:
            self._qualify_45_break()

        res = self._finalize_break_dict(total_seconds)
        self.on_break = False
        self._rest_block_active = False
        self._rest_block_len_sec = 0
        self._current_break_sec = 0
        self.counters.continuous_rest = 0
        return res

    @property
    def since_break_seconds(self) -> int:
        return self.counters.since_last_qual_break_drive

    def get_status(self) -> Dict[str, int | bool | str]:
        return {
            "drive_today_sec": self.counters.drive_today,
            "work_today_sec": self.counters.work_today,
            "drive_this_week_sec": self.counters.drive_this_week,
            "work_this_week_sec": self.counters.work_this_week,
            "drive_14days_sec": self.counters.drive_14days,
            "since_last_qual_break_drive_sec": self.counters.since_last_qual_break_drive,
            "continuous_rest_sec": self.counters.continuous_rest,
            "split_first_done": self._split_first_done,
            "needs_45_break": self.needs_45_break(),
            "close_to_4h30": self._close_to_4h30(),
            "state": self._state.name if isinstance(self._state, ActivityState) else "REST",
            "break_blocked_reason": self._break_blocked_reason,
        }

    # ================= Wspólna logika =================

    def needs_45_break(self) -> bool:
        return self.counters.since_last_qual_break_drive >= DRIVE_BEFORE_BREAK_MAX_MINUTES * MIN

    def _handle_state_transitions(self) -> None:
        if self._state == ActivityState.REST and self._prev_state != ActivityState.REST:
            self._rest_block_active = True
            self._rest_block_len_sec = 0
            self.counters.continuous_rest = 0
            self._daily_reset_done_this_rest = False
            self._weekly_reset_done_this_rest = False

        if self._state != ActivityState.REST and self._prev_state == ActivityState.REST:
            self._rest_block_active = False
            self._rest_block_len_sec = 0
            self.counters.continuous_rest = 0

    def _tick_driving(self, seconds: int, now_ts: int) -> None:
        self.counters.drive_today += seconds
        self.counters.work_today += seconds
        self.counters.drive_this_week += seconds
        self.counters.work_this_week += seconds
        self.counters.since_last_qual_break_drive += seconds
        self._drive_window.append((now_ts, seconds))
        self._recalc_14days_sum()

    def _tick_working(self, seconds: int) -> None:
        self.counters.work_today += seconds
        self.counters.work_this_week += seconds

    def _tick_rest(self, seconds: int) -> None:
        self.counters.continuous_rest += seconds
        if self._rest_block_active:
            self._rest_block_len_sec += seconds

        if self._rest_block_len_sec >= BREAK_TOTAL_TARGET_MIN * MIN:
            self._qualify_45_break()

        if not self._split_first_done and self._rest_block_len_sec >= BREAK_SPLIT_FIRST_MIN * MIN:
            self._split_first_done = True
        if self._split_first_done and self._rest_block_len_sec >= BREAK_SPLIT_SECOND_MIN * MIN:
            self._qualify_45_break()

        if (not self._daily_reset_done_this_rest) and self.counters.continuous_rest >= DAILY_REST_MIN * MIN:
            self._reset_daily()
            self._daily_reset_done_this_rest = True
            self._split_first_done = False

        if not self._weekly_reset_done_this_rest and self.counters.continuous_rest >= WEEKLY_REST_REDUCED_MIN * MIN:
            self._reset_weekly()
            self._weekly_reset_done_this_rest = True

    def _qualify_45_break(self) -> None:
        self.counters.since_last_qual_break_drive = 0
        self._split_first_done = False

    def _reset_daily(self) -> None:
        self.counters.drive_today = 0
        self.counters.work_today = 0

    def _reset_weekly(self) -> None:
        self.counters.drive_this_week = 0
        self.counters.work_this_week = 0

    def _prune_14day_window(self, now_unix: int) -> None:
        threshold = now_unix - FORTNIGHT_WINDOW_SEC
        while self._drive_window and self._drive_window[0][0] <= threshold:
            self._drive_window.popleft()
        self._recalc_14days_sum()

    def _recalc_14days_sum(self) -> None:
        self.counters.drive_14days = sum(sec for _, sec in self._drive_window)

    def _close_to_4h30(self) -> bool:
        spent = self.counters.since_last_qual_break_drive
        remain = DRIVE_BEFORE_BREAK_MAX_MINUTES * MIN - spent
        return 0 < remain <= WARN_REMAIN_BREAK_MINUTES * MIN

    # --- Twarde warunki przerwy ---

    def _hard_break_ok(self, engine_on: bool, parking_brake: bool) -> bool:
        return (not engine_on) and bool(parking_brake)

    def _compose_block_reason(self, engine_on: bool, parking_brake: bool) -> str:
        if engine_on and not parking_brake:
            return "Nie można rozpocząć przerwy: wyłącz silnik i zaciągnij hamulec ręczny."
        if engine_on:
            return "Nie można rozpocząć przerwy: wyłącz silnik."
        if not parking_brake:
            return "Nie można rozpocząć przerwy: zaciągnij hamulec ręczny."
        return ""

    def _finalize_break_dict(self, total_seconds: int) -> Dict:
        res = {"kind": "—", "seconds": int(total_seconds),
               "reset_daily": False, "reset_weekly": False, "reset_fortnight": False}

        if total_seconds >= WEEKLY_REST_REGULAR_MIN * MIN:
            res["kind"] = "WEEKLY_45H"; res["reset_weekly"] = True
        elif total_seconds >= WEEKLY_REST_REDUCED_MIN * MIN:
            res["kind"] = "WEEKLY_24H"; res["reset_weekly"] = True
        elif total_seconds >= DAILY_REST_MIN * MIN:
            res["kind"] = "DAILY_9H";   res["reset_daily"] = True
        elif total_seconds >= BREAK_TOTAL_TARGET_MIN * MIN:
            res["kind"] = "SHORT_45"
        elif total_seconds >= BREAK_SPLIT_SECOND_MIN * MIN and self._split_first_done:
            res["kind"] = "SHORT_45"; self._qualify_45_break()
        elif total_seconds >= BREAK_SPLIT_SECOND_MIN * MIN:
            res["kind"] = "SHORT_30"
        elif total_seconds >= BREAK_SPLIT_FIRST_MIN * MIN:
            res["kind"] = "SHORT_15"

        if res["kind"] == "SHORT_45":
            self._split_first_done = False

        return res

    # --- debug / testy ---

    def force_set_split15(self, value: bool) -> None:
        self._split_first_done = bool(value)

    def force_reset_daily(self) -> None:
        self._reset_daily()

    def force_reset_weekly(self) -> None:
        self._reset_weekly()

    def force_qualify_45(self) -> None:
        self._qualify_45_break()

    # --- akcesory dla UI ---
    @property
    def current_break_seconds(self) -> int:
        """Ile sekund trwa obecnie liczona przerwa (0, jeśli brak aktywnej)."""
        return int(self._current_break_sec)

    @property
    def is_on_break(self) -> bool:
        """Czy przerwa jest aktywna wg. logiki managera."""
        return bool(self.on_break)

    def get_block_reason(self) -> str:
        """Jeśli start_break() nie zadziałał – dlaczego."""
        return self._break_blocked_reason or ""
