# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QConicalGradient
from PySide6.QtWidgets import QWidget

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def _qcolor(c) -> QColor:
    if isinstance(c, QColor): return c
    return QColor(c)

def _lighten(c: QColor, f: float) -> QColor:
    # f>0 rozjaśnia, f<0 przyciemnia; zakres ~[-0.6, +0.6]
    f = max(-0.95, min(0.95, f))
    r,g,b = c.redF(), c.greenF(), c.blueF()
    if f >= 0:
        r = r + (1.0 - r)*f
        g = g + (1.0 - g)*f
        b = b + (1.0 - b)*f
    else:
        f = abs(f)
        r *= (1.0 - f)
        g *= (1.0 - f)
        b *= (1.0 - f)
    out = QColor(c)
    out.setRgbF(_clamp01(r), _clamp01(g), _clamp01(b), c.alphaF())
    return out


class CircularProgress(QWidget):
    """
    Okrągły wskaźnik z 3D look:
      - tło: ciemny „donut” z delikatnym gradientem,
      - foreground: złoty łuk z pionowym gradientem + połysk,
      - środek: tekst (np. '00:00\\n(-00:15)').
    API:
      setMaximum(int), setValue(int), setText(str),
      setColors(fg=None, bg=None), setThickness(int),
      setAntialiasing(bool)
    """
    def __init__(self, max_value=1, value=0, thickness=16, fg="#D4AF37", bg="#232323", text="", parent=None):
        super().__init__(parent)
        self._max = int(max_value) if max_value else 1
        self._val = int(value)
        self._th = int(max(2, thickness))
        self._fg = _qcolor(fg)
        self._bg = _qcolor(bg)
        self._text = text
        self._aa = True

        # podpowiedź dla layoutu – i tak ustawiasz min/max z zewnątrz
        self.setMinimumSize(120, 120)

    # --------- API setters ---------
    def setMaximum(self, m: int):
        m = int(m) if m else 1
        if m <= 0: m = 1
        if m != self._max:
            self._max = m
            self.update()

    def setValue(self, v: int):
        v = int(v)
        if v != self._val:
            self._val = v
            self.update()

    def setText(self, t: str):
        if t != self._text:
            self._text = t
            self.update()

    def setColors(self, fg=None, bg=None):
        changed = False
        if fg is not None:
            c = _qcolor(fg)
            if c != self._fg: self._fg = c; changed = True
        if bg is not None:
            c2 = _qcolor(bg)
            if c2 != self._bg: self._bg = c2; changed = True
        if changed: self.update()

    def setThickness(self, px: int):
        px = int(max(2, px))
        if px != self._th:
            self._th = px
            self.update()

    def setAntialiasing(self, on: bool):
        on = bool(on)
        if on != self._aa:
            self._aa = on
            self.update()

    # --------- painting ---------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, self._aa)

        w = self.width(); h = self.height()
        size = min(w, h)
        # padding tak, by pędzel o szerokości _th mieścił się w rect
        pad = self._th / 2.0 + 2.0
        rect = QRectF(pad, pad, size - 2*pad, size - 2*pad)
        cx = rect.center().x(); cy = rect.center().y()

        # ===== Donut tła (3D) =====
        # delikatny pionowy gradient (góra jaśniejsza, dół ciemniejszy)
        g_bg = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        bg_mid = _lighten(self._bg, -0.15)
        g_bg.setColorAt(0.0, _lighten(self._bg, 0.12))
        g_bg.setColorAt(0.5, bg_mid)
        g_bg.setColorAt(1.0, _lighten(self._bg, -0.25))
        pen_bg = QPen()
        pen_bg.setColor(Qt.transparent)  # kolor bierze się z pędzla (gradient)
        pen_bg.setBrush(g_bg)
        pen_bg.setWidthF(self._th)
        pen_bg.setCapStyle(Qt.FlatCap)
        p.setPen(pen_bg)
        start_angle = 90 * 16          # 0° w Qt = 3 o'clock; 90° = top
        span_full = -360 * 16          # minus = zgodnie z ruchem wskazówek
        p.drawArc(rect, start_angle, span_full)

        # ===== Łuk wartości (złoty gradient + połysk) =====
        ratio = _clamp01(self._val / float(self._max))
        if ratio > 0.0:
            # pionowy gradient złota (jaśniej u góry)
            g_fg = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            fg_top = _lighten(self._fg, 0.28)
            fg_bot = _lighten(self._fg, -0.10)
            g_fg.setColorAt(0.0, fg_top)
            g_fg.setColorAt(0.5, self._fg)
            g_fg.setColorAt(1.0, fg_bot)

            pen_fg = QPen()
            pen_fg.setColor(Qt.transparent)
            pen_fg.setBrush(g_fg)
            pen_fg.setWidthF(self._th)
            pen_fg.setCapStyle(Qt.FlatCap)
            p.setPen(pen_fg)

            span_val = int(-360.0 * 16.0 * ratio)
            p.drawArc(rect, start_angle, span_val)

            # cienki „połysk” na górnej krawędzi łuku (jak bevel)
            pen_hi = QPen()
            pen_hi.setColor(QColor(255, 255, 255, 80))
            pen_hi.setWidthF(max(1.0, self._th * 0.35))
            pen_hi.setCapStyle(Qt.FlatCap)
            p.setPen(pen_hi)
            # połysk tylko na ~70% długości łuku, zaczynając nieco od góry
            span_gloss = int(span_val * 0.7)
            p.drawArc(rect.adjusted(1.0, 1.0, -1.0, -1.0), start_angle - int(8*16), span_gloss)

        # ===== Tekst w środku =====
        if self._text:
            p.setPen(QPen(_lighten(self._fg, 0.15)))
            f = QFont(self.font())
            # Rozmiar czcionki zależny od średnicy i szerokości łuku
            base = max(10, int((rect.width() - self._th*1.5) * 0.12))
            f.setPointSize(base)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self._text)
