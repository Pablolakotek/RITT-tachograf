# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal

class OverlayTab(QWidget):
    openOverlayClicked = Signal()

    def __init__(self, tr: dict):
        super().__init__()
        self.tr = tr
        root = QVBoxLayout(self); root.setContentsMargins(10,10,10,10)

        self.cb_on_top = QCheckBox(self.tr["overlay_on_top"]); self.cb_on_top.setChecked(True)
        self.cb_bg = QCheckBox(self.tr["overlay_bg"]); self.cb_bg.setChecked(True)
        self.lbl_op = QLabel(self.tr["overlay_opacity"])
        self.sl_op = QSlider(Qt.Horizontal); self.sl_op.setRange(40,100); self.sl_op.setValue(90)
        self.btn_open = QPushButton(self.tr["overlay_open"]); self.btn_open.setProperty("gold", True)

        root.addWidget(self.cb_on_top); root.addWidget(self.cb_bg); root.addWidget(self.lbl_op); root.addWidget(self.sl_op); root.addWidget(self.btn_open)
        self.btn_open.clicked.connect(self.openOverlayClicked.emit)

    # API
    def set_opened(self, opened: bool, tr: dict | None = None):
        if tr: self.tr = tr
        self.btn_open.setText(self.tr["overlay_close"] if opened else self.tr["overlay_open"])

    def overlay_options(self):
        return {
            "on_top": self.cb_on_top.isChecked(),
            "bg": self.cb_bg.isChecked(),
            "opacity": self.sl_op.value()/100.0
        }

    def apply_tr(self, tr: dict):
        self.tr = tr
        self.cb_on_top.setText(self.tr["overlay_on_top"])
        self.cb_bg.setText(self.tr["overlay_bg"])
        self.lbl_op.setText(self.tr["overlay_opacity"])
        # przycisk tekst ustawiany w set_opened(...)
