# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from ritt.overlay import MiniOverlay
from ritt.breaks import DRIVE_BEFORE_BREAK_MAX
from .ui_helpers import fmt_hm

DAILY_DRIVE_LIMIT_SEC = 9 * 3600

class OverlayMixin:
    def handle_overlay(self):
        opened = self.overlay and self.overlay.isVisible()
        if opened:
            self.overlay.close()
            self.overlay = None
            self.overlayTab.set_opened(False, self.tr)
            return

        opts = self.overlayTab.overlay_options()
        def text_provider():
            rem45 = max(0, DRIVE_BEFORE_BREAK_MAX - self.breaks.since_break_seconds)
            rem_day = max(0, DAILY_DRIVE_LIMIT_SEC - self.daily_drive_sec)
            return (f"RITT • 4h30: {fmt_hm(self.breaks.since_break_seconds)} (−{fmt_hm(rem45)})\n"
                    f"9h: {fmt_hm(self.daily_drive_sec)} (−{fmt_hm(rem_day)}) | v={int(self.speed_kmh)} km/h")
        self.overlay = MiniOverlay(text_provider)
        self.overlay.bg_enabled = bool(opts["bg"])
        self.overlay.setWindowFlag(Qt.WindowStaysOnTopHint, bool(opts["on_top"]))
        self.overlay.opacity = float(opts["opacity"])
        self.overlay.show()
        self.overlayTab.set_opened(True, self.tr)
