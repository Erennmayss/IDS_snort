import sys
import psycopg2
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QComboBox,
    QTabWidget, QGroupBox, QGridLayout, QLineEdit,
    QDateEdit, QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QDate, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, \
    pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPalette

# ================== CONFIGURATION BASE DE DONNEES ==================
db_config = {
    'host': '192.168.1.2',
    'database': 'ids_db',
    'user': 'marwa',
    'password': 'marwa',
    'port': '5432'

}
listen_addresses = '*'


def connect_db():
    try:
        conn = psycopg2.connect(**db_config)
        return conn
    except Exception as e:
        print("Erreur connexion DB:", e)
        return None


# ================== LABEL ANIMÉ ==================
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


# ================== FRAME AVEC EFFET DE FOCUS ==================
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


# ================== INTERFACE PRINCIPALE ==================
class AlertInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Système de Détection d'Intrusions - Interface Alertes")

        # Configuration plein écran
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height() - 80)

        # Style de fond sombre
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1E2E4F"))
        self.setPalette(palette)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Titre animé
        self.title = AnimatedLabel("🔔 ALERTES DE SÉCURITÉ")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title)

        # Animations du titre
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

        # Horodatage
        self.timestamp_label = QLabel()
        timestamp_font = QFont("Arial", 12)
        self.timestamp_label.setFont(timestamp_font)
        self.timestamp_label.setStyleSheet("color: white; padding: 10px;")
        self.update_timestamp()
        main_layout.addWidget(self.timestamp_label, alignment=Qt.AlignmentFlag.AlignRight)

        # Barre de filtres
        self.setup_filter_bar(main_layout)

        # Zone d'onglets
        self.setup_tabs(main_layout)

        # Barre de statistiques
        self.setup_stats_bar(main_layout)

        # Timer pour mise à jour automatique
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_alerts)
        self.timer.start(5000)

        # Charger les données depuis la base
        self.load_alerts_from_db()

    # ================== FILTRES ==================
    def setup_filter_bar(self, parent_layout):
        filter_widget = QGroupBox("Filtres")
        filter_widget.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 2px solid #335889;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        filter_layout = QGridLayout()

        # Gravité
        gravite_label = QLabel("Gravité:")
        gravite_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(gravite_label, 0, 0)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Toutes", "Élevée", "Moyenne", "Basse"])
        self.severity_combo.currentTextChanged.connect(self.apply_filters)
        self.severity_combo.setStyleSheet("""
            QComboBox {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.severity_combo, 0, 1)

        # Type d'attaque
        attack_label = QLabel("Type d'attaque:")
        attack_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(attack_label, 0, 2)

        self.attack_type_combo = QComboBox()
        self.populate_attack_types()  # MODIFICATION : Renommé pour être plus explicite
        self.attack_type_combo.currentTextChanged.connect(self.apply_filters)
        self.attack_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.attack_type_combo, 0, 3)

        # Date
        date_label = QLabel("Date:")
        date_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(date_label, 0, 4)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.apply_filters)
        self.date_edit.setMinimumWidth(150)
        self.date_edit.setFixedWidth(200)
        self.date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
                min-width: 150px;
                max-width: 200px;
            }
            QDateEdit::drop-down {
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                width: 0;
                height: 0;
            }
        """)
        filter_layout.addWidget(self.date_edit, 0, 5)

        # Recherche IP
        ip_label = QLabel("Recherche IP:")
        ip_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(ip_label, 0, 6)

        self.search_ip = QLineEdit()
        self.search_ip.setPlaceholderText("Entrez une IP...")
        self.search_ip.textChanged.connect(self.apply_filters)
        self.search_ip.setMinimumWidth(150)
        self.search_ip.setStyleSheet("""
            QLineEdit {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        filter_layout.addWidget(self.search_ip, 0, 7)

        filter_widget.setLayout(filter_layout)
        parent_layout.addWidget(filter_widget)

    def populate_attack_types(self):  # MODIFICATION : Renommé pour être plus explicite
        conn = None
        try:
            # Connexion à PostgreSQL
            conn = psycopg2.connect(**db_config)
            cur = conn.cursor()

            # Récupération des types d'attaque uniques
            query = "SELECT DISTINCT attack_type::text FROM security_alerts ORDER BY attack_type"
            cur.execute(query)

            rows = cur.fetchall()

            self.attack_type_combo.clear()
            self.attack_type_combo.addItem("Tous")

            for row in rows:
                if row[0]:  # Vérifier que ce n'est pas null
                    self.attack_type_combo.addItem(str(row[0]))

            cur.close()
        except Exception as e:
            print(f"Erreur lors du remplissage des types d'attaque : {e}")
            # Ajouter quelques types par défaut en cas d'erreur
            self.attack_type_combo.addItems(["Tous", "DoS", "Brute Force", "Scan Port", "Malware"])
        finally:
            if conn:
                conn.close()

    # ================== ONGLETS ==================
    def setup_tabs(self, parent_layout):
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #335889;
                border-radius: 10px;
                background-color: #1E2E4F;
            }
            QTabBar::tab {
                background-color: #2F4166;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #9b59b6;
            }
            QTabBar::tab:hover {
                background-color: #335889;
            }
        """)

        # Onglet ML
        self.ml_tab = QWidget()
        self.ml_tab.setStyleSheet("background-color: #1E2E4F;")
        self.setup_ml_tab()
        self.tab_widget.addTab(self.ml_tab, "🤖 Détection ML")

        # Onglet Snort
        self.snort_tab = QWidget()
        self.snort_tab.setStyleSheet("background-color: #1E2E4F;")
        self.setup_snort_tab()
        self.tab_widget.addTab(self.snort_tab, "🛡️ Détection Snort")

        parent_layout.addWidget(self.tab_widget)

    def setup_ml_tab(self):
        layout = QVBoxLayout(self.ml_tab)

        self.ml_table = QTableWidget()
        self.ml_table.setColumnCount(5)
        self.ml_table.setHorizontalHeaderLabels(["Date", "IP Source", "IP Destination", "Type Attaque", "Gravité"])

        # Style du tableau
        self.ml_table.setStyleSheet("""
            QTableWidget {
                background-color: #2F4166;
                alternate-background-color: #335889;
                color: white;
                gridline-color: #9b59b6;
                selection-background-color: #9b59b6;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1E2E4F;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)

        # Ajustement des largeurs de colonnes
        header = self.ml_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # IP Source
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # IP Destination
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Type Attaque
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Gravité

        self.ml_table.setAlternatingRowColors(True)
        self.ml_table.setSortingEnabled(True)
        layout.addWidget(self.ml_table)

    def setup_snort_tab(self):
        layout = QVBoxLayout(self.snort_tab)

        self.snort_table = QTableWidget()
        self.snort_table.setColumnCount(5)
        self.snort_table.setHorizontalHeaderLabels(["Date", "IP Source", "IP Destination", "Type Attaque", "Gravité"])

        # Style du tableau
        self.snort_table.setStyleSheet("""
            QTableWidget {
                background-color: #2F4166;
                alternate-background-color: #335889;
                color: white;
                gridline-color: #9b59b6;
                selection-background-color: #9b59b6;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1E2E4F;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)

        # Ajustement des largeurs de colonnes
        header = self.snort_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # IP Source
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # IP Destination
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Type Attaque
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Gravité

        self.snort_table.setAlternatingRowColors(True)
        self.snort_table.setSortingEnabled(True)
        layout.addWidget(self.snort_table)

    # ================== STATISTIQUES ==================
    def setup_stats_bar(self, parent_layout):
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        self.ml_stats = QLabel("🤖 ML: 0 alertes")
        self.ml_stats.setStyleSheet("""
            QLabel {
                background-color: #2F4166;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)

        self.snort_stats = QLabel("🛡️ Snort: 0 alertes")
        self.snort_stats.setStyleSheet("""
            QLabel {
                background-color: #2F4166;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #335889;
            }
        """)

        self.total_stats = QLabel("📊 Total: 0 alertes")
        self.total_stats.setStyleSheet("""
            QLabel {
                background-color: #9b59b6;
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-weight: bold;
                border: 2px solid #8e44ad;
            }
        """)

        stats_layout.addWidget(self.ml_stats)
        stats_layout.addWidget(self.snort_stats)
        stats_layout.addStretch()
        stats_layout.addWidget(self.total_stats)

        parent_layout.addWidget(stats_widget)

    # ================== CHARGEMENT DES ALERTES ==================
    def load_alerts_from_db(self):
        conn = connect_db()
        if conn is None:
            # Données de test si pas de connexion
            self.load_sample_data()
            return

        cursor = conn.cursor()
        query = """
        SELECT timestamp, source_ip, destination_ip, attack_type, severity, detection_engine
        FROM security_alerts
        ORDER BY timestamp DESC

        """

        try:
            cursor.execute(query)
            rows = cursor.fetchall()

            ml_data, snort_data = [], []
            for row in rows:
                # Format complet : date et heure avec secondes
                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                src, dst, attack, severity, engine = row[1], row[2], row[3], row[4], row[5]
                data = [date, src, dst, attack, severity]

                if engine.lower() == "ml":
                    ml_data.append(data)
                elif engine.lower() == "snort":
                    snort_data.append(data)

        except Exception as e:
            print("Erreur lors de la récupération des données:", e)
            ml_data, snort_data = [], []
            self.load_sample_data()
            return

        finally:
            cursor.close()
            conn.close()

        self.populate_table(self.ml_table, ml_data)
        self.populate_table(self.snort_table, snort_data)
        self.update_statistics()

    def load_sample_data(self):
        """Charger des données d'exemple avec timestamps complets si pas de connexion DB"""
        ml_data = [
            ["14/03/2024 14:22:15", "192.168.1.50", "192.168.1.10", "DoS", "Élevée"],
            ["14/03/2024 14:25:30", "10.0.0.15", "192.168.1.20", "Brute Force", "Élevée"],
            ["14/03/2024 14:30:45", "10.0.0.5", "192.168.1.15", "Scan Port", "Moyenne"],
            ["14/03/2024 14:35:20", "172.16.0.8", "192.168.1.25", "Malware", "Élevée"],
            ["14/03/2024 14:40:10", "192.168.1.100", "192.168.1.1", "DoS", "Basse"],
            ["14/03/2024 14:45:55", "10.0.0.25", "192.168.1.35", "Scan Port", "Moyenne"],
            ["14/03/2024 14:50:30", "172.16.0.12", "192.168.1.40", "Brute Force", "Élevée"],
        ]

        snort_data = [
            ["14/03/2024 14:23:10", "192.168.1.100", "192.168.1.1", "ICMP Flood", "Élevée"],
            ["14/03/2024 14:27:45", "10.0.0.50", "192.168.1.30", "Port Scan", "Moyenne"],
            ["14/03/2024 14:32:20", "172.16.0.20", "192.168.1.45", "SQL Injection", "Élevée"],
        ]

        self.populate_table(self.ml_table, ml_data)
        self.populate_table(self.snort_table, snort_data)
        self.update_statistics()

    def populate_table(self, table, data):
        table.setRowCount(len(data))

        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))

                # Colorer selon la gravité (colonne 4)
                if col == 4:
                    if value == "Élevée":
                        item.setBackground(QColor("#920004"))  # Rouge foncé
                        item.setForeground(QColor("white"))
                    elif value == "Moyenne":
                        item.setBackground(QColor("#d24e01"))  # Orange
                        item.setForeground(QColor("black"))
                    elif value == "Basse":
                        item.setBackground(QColor("#2B7337"))  # Vert
                        item.setForeground(QColor("black"))

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)

    # ================== HORODATAGE ==================
    def update_timestamp(self):
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.timestamp_label.setText(f"Dernière mise à jour: {current_time}")

    # ================== STATISTIQUES ==================
    def update_statistics(self):
        ml_visible = sum(not self.ml_table.isRowHidden(r) for r in range(self.ml_table.rowCount()))
        snort_visible = sum(not self.snort_table.isRowHidden(r) for r in range(self.snort_table.rowCount()))
        total = ml_visible + snort_visible

        self.ml_stats.setText(f"🤖 ML: {ml_visible} alertes")
        self.snort_stats.setText(f"🛡️ Snort: {snort_visible} alertes")
        self.total_stats.setText(f"📊 Total: {total} alertes")

    # ================== RAFRAÎCHISSEMENT ==================
    def refresh_alerts(self):
        self.update_timestamp()
        self.load_alerts_from_db()
        self.apply_filters()

    # ================== FILTRES ==================
    def apply_filters(self):
        # 1. On récupère les valeurs des filtres
        selected_severity = self.severity_combo.currentText()
        selected_attack_type = self.attack_type_combo.currentText()  # MODIFICATION : Récupération du type d'attaque
        ip_search_text = self.search_ip.text().lower().strip()

        # Formatage de la date du calendrier en chaîne "dd/MM/yyyy"
        filter_date_str = self.date_edit.date().toString("dd/MM/yyyy")

        for table in [self.ml_table, self.snort_table]:
            for row in range(table.rowCount()):
                show_row = True

                # Récupération de l'objet item et de son texte
                item_date = table.item(row, 0)
                if not item_date: continue

                full_timestamp = item_date.text()  # ex: "15/03/2026 14:30:05"

                # --- EXTRACTION DE LA DATE SEULE ---
                date_only_part = full_timestamp.split(' ')[0]  # donnera "15/03/2026"

                # --- TESTS DE FILTRAGE ---

                # 1. Comparaison stricte de la date
                if date_only_part != filter_date_str:
                    show_row = False

                # 2. Gravité
                if show_row and selected_severity != "Toutes":
                    if table.item(row, 4).text() != selected_severity:
                        show_row = False

                # 3. Type d'attaque - CORRECTION AJOUTÉE
                if show_row and selected_attack_type != "Tous":
                    if table.item(row, 3).text() != selected_attack_type:
                        show_row = False

                # 4. Recherche IP
                if show_row and ip_search_text:
                    src = table.item(row, 1).text().lower()
                    dst = table.item(row, 2).text().lower()
                    if ip_search_text not in src and ip_search_text not in dst:
                        show_row = False

                # On applique le masquage
                table.setRowHidden(row, not show_row)

        self.update_statistics()


# ================== LANCEMENT ==================
def main():
    app = QApplication(sys.argv)
    window = AlertInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()