# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

def _make_shadow(blur=16, dx=0, dy=3, a=110):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setOffset(dx, dy)
    eff.setColor(QColor(0, 0, 0, int(a)))
    return eff

def install_3d_effects(root: QWidget):
    """
    Nadaje delikatny cień wszystkim widgetom o objectName == 'Card'.
    Wywołaj raz po zbudowaniu UI (np. w main_window po dodaniu zakładek).
    """
    if root is None:
        return
    cards = root.findChildren(QWidget, "Card")
    for w in cards:
        # uniknij podwójnych efektów
        if not isinstance(w.graphicsEffect(), QGraphicsDropShadowEffect):
            w.setGraphicsEffect(_make_shadow(blur=18, dx=0, dy=4, a=120))

def set_3d_effects_enabled(root: QWidget, enabled: bool):
    """
    (opcjonalne) Możesz tymczasowo wyłączyć cienie np. w trakcie intensywnego resize'u.
    """
    cards = root.findChildren(QWidget, "Card")
    for w in cards:
        eff = w.graphicsEffect()
        if isinstance(eff, QGraphicsDropShadowEffect):
            eff.setEnabled(bool(enabled))
