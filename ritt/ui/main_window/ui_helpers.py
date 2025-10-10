# -*- coding: utf-8 -*-
from datetime import datetime
from PySide6.QtGui import QColor

# ========================
# 📅 Nazwy dni tygodnia
# ========================
WDAY = {
    "pl": ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

# ========================
# ⏱ Formatowanie godzin/minut (hh:mm)
# ========================
def fmt_hm(sec: int) -> str:
    """Zamienia sekundy na format 00:00"""
    if sec < 0:
        sec = 0
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"

# ========================
# 📆 Nazwa dnia tygodnia (po polsku/angielsku)
# ========================
def _wday_name(lang: str, idx: int | None) -> str:
    """Zwraca nazwę dnia tygodnia"""
    if idx is None:
        return "—"
    arr = WDAY.get(lang, WDAY["en"])
    return arr[int(idx) % 7]

# ========================
# 🕒 Formatowanie czasu gry (czytelny zegar)
# ========================
def fmt_game_clock(game_time_iso: str | None, lang: str = "pl") -> str:
    """
    Formatuje czas gry do postaci np.:
    'Czwartek • 14:45' albo 'Thursday • 14:45'
    """
    if not game_time_iso:
        return "—"
    try:
        # Konwersja ISO (np. 2025-10-09T14:45:00Z → datetime)
        dt = datetime.fromisoformat(game_time_iso.replace("Z", "+00:00"))
        wday = WDAY.get(lang, WDAY["en"])[dt.weekday()]
        return f"{wday} • {dt.strftime('%H:%M')}"
    except Exception:
        return "—"

# ========================
# 🎨 Pomocnicze kolory (opcjonalnie)
# ========================
GOLD = QColor("#FFD700")
ACCENT_RED = QColor("#FF6B6B")
ACCENT_WARN = QColor("#FFB347")
