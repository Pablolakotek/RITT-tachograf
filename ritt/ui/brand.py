# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ritt.ui.gold_text import GoldLabel


class BrandHeader(QWidget):
    """
    Pasek nagłówka:
      [ LEWO: 'RITT Tachograph' ]                            [ PRAWO: '👤 login' ]
    """
    def __init__(self, title: str = "RITT Tachograph", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(8)

        # LEWO: tytuł
        self.lbl_title = GoldLabel(title)
        f = QFont(self.lbl_title.font()); f.setPointSize(max(18, f.pointSize() + 6)); f.setBold(True)
        self.lbl_title.setFont(f)
        self.lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # PRAWO: użytkownik
        self.lbl_user = GoldLabel("")
        fu = QFont(self.lbl_user.font()); fu.setPointSize(max(12, fu.pointSize() + 2)); fu.setBold(True)
        self.lbl_user.setFont(fu)
        self.lbl_user.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_user.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.lbl_user.setVisible(False)

        lay.addWidget(self.lbl_title, 1)
        lay.addWidget(self.lbl_user, 0)

    def set_title(self, text: str):
        self.lbl_title.setText(text)

    def set_user_display(self, login: str | None = None, name: str | None = None, driver_id: str | None = None):
        """
        Priorytet WYŚWIETLANIA: login > name > ID.
        """
        shown = None
        if login and str(login).strip():
            shown = str(login).strip()
        elif name and str(name).strip():
            shown = str(name).strip()
        elif driver_id and str(driver_id).strip():
            shown = f"ID: {driver_id}"

        if shown:
            self.lbl_user.setText(f"👤 {shown}")
            self.lbl_user.setVisible(True)
        else:
            self.lbl_user.clear()
            self.lbl_user.setVisible(False)
