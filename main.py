import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

# Import de ta config
from config import COLORS


class NavButton(QPushButton):
    def __init__(self, text, icon_str, index, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.index = index
        self.full_text = text
        self.icon_str = icon_str
        self.update_style(False)

    def update_style(self, is_collapsed):
        display_text = f" {self.icon_str}" if is_collapsed else f"  {self.icon_str}   {self.full_text}"
        self.setText(display_text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #CBD5E1; 
                border: none;
                border-left: 4px solid transparent;
                text-align: left;
                padding-left: 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #334155; color: white; }}
            QPushButton:checked {{
                background-color: #2D3A4F;
                color: {COLORS['info']};
                border-left: 4px solid {COLORS['info']};
            }}
        """)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS-Snort")
        self.is_collapsed = False

        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.page_instances = {}

        self.setup_sidebar()

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stack, 1)
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.switch_page(0)
        self.setLayout(self.main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(220)
        self.sidebar.setStyleSheet("background-color: #1E293B; border-right: 1px solid #334155;")

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo - Version simplifiée avec un seul label qui change de texte
        self.logo_label = QLabel("🛡️ Snort & ML IDS")
        self.logo_label.setFixedHeight(80)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet(
            f"color: {COLORS['info']}; font-weight: 900; font-size: 16px; "
            f"background: transparent; font-family: 'Segoe UI', monospace; "
            f"border-bottom: 1px solid #334155;"
        )
        layout.addWidget(self.logo_label)
        layout.addSpacing(10)

        # Boutons de navigation
        self.nav_buttons = []
        menus = [("Dashboard", "📊"), ("Alertes", "⚠️"), ("Analyse", "📈"),
                 ("Intelligence", "🤖"), ("Paramètres", "⚙️"), ("Rapports", "📄")]

        for i, (text, icon) in enumerate(menus):
            btn = NavButton(text, icon, i)
            btn.clicked.connect(lambda _, idx=i: self.switch_page(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Bouton Toggle
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                color: #8899AA;
                border: none;
                border-top: 1px solid #334155;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                color: white;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.toggle_btn)

    def switch_page(self, index):
        if index not in self.page_instances:
            self.create_page(index)

        self.stack.setCurrentWidget(self.page_instances[index])
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def create_page(self, index):
        try:
            if index == 0:
                from gui.dashboard import SimplePage
                widget = SimplePage()
            elif index == 1:
                from gui.alerte import AlertInterface
                widget = AlertInterface()
            elif index == 2:
                from gui.traficreseaux import TrafficAnalyzerInterface
                widget = TrafficAnalyzerInterface()
            elif index == 3:
                from gui.ML import IDSWindow
                widget = IDSWindow()
            elif index == 4:
                from gui.configuration import InterfaceParametresIDS
                widget = InterfaceParametresIDS()
            elif index == 5:
                from gui.Rapport import RapportInterface
                widget = RapportInterface()
            else:
                widget = QWidget()

            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            widget.setMinimumSize(0, 0)
            self.page_instances[index] = widget
            self.stack.addWidget(widget)
        except Exception as e:
            print(f"Erreur chargement page {index}: {e}")

    def toggle_sidebar(self):
        width = self.sidebar.width()
        new_width = 70 if width > 100 else 220
        self.is_collapsed = (new_width == 70)

        # Animation de la sidebar
        self.sidebar.setMaximumWidth(16777215)
        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(250)
        self.anim.setStartValue(width)
        self.anim.setEndValue(new_width)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()
        self.sidebar.setMaximumWidth(new_width)

        # Changer le texte du logo
        if self.is_collapsed:
            self.logo_label.setText("🛡️")
            self.logo_label.setStyleSheet(
                f"color: {COLORS['info']}; font-weight: 900; font-size: 28px; "
                f"background: transparent; border-bottom: 1px solid #334155;"
            )
            self.toggle_btn.setText("▶")
            self.toggle_btn.setToolTip("Développer le menu")
        else:
            self.logo_label.setText("🛡️ Snort & ML IDS")
            self.logo_label.setStyleSheet(
                f"color: {COLORS['info']}; font-weight: 900; font-size: 16px; "
                f"background: transparent; font-family: 'Segoe UI', monospace; "
                f"border-bottom: 1px solid #334155;"
            )
            self.toggle_btn.setText("◀")
            self.toggle_btn.setToolTip("Réduire le menu")

        # Mise à jour des boutons de navigation
        for btn in self.nav_buttons:
            btn.update_style(self.is_collapsed)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())