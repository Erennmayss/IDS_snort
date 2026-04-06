# gui/components.py
from PyQt6.QtWidgets import QLabel, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QWidget, QVBoxLayout, QProgressBar
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer
from PyQt6.QtGui import QColor, QMovie
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COLORS

# ================== LABEL ANIMÉ ==================
class AnimatedLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._scale = 0.35
        self.update_style()

    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = value
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['info']};
                font-size: {int(32 * self._scale)}px;
                font-weight: bold;
                font-style: italic;
                font-family: 'Segoe UI';
                padding: 15px;
                background-color: none;
                border-radius: 15px;
            }}
        """)

    scale = pyqtProperty(float, getScale, setScale)

# ================== FRAME AVEC EFFET DE FOCUS ==================
class FocusableFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor(COLORS['info']))
        self.shadow_effect.setOffset(0, 0)
        self.shadow_effect.setEnabled(False)
        self.setGraphicsEffect(self.shadow_effect)

        self.focus_anim = QPropertyAnimation(self.shadow_effect, b"blurRadius")
        self.focus_anim.setDuration(150)
        self.focus_anim.setStartValue(20)
        self.focus_anim.setEndValue(30)
        self.focus_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.focus_timer = QTimer()
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self.remove_focus)

        self.click_anim = QPropertyAnimation(self, b"geometry")
        self.click_anim.setDuration(200)
        self.click_anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def mousePressEvent(self, event):
        rect = self.geometry()
        smaller = rect.adjusted(3, 3, -3, -3)
        normal = rect
        self.click_anim.setStartValue(smaller)
        self.click_anim.setKeyValueAt(0.3, normal)
        self.click_anim.setEndValue(normal)
        self.click_anim.start()
        self.apply_focus()
        event.accept()

    def apply_focus(self):
        self.shadow_effect.setEnabled(True)
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self.focus_anim.start()
        current_style = self.styleSheet()
        self.setStyleSheet(current_style + f"""
            QFrame {{
                border: 2px solid {COLORS['info']};
            }}
        """)
        self.focus_timer.start(1000)

    def remove_focus(self):
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.focus_anim.start()
        QTimer.singleShot(150, self.restore_style)

    def restore_style(self):
        current_style = self.styleSheet()
        base_style = current_style.replace(f"border: 2px solid {COLORS['info']};", "")
        self.setStyleSheet(base_style)
        self.shadow_effect.setEnabled(False)

# ================== WIDGET DE CHARGEMENT ==================
class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(15, 23, 42, 200);
                border-radius: 20px;
                padding: 30px;
            }}
        """)
        container_layout = QVBoxLayout(container)

        self.loading_label = QLabel()
        self.movie = QMovie("loading.gif")
        if self.movie.isValid():
            self.loading_label.setMovie(self.movie)
        else:
            self.loading_label.setText("Chargement en cours...")
            self.loading_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['info']};
                    font-size: 24px;
                    font-weight: bold;
                    padding: 30px;
                }}
            """)

        container_layout.addWidget(self.loading_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {COLORS['info']};
                border-radius: 10px;
                text-align: center;
                color: white;
                background-color: {COLORS['bg_medium']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['info']};
                border-radius: 8px;
            }}
        """)
        container_layout.addWidget(self.progress_bar)
        layout.addWidget(container)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)

    def showEvent(self, event):
        if self.movie.isValid(): self.movie.start()
        super().showEvent(event)

    def hideEvent(self, event):
        if self.movie.isValid(): self.movie.stop()
        super().hideEvent(event)

    def show_with_fade(self):
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        self.show()

    def hide_with_fade(self):
        self.fade_anim.setStartValue(1)
        self.fade_anim.setEndValue(0)
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)