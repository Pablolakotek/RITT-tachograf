from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer

class MiniOverlay(QWidget):
    def __init__(self, text_provider):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.text_provider = text_provider
        self.bg_enabled=True; self.opacity=0.9
        self.lbl=QLabel(""); self.lbl.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.lbl.setStyleSheet("font-size:16px; color:#fff; padding:8px;")
        lay=QVBoxLayout(self); lay.addWidget(self.lbl)
        self.resize(350,120); self._drag=None
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.refresh()

    def refresh(self):
        self.lbl.setText(self.text_provider())
        bg="rgba(0,0,0,180)" if self.bg_enabled else "rgba(0,0,0,0)"
        self.setStyleSheet(f"background:{bg}; border-radius:12px;")
        self.setWindowOpacity(self.opacity)

    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag=e.globalPosition().toPoint()
    def mouseMoveEvent(self,e):
        if self._drag:
            d=e.globalPosition().toPoint()-self._drag
            self.move(self.pos()+d); self._drag=e.globalPosition().toPoint()
    def mouseReleaseEvent(self,e): self._drag=None
