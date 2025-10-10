# -*- coding: utf-8 -*-
import os, json
from PySide6.QtCore import QStandardPaths

class HistoryMixin:
    def _history_path(self) -> str:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.getcwd()
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "break_history.json")

    def _history_load(self):
        """Wczytuje historię przerw z pliku, jeśli istnieje."""
        if hasattr(self, "breaksTab"):
            self.breaksTab.clear_history()  # ✅ tylko jeśli zakładka już istnieje

        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, "r", encoding="utf-8") as f:
                    self._history = json.load(f) or []
            else:
                self._history = []
        except Exception as e:
            print(f"[history_load] {e}")
            self._history = []

        # Jeśli zakładka istnieje — uzupełnij historię
        if hasattr(self, "breaksTab"):
            for rec in reversed(self._history):
                self.breaksTab.append_history(
                    rec.get("start_display", "—"),
                    rec.get("end_display", "—"),
                    rec.get("type_text", "—"),
                    rec.get("duration_text", "—"),
                    rec.get("effects_text", "—"),
                    rec.get("end_reason", "—"),
                )

    def _history_save(self):
        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[history_save] {e}")

    def _history_append(self, record):
        self._history.insert(0, record)
        self._history_save()

    def _history_clear(self):
        self._history = []
        self._history_save()
        if hasattr(self, "breaksTab"):
            self.breaksTab.clear_history()
        self.statusBar().showMessage("Historia przerw wyczyszczona.", 2000)
