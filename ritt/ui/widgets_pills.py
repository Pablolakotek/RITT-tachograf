# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetricsF, QPen
from PySide6.QtCore import Qt, QRectF, QSize


class PillProgress(QWidget):
    """
    Lekki pasek postępu typu 'pill' (zaokrąglony), z tekstem w środku.
    API (zgodne z potrzebami MainTab):
      setMaximum(int), setValue(int), setText(str), setColors(fg: str | None),
      setPreferredHeight(int) – do responsywnego skalowania.
    """
    def __init__(self, max_value=100, value=0, text="", fg="#d4af37", parent=None):
        super().__init__(parent)
        self._max = max(1, int(max_value))
        self._val = max(0, int(value))
        self._text = text or ""
        self._fg = QColor(fg)
        self._bg = QColor(20, 20, 22)      # tło pigułki
        self._halo = QColor(212, 175, 55, 38)  # lekkie tło „złote”
        self._h = 28
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(self._h)

        # antyaliasing włączony, ale to proste prostokąty – bardzo tanie
        self._antialias = True

    # ------- API -------
    def setMaximum(self, m: int):
        m = max(1, int(m))
        if m != self._max:
            self._max = m
            self._val = min(self._val, self._max)
            self.update()

    def setValue(self, v: int):
        v = max(0, int(v))
        if v != self._val:
            self._val = min(v, self._max)
            self.update()

    def setText(self, t: str):
        if t != self._text:
            self._text = t or ""
            self.update()

    def setColors(self, fg: str | None = None):
        if fg:
            c = QColor(fg)
            if c != self._fg:
                self._fg = c
                self.update()

    def setPreferredHeight(self, h: int):
        h = max(20, int(h))
        if h != self._h:
            self._h = h
            self.setMinimumHeight(self._h)
            self.setMaximumHeight(self._h)
            self.update()

    def sizeHint(self) -> QSize:
        return QSize(200, self._h)

    # ------- rysowanie -------
    def paintEvent(self, _):
        w = self.width(); h = self.height()
        if w <= 4 or h <= 4:
            return
        p = QPainter(self)
        if self._antialias:
            p.setRenderHint(QPainter.Antialiasing, True)

        radius = h / 2.0
        rect = QRectF(1, 1, w - 2, h - 2)

        # tło kapsuły
        p.setPen(QPen(self._halo, 1))
        p.setBrush(self._bg)
        p.drawRoundedRect(rect, radius, radius)

        # wypełnienie wg wartości
        ratio = 0.0 if self._max <= 0 else (self._val / float(self._max))
        fill_w = max(0.0, min(rect.width(), rect.width() * ratio))
        fill = QRectF(rect.left(), rect.top(), fill_w, rect.height())

        # złote wypełnienie (solid – szybkie)
        p.setPen(Qt.NoPen)
        p.setBrush(self._fg)
        # żeby zachować zaokrąglenia na końcach, dzielimy wypełnienie na pełną kapsułę i prostokąt
        if fill_w > radius * 2:
            # pełne zaokrąglone + reszta prostokąt
            full_caps = QRectF(rect.left(), rect.top(), radius * 2, rect.height())
            p.drawRoundedRect(full_caps, radius, radius)
            rest = QRectF(rect.left() + radius, rect.top(), fill_w - radius, rect.height())
            p.drawRect(rest)
        else:
            # tylko zaokrąglony fragment
            small = QRectF(rect.left(), rect.top(), fill_w, rect.height())
            p.drawRoundedRect(small, radius, radius)

        # tekst
        if self._text:
            f = self.font()
            # dopasuj font do wysokości
            f.setPointSizeF(max(9.0, min(16.0, h * 0.42)))
            self.setFont(f)
            p.setPen(QColor(0, 0, 0) if self._fg.lightness() > 120 and ratio > 0.12 else QColor(220, 200, 120))
            p.drawText(rect, Qt.AlignCenter, self._text)
