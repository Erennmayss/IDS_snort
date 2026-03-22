import sys
import psycopg2
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QPushButton, QWidget, QVBoxLayout, QLabel,
    QFrame, QGridLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QRect, QPropertyAnimation, QSize,
    QEasingCurve, QParallelAnimationGroup,
    pyqtProperty, QTimer
)
from PyQt6.QtGui import QPalette, QColor, QPixmap, QIcon

# ================= IMPORTS MATPLOTLIB =================
import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ================= CONFIGURATION BASE DE DONNÉES =================
DB_CONFIG = {
    'dbname': 'ids_db',
    'user': 'marwa',
    'password': 'marwa',
    'host': '192.168.1.2',
    'port': '5432'
}


# ================= HISTOGRAMME AVEC TAILLE OPTIMISÉE =================
class TrafficHistogram(FigureCanvas):
    def __init__(self):
        # Taille parfaitement adaptée à la case graphique
        self.fig = Figure(figsize=(4.5, 2.8), dpi=100)  # Dimensions optimales
        self.ax = self.fig.add_subplot(111)

        super().__init__(self.fig)

        # Configuration des couleurs
        self.ax.set_facecolor("#1E2E4F")
        self.fig.patch.set_facecolor("#1E2E4F")

        # Ajustement précis des marges
        self.fig.subplots_adjust(left=0.1, right=0.98, top=0.85, bottom=0.25)

        self.setMinimumHeight(200)
        self.setMaximumHeight(220)

        # Initialisation
        self.update_histogram([0] * 24)

    def update_histogram(self, data):
        """Met à jour l'histogramme avec une lisibilité optimale"""
        self.ax.clear()
        self.ax.set_facecolor("#1E2E4F")

        # Préparation des données
        heures = list(range(24))

        # Couleurs vives et contrastées
        couleurs = ['#FF4444' if val == 1 else '#44FF44' for val in data]

        # Barres plus fines pour mieux s'adapter
        bars = self.ax.bar(heures, data, color=couleurs, width=0.6, edgecolor='white', linewidth=0.8)

        # Titre compact mais lisible
        self.ax.set_title("TRAFIC 24H", color="white", fontsize=11, fontweight='bold', pad=5)

        # Axes avec labels minimaux
        self.ax.set_xlabel("HEURE", color="white", fontsize=8, fontweight='bold', labelpad=3)
        self.ax.set_ylabel("ÉTAT", color="white", fontsize=8, fontweight='bold', labelpad=3)

        # Configuration des ticks pour éviter la surcharge
        heures_labels = [f"{h:02d}" for h in range(24)]
        indices_a_afficher = [0, 3, 6, 9, 12, 15, 18, 21, 23]
        heures_a_afficher = [heures_labels[i] for i in indices_a_afficher]

        self.ax.set_xticks(indices_a_afficher)
        self.ax.set_xticklabels(heures_a_afficher, color='white', fontsize=7, rotation=0)
        self.ax.tick_params(axis='y', colors='white', labelsize=7)

        # Axe Y simplifié
        self.ax.set_ylim(0, 1.2)
        self.ax.set_yticks([0, 1])
        self.ax.set_yticklabels(['0', '1'], fontsize=7, fontweight='bold')

        # Grille légère
        self.ax.grid(True, axis='y', alpha=0.15, linestyle='--', color='white', linewidth=0.5)

        # Supprimer les bordures inutiles
        for spine in self.ax.spines.values():
            spine.set_visible(False)

        self.draw()


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            print("Connexion à la base de données établie")
        except Exception as e:
            print(f"Erreur de connexion à la base de données: {e}")

    def get_attack_stats(self):
        """Récupère les statistiques d'attaques"""
        try:
            cursor = self.connection.cursor()

            # Nombre total d'attaques
            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total_attacks = cursor.fetchone()[0]

            # Attaques de la dernière heure
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute("""
                SELECT COUNT(*) FROM security_alerts 
                WHERE timestamp >= %s
            """, (one_hour_ago,))
            last_hour_attacks = cursor.fetchone()[0]

            # Distribution par sévérité
            cursor.execute("""
                SELECT severity, COUNT(*) 
                FROM security_alerts 
                GROUP BY severity
            """)
            severity_counts = dict(cursor.fetchall())

            cursor.close()
            return {
                'total_attacks': total_attacks,
                'last_hour_attacks': last_hour_attacks,
                'severity_counts': severity_counts
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            return {
                'total_attacks': 0,
                'last_hour_attacks': 0,
                'severity_counts': {'Élevée': 0, 'Moyenne': 0, 'Basse': 0}
            }

    def get_total_packets(self):
        """Simule ou récupère le nombre total de paquets analysés"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total = cursor.fetchone()[0]
            cursor.close()
            if total == 0:
                return 0
            return total * 100
        except:
            return 0

    def calculate_risk_level(self):
        """Calcule le niveau de risque global"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT COUNT(*) FROM security_alerts")
            total_alerts = cursor.fetchone()[0]

            if total_alerts == 0:
                cursor.close()
                return 0

            last_24h = datetime.now() - timedelta(hours=24)
            cursor.execute("""
                SELECT severity, COUNT(*) 
                FROM security_alerts 
                WHERE timestamp >= %s
                GROUP BY severity
            """, (last_24h,))

            severity_data = dict(cursor.fetchall())

            if not severity_data:
                cursor.close()
                return 0

            risk_score = 0
            total_alerts_recent = sum(severity_data.values())

            if total_alerts_recent > 0:
                risk_score = (
                                     severity_data.get('Élevée', 0) * 3 +
                                     severity_data.get('Moyenne', 0) * 2 +
                                     severity_data.get('Basse', 0) * 1
                             ) / (total_alerts_recent * 3) * 100

            cursor.close()
            return min(100, int(risk_score))
        except Exception as e:
            print(f"Erreur calcul risque: {e}")
            return 0

    def get_attacks_last_24h(self):
        """Retourne un tableau 0/1 pour les 24 dernières heures"""
        try:
            cursor = self.connection.cursor()

            last_24h = datetime.now() - timedelta(hours=24)

            cursor.execute("""
                SELECT EXTRACT(HOUR FROM timestamp)
                FROM security_alerts
                WHERE timestamp >= %s
            """, (last_24h,))

            rows = cursor.fetchall()

            hours = [0] * 24

            for r in rows:
                h = int(r[0])
                hours[h] = 1

            cursor.close()
            return hours

        except Exception as e:
            print("Erreur histogramme:", e)
            return [0] * 24


# ================= ANIMATED LABEL =================
class AnimatedLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self._scale = 0.25
        self.update_style()

    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = value
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                color: #9b59b6;
                font-size: {int(28 * self._scale)}px;
                font-weight: bold;
                font-style: italic;
                font-family: 'Segoe UI';
                padding: 20px;
                background-color: none;
                border-radius: 15px;
            }}
        """)

    scale = pyqtProperty(float, getScale, setScale)


# ================= FRAME AVEC EFFET DE FOCUS =================
class FocusableFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor("#9b59b6"))
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
        self.setStyleSheet(current_style + """
            QFrame {
                border: 2px solid rgba(155, 89, 182, 0.8);
            }
        """)

        self.focus_timer.start(1000)

    def remove_focus(self):
        self.focus_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.focus_anim.start()
        QTimer.singleShot(150, self.restore_style)

    def restore_style(self):
        current_style = self.styleSheet()
        base_style = current_style.replace("border: 2px solid rgba(155, 89, 182, 0.8);", "")
        self.setStyleSheet(base_style)
        self.shadow_effect.setEnabled(False)


# ================= MAIN WINDOW =================
class SimplePage(QWidget):
    def __init__(self):
        super().__init__()

        self.db_manager = DatabaseManager()

        self.setWindowTitle("Intrusion Detection System")

        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height())

        # Background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)

        # ================= LEFT MENU =================
        menu_width = int(size.width() * 0.18)
        menu_height = size.height() - 20

        self.left_menu = QFrame(self)
        self.left_menu.setGeometry(0, 0, menu_width, menu_height)
        self.left_menu.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border: none;
            }
        """)

        menu_layout = QVBoxLayout(self.left_menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        menu_layout.setSpacing(10)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            pixmap = QPixmap("ids1.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(scaled_pixmap)
        except:
            pass

        logo_label.setFixedSize(190, 120)
        logo_label.setStyleSheet("""
            QLabel {
                border-radius: 60px;
                background-color: #1E2E4F;
                border: 3px solid #31487A;
            }
        """)

        menu_layout.addWidget(logo_label)

        menu_title = QLabel("Snort and Ai based Ids")
        menu_title.setStyleSheet("""
            color: #9b59b6;
            font-size: 18px;
            font-weight: bold;
        """)
        menu_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(menu_title)

        # Liste des boutons avec images personnalisées
        buttons_info = [
            ("donnees.png", "Dashboard"),
            ("alerte.png", "Alertes"),
            ("analyse.png", "Analyse du Trafic"),
            ("ml.png", "Machine Learning"),
            ("parametre.png", "Paramètres"),
            ("rapport.png", "Rapports")
        ]

        for image_name, text in buttons_info:
            btn = self.create_menu_button_with_image(image_name, text)
            menu_layout.addWidget(btn, stretch=1)

        menu_layout.addStretch()

        # ================= MAIN FRAME =================
        cadre_width = int(size.width() * 0.8)
        cadre_height = size.height() - 87

        self.cadre = QFrame(self)
        self.cadre.setGeometry(size.width() - cadre_width - 5, 4, cadre_width, cadre_height)
        self.cadre.setStyleSheet("""
            QFrame {
                background-color: #335889;
                border-radius: 30px;
                padding: 20px;
            }
        """)

        main_layout = QVBoxLayout(self.cadre)

        # ================= TITLE =================
        self.title = AnimatedLabel("Tableau de bord")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.opacity_effect)

        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(2000)
        self.opacity_anim.setKeyValueAt(0, 0.5)
        self.opacity_anim.setKeyValueAt(0.5, 1)
        self.opacity_anim.setKeyValueAt(1, 0.5)
        self.opacity_anim.setLoopCount(-1)

        self.scale_anim = QPropertyAnimation(self.title, b"scale")
        self.scale_anim.setDuration(2000)
        self.scale_anim.setKeyValueAt(0, 0.95)
        self.scale_anim.setKeyValueAt(0.5, 1.0)
        self.scale_anim.setKeyValueAt(1, 0.95)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.scale_anim.setLoopCount(-1)

        self.group = QParallelAnimationGroup()
        self.group.addAnimation(self.opacity_anim)
        self.group.addAnimation(self.scale_anim)
        self.group.start()

        # ================= GRID AVEC 4 CADRES =================
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        self.update_data_from_db()

        # Cadres 1, 2, 3
        self.cadre1 = self.create_inner_frame(
            " Nombre total de paquets analysés",
            self.format_packets_display()
        )

        self.cadre2 = self.create_inner_frame(
            "Nombre d'attaques détectées",
            self.format_attacks_display()
        )

        self.cadre3 = self.create_inner_frame(
            " Niveau de risque global",
            self.format_risk_display()
        )

        # ================= CADRE 4 AVEC HISTOGRAMME OPTIMISÉ =================
        self.cadre4 = FocusableFrame()
        self.cadre4.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-radius: 20px;
                padding: 10px;
                border: 2px solid #335889;
            }
        """)

        layout4 = QVBoxLayout(self.cadre4)
        layout4.setSpacing(5)
        layout4.setContentsMargins(8, 8, 8, 8)

        # Titre compact
        title4 = QLabel(" TRAFIC EN TEMPS RÉEL")
        title4.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            background-color: #335889;
            padding: 5px;
            border-radius: 5px;
            margin-bottom: 3px;
        """)
        title4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout4.addWidget(title4)

        # Légende simple et claire
        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setSpacing(10)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend_layout.setContentsMargins(0, 0, 0, 0)

        sain_label = QLabel("● SAIN (0)")
        sain_label.setStyleSheet("""
            color: #44FF44;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 8px;
            background-color: #1E3A5F;
            border-radius: 8px;
        """)
        legend_layout.addWidget(sain_label)

        attaque_label = QLabel("● ATTAQUE (1)")
        attaque_label.setStyleSheet("""
            color: #FF4444;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 8px;
            background-color: #1E3A5F;
            border-radius: 8px;
        """)
        legend_layout.addWidget(attaque_label)

        layout4.addWidget(legend_widget)

        # Histogramme parfaitement dimensionné
        self.histogram = TrafficHistogram()
        layout4.addWidget(self.histogram)

        # Ajouter les cadres à la grille
        grid_layout.addWidget(self.cadre1, 0, 0)
        grid_layout.addWidget(self.cadre2, 0, 1)
        grid_layout.addWidget(self.cadre3, 1, 0)
        grid_layout.addWidget(self.cadre4, 1, 1)

        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        main_layout.addLayout(grid_layout)

        # Initialisation de l'histogramme
        hist_data = self.db_manager.get_attacks_last_24h()
        self.histogram.update_histogram(hist_data)

        # Timer pour rafraîchir le dashboard
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_dashboard)
        self.update_timer.start(5000)

    def create_menu_button_with_image(self, image_name, text):
        """Crée un bouton de menu avec une image personnalisée"""
        btn = QPushButton(f"{text}")  # Espaces pour l'alignement
        btn.setMinimumWidth(0)
        btn.setMaximumWidth(16777215)  # important
        btn.setStyleSheet("""
            QPushButton {
                 background-color: transparent;
                 border: none;
                 color: white;
                 padding: 12px 17px;
                 text-align: left;
                 border-radius: 6px;
                 text-align: left;
                 font-size : 14px;
            }
            QPushButton:hover {
                background-color: #3A5FA0;
            }
            QPushButton:pressed {
                background-color: #253456;
            }
        """)
        icon_size = 32  # Plus grand pour al.png et analyse.png


        # Charger l'image
        try:
            pixmap = QPixmap(image_name)
            if not pixmap.isNull():
                # Redimensionner l'image
                scaled_pixmap = pixmap.scaled(
                    icon_size, icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                # Créer une icône à partir du pixmap
                icon = QIcon()
                icon.addPixmap(scaled_pixmap)
                btn.setIcon(icon)
                btn.setIconSize(QSize(icon_size, icon_size))
                print(f"✅ Image chargée: {image_name} (taille: {icon_size}px)")
            else:
                print(f"⚠️ Image non trouvée: {image_name}")
                # Image par défaut si l'image n'est pas trouvée
                btn.setText(f" {text}")
        except Exception as e:
            print(f"❌ Erreur chargement image {image_name}: {e}")
        btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
)

        return btn

    def format_packets_display(self):
        if self.total_packets == 0:
            return " 0 paquet\nAucune activité"
        return f" {self.total_packets:,} paquets".replace(",", " ")

    def format_attacks_display(self):
        total = self.attack_stats['total_attacks']
        last_hour = self.attack_stats['last_hour_attacks']

        if total == 0:
            return " 0 attaque\n Système sécurisé"
        return f" {total} attaques\n +{last_hour} dernière heure"

    def format_risk_display(self):
        if self.attack_stats['total_attacks'] == 0:
            return "0%\n🟢 Aucune menace\nSystème sécurisé"

        if self.risk_level == 0:
            return "0%\n🟢 Risque nul\nAucune alerte"
        elif self.risk_level < 30:
            return f"{self.risk_level}%\n🟢 Risque Faible"
        elif self.risk_level < 60:
            return f"{self.risk_level}%\n🟡 Risque Moyen"
        else:
            return f"{self.risk_level}%\n🔴 Risque Élevé"

    def update_data_from_db(self):
        self.attack_stats = self.db_manager.get_attack_stats()
        self.total_packets = self.db_manager.get_total_packets()
        self.risk_level = self.db_manager.calculate_risk_level()

    def refresh_dashboard(self):
        try:
            old_total = self.attack_stats['total_attacks']
            self.update_data_from_db()

            self.update_frame_content(self.cadre1, self.format_packets_display())

            new_attacks = self.attack_stats['total_attacks']
            new_last_hour = self.attack_stats['last_hour_attacks']

            attack_indicator = ""
            if new_attacks > old_total:
                attack_indicator = " ⬆️"
            elif new_attacks < old_total:
                attack_indicator = " ⬇️"

            if new_attacks == 0:
                new_content2 = " 0 attaque\n Système sécurisé"
            else:
                new_content2 = f" {new_attacks} attaques{attack_indicator}\n +{new_last_hour} dernière heure"

            self.update_frame_content(self.cadre2, new_content2)
            self.update_frame_content(self.cadre3, self.format_risk_display())

            # Mise à jour de l'histogramme
            hist_data = self.db_manager.get_attacks_last_24h()
            self.histogram.update_histogram(hist_data)

        except Exception as e:
            print(f"❌ Erreur: {e}")

    def update_frame_content(self, frame, new_content):
        for child in frame.children():
            if isinstance(child, QLabel) and child != frame.children()[1]:
                child.setText(new_content)
                break

    def create_inner_frame(self, title_text, content_text):
        frame = FocusableFrame()

        frame.setStyleSheet("""
            QFrame {
                background-color: #1E2E4F;
                border-radius: 20px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel(title_text)
        title.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-bottom: 2px solid #335889;
        """)
        layout.addWidget(title)

        content = QLabel(content_text)
        content.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
        """)
        content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(content)

        layout.addStretch()
        return frame

    def closeEvent(self, event):
        if hasattr(self, 'db_manager') and self.db_manager.connection:
            self.db_manager.connection.close()
            print("Connexion à la base de données fermée")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimplePage()
    window.show()
    sys.exit(app.exec())