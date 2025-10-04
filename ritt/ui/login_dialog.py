# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QWidget, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

try:
    from ritt.ui.gold_text import GoldLabel as TitleLabel
except Exception:
    TitleLabel = QLabel


class LoginDialog(QDialog):
    def __init__(self, parent=None, net_client=None):
        super().__init__(parent)
        self.setWindowTitle("Logowanie — RITT Tachograph")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.net_client = net_client
        self._display_name = None
        self._driver_id = None
        self.setWindowTitle("Logowanie — R‑I‑T‑T Tachograph")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Tytuł
        title = TitleLabel("RITT • Logowanie")
        tf = QFont(title.font()); tf.setPointSize(tf.pointSize() + 6); tf.setBold(True)
        title.setFont(tf)
        root.addWidget(title, 0, Qt.AlignLeft)

        # login
        row1 = QWidget(); l1 = QHBoxLayout(row1); l1.setContentsMargins(0,0,0,0); l1.setSpacing(8)
        l1.addWidget(QLabel("Login:"), 0)
        self.ed_login = QLineEdit(); self.ed_login.setPlaceholderText("np. jkowalski")
        l1.addWidget(self.ed_login, 1)
        root.addWidget(row1)

        # hasło
        row2 = QWidget(); l2 = QHBoxLayout(row2); l2.setContentsMargins(0,0,0,0); l2.setSpacing(8)
        l2.addWidget(QLabel("Hasło:"), 0)
        self.ed_pass = QLineEdit(); self.ed_pass.setEchoMode(QLineEdit.Password)
        l2.addWidget(self.ed_pass, 1)
        root.addWidget(row2)

        # checkboksy
        self.cb_remember_user = QCheckBox("Zapamiętaj login")
        self.cb_remember_pass = QCheckBox("Zapamiętaj hasło")
        root.addWidget(self.cb_remember_user, 0, Qt.AlignLeft)
        root.addWidget(self.cb_remember_pass, 0, Qt.AlignLeft)

        # komunikat o błędzie
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:#ff6b6b;")
        self.lbl_err.setVisible(False)
        root.addWidget(self.lbl_err)

        # przyciski
        btns = QWidget(); lb = QHBoxLayout(btns); lb.setContentsMargins(0,0,0,0); lb.setSpacing(8)
        lb.addItem(QSpacerItem(0,0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.btn_cancel = QPushButton("Anuluj"); self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Zaloguj"); self.btn_ok.clicked.connect(self._do_login)
        lb.addWidget(self.btn_cancel); lb.addWidget(self.btn_ok)
        root.addWidget(btns)

        self._load_saved()

    # ---- właściwości ----
    @property
    def username(self) -> str:
        return self.ed_login.text().strip()

    @property
    def password(self) -> str:
        return self.ed_pass.text()

    @property
    def display_name(self) -> str | None:
        return self._display_name

    @property
    def driver_id(self) -> str | None:
        return self._driver_id

    # ---- helpers ----
    def _load_saved(self):
        s = QSettings("RITT", "Auth")
        u = s.value("username")
        p = s.value("password")
        if u:
            self.ed_login.setText(str(u))
            self.cb_remember_user.setChecked(True)
        if p:
            self.ed_pass.setText(str(p))
            self.cb_remember_pass.setChecked(True)

    def _save_if_needed(self):
        s = QSettings("RITT", "Auth")
        if self.cb_remember_user.isChecked() and self.username:
            s.setValue("username", self.username)
        else:
            s.remove("username")

        if self.cb_remember_pass.isChecked() and self.password:
            s.setValue("password", self.password)
        else:
            s.remove("password")
        s.sync()

    def _show_error(self, msg: str):
        self.lbl_err.setText(str(msg)); self.lbl_err.setVisible(True)

    # ---- logowanie ----
    def _do_login(self):
        if not self.username or not self.password:
            self._show_error("Podaj login i hasło.")
            return

        # tutaj można dodać request do API
        self._save_if_needed()
        self.accept()
