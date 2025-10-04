# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QFrame, QWidget, QGraphicsItem
from PySide6.QtGui import QTransform, QPainter
from PySide6.QtCore import Qt, QTimer

class ScalableContainer(QGraphicsView):
    """
    Lekkie, przepłynne skalowanie całego contentu:
    - throttling podczas resize (jedno przeliczenie co ~40 ms),
    - lżejsze render-hinty w trakcie przeciągania,
    - cache dla proxy (DeviceCoordinateCache).
    """
    def __init__(self, content: QWidget, design_size=(1200, 780),
                 allow_upscale=True, margin=6, throttle_ms=40, parent=None):
        super().__init__(parent)
        self._content = content
        self._dw, self._dh = int(design_size[0]), int(design_size[1])
        self._allow_up = bool(allow_upscale)
        self._margin = int(margin)

        # Bazowy wymiar "projektowy" – wszystko skaluje się do niego
        self._content.setFixedSize(self._dw, self._dh)

        scene = QGraphicsScene(self)
        self._proxy = scene.addWidget(self._content)
        # cache dla przerysowań
        self._proxy.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setScene(scene)

        self.setAlignment(Qt.AlignCenter)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Optymalizacje widoku
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)
        self.setCacheMode(QGraphicsView.CacheBackground)

        # Timer do throttlingu przy resize
        self._throttle = max(10, int(throttle_ms))
        self._resizeTimer = QTimer(self)
        self._resizeTimer.setSingleShot(True)
        self._resizeTimer.timeout.connect(self._apply_scale_heavy)

        # Start: pełne, „ładne” hinty
        self._set_render_light(False)
        self._apply_scale_heavy()

        # Transparentne tło, żeby było widać motyw
        self.setStyleSheet("QGraphicsView { background: transparent; }")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # W trakcie przeciągania – lekkie hinty + odkładamy cięższe przeliczenie
        self._set_render_light(True)
        self._resizeTimer.start(self._throttle)

    # --- tryby renderu ---
    def _set_render_light(self, light: bool):
        if light:
            # Tylko antyaliasing dla tekstu (najszybciej)
            self.setRenderHints(QPainter.TextAntialiasing)
        else:
            # Pełne „ładne” rysowanie
            self.setRenderHints(QPainter.Antialiasing |
                                QPainter.SmoothPixmapTransform |
                                QPainter.TextAntialiasing)

    # --- skalowanie ---
    def _apply_scale_heavy(self):
        self._apply_scale()
        # po krótkiej pauzie od resize wracamy do „ładnych” hintów
        self._set_render_light(False)

    def _apply_scale(self):
        vw = max(1, self.viewport().width() - 2 * self._margin)
        vh = max(1, self.viewport().height() - 2 * self._margin)
        sx = vw / float(self._dw)
        sy = vh / float(self._dh)
        s = min(sx, sy)
        if not self._allow_up:
            s = min(1.0, s)

        tr = QTransform()
        tr.scale(s, s)
        self.setTransform(tr)
        self.setSceneRect(0, 0, self._dw, self._dh)
