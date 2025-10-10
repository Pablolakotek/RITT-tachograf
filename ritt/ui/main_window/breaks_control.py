# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QMessageBox
from .ui_helpers import fmt_hm
from ritt.integrations.events import send_event_to_n8n  # ✅ wysyłanie eventów do n8n


class BreaksMixin:
    def start_fixed_break(self, seconds):
        """Rozpoczęcie przerwy o stałej długości (np. 15, 30, 45 min)."""
        send_event_to_n8n(self, "break_start", f"Rozpoczęto przerwę {seconds // 60} min")

        if self.breaks.on_break:
            QMessageBox.information(self, "Przerwa", "Przerwa już trwa.")
            return

        ok = self.breaks.start_break(engine_on=self.engine_on, parking_brake=self.parking_brake)
        if not ok:
            QMessageBox.warning(self, "Nie można rozpocząć", "Wyłącz silnik i zaciągnij hamulec ręczny.")
            return

        self.active_break_total = seconds
        self.active_break_remaining = seconds
        self.breaksTab.set_global_enabled(False)
        self.statusBar().showMessage("Rozpoczęto przerwę.", 2000)

    def stop_break(self):
        """Zakończenie przerwy (manualne lub po czasie)."""
        send_event_to_n8n(self, "break_end", "Zakończono przerwę")

        if not self.breaks.on_break:
            return

        res = self.breaks.end_break()
        self.breaksTab.set_global_enabled(True)
        self.statusBar().showMessage("Przerwa zakończona.", 2000)
