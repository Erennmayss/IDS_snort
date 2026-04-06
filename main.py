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
        self.setWindowTitle("IDS SENTINEL")
        self.is_collapsed = False

        # Correction du décalage : On utilise showMaximized() à la fin au lieu de setGeometry
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Dictionnaire pour stocker les instances des pages (Chargement à la demande)
        self.page_instances = {}

        self.setup_sidebar()

        # Zone de contenu
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stack, 1)

        # Charger la première page (Dashboard)
        self.switch_page(0)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(220)
        self.sidebar.setStyleSheet("background-color: #1E293B; border-right: 1px solid #334155;")

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo = QLabel("🛡️ SENTINEL")
        logo.setFixedHeight(80)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            f"color: {COLORS['info']}; font-weight: 900; font-size: 18px; border-bottom: 1px solid #334155;")
        layout.addWidget(logo)
        layout.addSpacing(10)

        # Boutons
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
        self.toggle_btn = QPushButton("⇇")
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.setStyleSheet("color: #8899AA; border: none; border-top: 1px solid #334155;")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.toggle_btn)

    def switch_page(self, index):
        """Charge la page uniquement au moment où on clique dessus"""
        if index not in self.page_instances:
            self.create_page(index)

        self.stack.setCurrentWidget(self.page_instances[index])
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def create_page(self, index):
        """Instanciation dynamique pour éviter la lourdeur au démarrage"""
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
            elif index == 3:  # <--- AJOUT DU MACHINE LEARNING ICI
                from gui.ML import IDSWindow
                widget = IDSWindow()
            elif index == 4:
                from gui.configuration import InterfaceParametresIDS
                widget = InterfaceParametresIDS()
            else:
                widget = QWidget()  # Page vide par défaut

            self.page_instances[index] = widget
            self.stack.addWidget(widget)
        except Exception as e:
            print(f"Erreur chargement page {index}: {e}")

    def toggle_sidebar(self):
        width = self.sidebar.width()
        new_width = 70 if width > 100 else 220
        self.is_collapsed = (new_width == 70)

        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(250)
        self.anim.setStartValue(width)
        self.anim.setEndValue(new_width)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

        self.sidebar.setMaximumWidth(new_width)
        for btn in self.nav_buttons:
            btn.update_style(self.is_collapsed)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()  # Correction du décalage : on laisse Windows gérer la taille
    sys.exit(app.exec())