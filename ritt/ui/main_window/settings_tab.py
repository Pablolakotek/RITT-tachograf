# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton, QMessageBox

class SettingsTab(QWidget):
    def __init__(self, tr):
        super().__init__()
        self.tr = tr
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("⚙️ Ustawienia tachografu")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        layout.addWidget(title)

        form = QFormLayout()
        self.driver_id = QLineEdit()
        self.api_url = QLineEdit()
        self.daily_limit = QLineEdit()
        form.addRow("ID kierowcy:", self.driver_id)
        form.addRow("Adres API / n8n:", self.api_url)
        form.addRow("Dzienne ograniczenie (h):", self.daily_limit)
        layout.addLayout(form)

        self.save_btn = QPushButton("💾 Zapisz ustawienia")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)
        layout.addStretch(1)

    def save_settings(self):
        from PySide6.QtCore import QSettings
        s = QSettings("RITT", "Tachograph")
        s.setValue("driver_id", self.driver_id.text())
        s.setValue("api_url", self.api_url.text())
        s.setValue("daily_limit_h", self.daily_limit.text())
        s.sync()
        QMessageBox.information(self, "Zapisano", "Ustawienia tachografu zostały zapisane.")
