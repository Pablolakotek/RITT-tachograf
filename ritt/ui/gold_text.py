# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtGui import (
    QPainter, QPainterPath, QLinearGradient, QColor, QPen,
    QPixmap, QFont, QFontMetricsF, QImage
)
from PySide6.QtCore import Qt, QRectF, QSize

class GoldLabel(QLabel):
    """
    Metaliczny złoty napis z cache'owaną bitmapą:
    – gradient + obrys liczone TYLKO gdy zmieni się tekst/font/rozmiar
    – podczas repaintów rysujemy gotowy pixmap → bardzo szybkie
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._outline = QColor(20, 20, 20)
        self._shine_top = QColor("#fff8d5")
        self._gold_mid1 = QColor("#f1d17a")
        self._gold_mid2 = QColor("#d4af37")
        self._gold_deep = QColor("#8a6b12")
        self._padding = 2
        self._cache_pix = None
        self._cache_text = None
        self._cache_font_key = None
        self._cache_size = None
        self.setAttribute(Qt.WA_StaticContents, True)

    def sizeHint(self) -> QSize:
        fm = QFontMetricsF(self.font())
        br = fm.boundingRect(self.text() or " ")
        h = int(br.height()) + self._padding * 2 + 2
        w = int(fm.horizontalAdvance(self.text() or " ")) + self._padding * 2 + 2
        return QSize(max(40, w), max(20, h))

    def setText(self, text: str) -> None:
        if text == self._cache_text: return
        super().setText(text); self._invalidate_cache()

    def setFont(self, f: QFont) -> None:
        old = self.font(); super().setFont(f)
        if (old.family(), old.pointSizeF(), old.weight(), old.style()) != (f.family(), f.pointSizeF(), f.weight(), f.style()):
            self._invalidate_cache()

    def resizeEvent(self, ev):
        super().resizeEvent(ev); self._invalidate_cache()

    def paintEvent(self, _):
        if self._need_rebuild(): self._rebuild_cache()
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        if self._cache_pix:
            x = 0
            if self.alignment() & Qt.AlignHCenter:
                x = (self.width() - self._cache_pix.width()/self.devicePixelRatioF())/2.0
            elif self.alignment() & Qt.AlignRight:
                x = self.width() - self._cache_pix.width()/self.devicePixelRatioF()
            y = (self.height() - self._cache_pix.height()/self.devicePixelRatioF())/2.0
            p.drawPixmap(int(x), int(y), self._cache_pix)

    # --- cache utils ---
    def _need_rebuild(self) -> bool:
        if self._cache_pix is None: return True
        if self._cache_text != (self.text() or ""): return True
        key = (self.font().family(), float(self.font().pointSizeF()), self.font().weight(), self.font().style())
        if self._cache_font_key != key: return True
        size_key = (self.width(), self.height(), self.devicePixelRatioF())
        if self._cache_size != size_key: return True
        return False

    def _invalidate_cache(self):
        self._cache_pix = None; self.update()

    def _rebuild_cache(self):
        text = self.text() or ""
        dpr = max(1.0, self.devicePixelRatioF())
        fm = QFontMetricsF(self.font())
        tw = fm.horizontalAdvance(text); th = fm.height()
        if not text or self.width() <= 0 or self.height() <= 0:
            self._cache_pix = None
        else:
            pad = max(self._padding, int(th*0.15))
            img_w = int(tw + pad*2); img_h = int(th + pad*2)
            img = QImage(int(img_w*dpr), int(img_h*dpr), QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(dpr); img.fill(Qt.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing, True); p.setRenderHint(QPainter.TextAntialiasing, True)
            x = pad; y_baseline = pad + fm.ascent()
            path = QPainterPath(); path.addText(x, y_baseline, self.font(), text)
            pen = QPen(self._outline); pen.setWidthF(max(1.0, th*0.06))
            p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawPath(path)
            grad_rect = QRectF(x, y_baseline - th, tw, th)
            g = QLinearGradient(grad_rect.topLeft(), grad_rect.bottomLeft())
            g.setColorAt(0.00, self._shine_top)
            g.setColorAt(0.22, self._gold_mid1)
            g.setColorAt(0.50, self._gold_mid2)
            g.setColorAt(0.78, self._gold_mid1)
            g.setColorAt(1.00, self._gold_deep)
            p.setPen(Qt.NoPen); p.setBrush(g); p.drawPath(path); p.end()
            self._cache_pix = QPixmap.fromImage(img)
        self._cache_text = text
        self._cache_font_key = (self.font().family(), float(self.font().pointSizeF()), self.font().weight(), self.font().style())
        self._cache_size = (self.width(), self.height(), dpr)
