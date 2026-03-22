import sys
import psycopg2
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QComboBox,
    QTabWidget, QGroupBox, QGridLayout, QLineEdit,
    QDateEdit, QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QSpinBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QDate, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, \
    pyqtProperty, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette, QMovie

# ================== CONFIGURATION BASE DE DONNEES ==================
db_config = {
    'host': '192.168.1.2',
    'database': 'ids_db',
    'user': 'marwa',
    'password': 'marwa',
    'port': '5432',
    'connect_timeout': 5  # Timeout de connexion
}


# ================== THREAD DE CHARGEMENT DES DONNÉES ==================
class DataLoaderThread(QThread):
    """Thread pour charger les données sans bloquer l'interface"""

    data_loaded = pyqtSignal(list, list)  # Signaux pour les données ML et Snort
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, filters=None):
        super().__init__()
        self.filters = filters or {}
        self.running = True

    def run(self):
        """Méthode exécutée dans le thread"""
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # Construction de la requête avec les filtres
            query = """
            SELECT timestamp, source_ip, destination_ip, attack_type, severity, detection_engine
            FROM security_alerts
            WHERE 1=1
            """
            params = []

            if self.filters.get('date'):
                query += " AND DATE(timestamp) = %s"
                params.append(self.filters['date'])

            if self.filters.get('severity') and self.filters['severity'] != "Toutes":
                query += " AND severity = %s"
                params.append(self.filters['severity'])

            if self.filters.get('attack_type') and self.filters['attack_type'] != "Tous":
                query += " AND attack_type = %s"
                params.append(self.filters['attack_type'])

            if self.filters.get('ip_search'):
                ip_pattern = f"%{self.filters['ip_search']}%"
                query += " AND (source_ip LIKE %s OR destination_ip LIKE %s)"
                params.extend([ip_pattern, ip_pattern])

            query += " ORDER BY timestamp DESC"

            # Exécution de la requête
            cursor.execute(query, params)
            rows = cursor.fetchall()

            total_rows = len(rows)
            ml_data = []
            snort_data = []

            for i, row in enumerate(rows):
                if not self.running:
                    break

                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                src, dst, attack, severity, engine = row[1], row[2], row[3], row[4], row[5]
                data = [date, src, dst, attack, severity]

                if engine.lower() == "ml":
                    ml_data.append(data)
                elif engine.lower() == "snort":
                    snort_data.append(data)

                # Mise à jour de la progression
                if i % 100 == 0:  # Mettre à jour tous les 100 enregistrements
                    progress = int((i + 1) / total_rows * 100) if total_rows > 0 else 0
                    self.progress_update.emit(progress)

            self.progress_update.emit(100)
            self.data_loaded.emit(ml_data, snort_data)

        except psycopg2.OperationalError as e:
            self.error_occurred.emit(f"Erreur de connexion à la base de données: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors du chargement: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def stop(self):
        """Arrêter le thread proprement"""
        self.running = False


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


# ================== WIDGET DE CHARGEMENT ==================
class LoadingOverlay(QWidget):
    """Overlay de chargement avec animation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Conteneur pour l'animation
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 46, 79, 200);
                border-radius: 20px;
                padding: 30px;
            }
        """)
        container_layout = QVBoxLayout(container)

        # Label avec animation GIF
        self.loading_label = QLabel()
        self.movie = QMovie("loading.gif")  # Vous pouvez utiliser une animation personnalisée
        if self.movie.isValid():
            self.loading_label.setMovie(self.movie)
        else:
            # Fallback text
            self.loading_label.setText("Chargement en cours...")
            self.loading_label.setStyleSheet("""
                QLabel {
                    color: #9b59b6;
                    font-size: 24px;
                    font-weight: bold;
                    padding: 30px;
                }
            """)

        container_layout.addWidget(self.loading_label)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #9b59b6;
                border-radius: 10px;
                text-align: center;
                color: white;
                background-color: #2F4166;
            }
            QProgressBar::chunk {
                background-color: #9b59b6;
                border-radius: 8px;
            }
        """)
        container_layout.addWidget(self.progress_bar)

        layout.addWidget(container)

        # Animation d'apparition
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)

    def showEvent(self, event):
        if self.movie.isValid():
            self.movie.start()
        super().showEvent(event)

    def hideEvent(self, event):
        if self.movie.isValid():
            self.movie.stop()
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

        # Variables de pagination
        self.current_page = 1
        self.items_per_page = 100
        self.total_ml_alerts = 0
        self.total_snort_alerts = 0
        self.all_ml_data = []
        self.all_snort_data = []

        # Thread de chargement
        self.loader_thread = None

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

        # Barre de pagination
        self.setup_pagination_bar(main_layout)

        # Barre de statistiques
        self.setup_stats_bar(main_layout)

        # Overlay de chargement
        self.loading_overlay = LoadingOverlay(self.centralWidget())
        self.loading_overlay.hide()
        self.loading_overlay.raise_()

        # Timer pour mise à jour automatique (moins fréquent pour éviter les blocages)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_alerts)
        self.timer.start(30000)  # 30 secondes au lieu de 5

        # Charger les données depuis la base (asynchrone)
        self.load_alerts_async()

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
        self.severity_combo.currentTextChanged.connect(self.on_filter_changed)
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
        self.populate_attack_types()
        self.attack_type_combo.currentTextChanged.connect(self.on_filter_changed)
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
        self.date_edit.dateChanged.connect(self.on_filter_changed)
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
        self.search_ip.textChanged.connect(self.on_filter_changed)
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

        # Bouton de rafraîchissement
        refresh_button = QPushButton("🔄 Rafraîchir")
        refresh_button.clicked.connect(self.refresh_alerts)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                border: 2px solid #8e44ad;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #6c3483;
            }
        """)
        filter_layout.addWidget(refresh_button, 0, 8)

        filter_widget.setLayout(filter_layout)
        parent_layout.addWidget(filter_widget)

    def on_filter_changed(self):
        """Appelé quand un filtre change - charge les données avec délai pour éviter trop de requêtes"""
        # Annuler le timer précédent
        if hasattr(self, 'filter_timer'):
            self.filter_timer.stop()
        else:
            self.filter_timer = QTimer()
            self.filter_timer.setSingleShot(True)
            self.filter_timer.timeout.connect(self.apply_filters)

        # Démarrer le timer (500ms de délai)
        self.filter_timer.start(500)

    def populate_attack_types(self):
        """Remplir la liste des types d'attaque de manière asynchrone"""
        self.attack_type_combo.clear()
        self.attack_type_combo.addItem("Tous")

        # Charger les types d'attaque dans un thread séparé
        class AttackTypesLoader(QThread):
            finished = pyqtSignal(list)

            def run(self):
                types = ["Tous"]
                try:
                    conn = psycopg2.connect(**db_config)
                    cur = conn.cursor()
                    query = "SELECT DISTINCT attack_type::text FROM security_alerts ORDER BY attack_type"
                    cur.execute(query)
                    rows = cur.fetchall()

                    for row in rows:
                        if row[0]:
                            types.append(str(row[0]))

                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"Erreur lors du chargement des types: {e}")
                finally:
                    self.finished.emit(types)

        self.attack_loader = AttackTypesLoader()
        self.attack_loader.finished.connect(lambda types: self.attack_type_combo.addItems(types[1:]))
        self.attack_loader.start()

    # ================== PAGINATION ==================
    def setup_pagination_bar(self, parent_layout):
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)

        # Bouton précédent
        self.prev_button = QPushButton("◀ Précédent")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #2F4166;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                border: 2px solid #335889;
            }
            QPushButton:hover {
                background-color: #335889;
            }
            QPushButton:pressed {
                background-color: #1E2E4F;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
                border: 2px solid #555;
            }
        """)
        self.prev_button.clicked.connect(self.previous_page)

        # Label page
        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                padding: 8px 15px;
                background-color: #9b59b6;
                border-radius: 5px;
            }
        """)

        # Bouton suivant
        self.next_button = QPushButton("Suivant ▶")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #2F4166;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                border: 2px solid #335889;
            }
            QPushButton:hover {
                background-color: #335889;
            }
            QPushButton:pressed {
                background-color: #1E2E4F;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
                border: 2px solid #555;
            }
        """)
        self.next_button.clicked.connect(self.next_page)

        # Items per page
        self.items_per_page_label = QLabel("Alertes par page:")
        self.items_per_page_label.setStyleSheet("color: white; font-weight: bold;")

        self.items_per_page_spin = QSpinBox()
        self.items_per_page_spin.setMinimum(10)
        self.items_per_page_spin.setMaximum(500)
        self.items_per_page_spin.setValue(100)
        self.items_per_page_spin.setSingleStep(10)
        self.items_per_page_spin.valueChanged.connect(self.items_per_page_changed)
        self.items_per_page_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2F4166;
                color: white;
                padding: 5px;
                border: 1px solid #335889;
                border-radius: 5px;
            }
        """)

        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.items_per_page_label)
        pagination_layout.addWidget(self.items_per_page_spin)

        parent_layout.addWidget(pagination_widget)

    def items_per_page_changed(self, value):
        self.items_per_page = value
        self.current_page = 1
        self.update_pagination_display()
        self.load_current_page()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pagination_display()
            self.load_current_page()

    def next_page(self):
        max_pages_ml = (len(self.all_ml_data) + self.items_per_page - 1) // self.items_per_page
        max_pages_snort = (len(self.all_snort_data) + self.items_per_page - 1) // self.items_per_page
        max_pages = max(max_pages_ml, max_pages_snort)

        if self.current_page < max_pages:
            self.current_page += 1
            self.update_pagination_display()
            self.load_current_page()

    def update_pagination_display(self):
        self.page_label.setText(f"Page {self.current_page}")

        # Activer/désactiver boutons
        max_pages_ml = (len(self.all_ml_data) + self.items_per_page - 1) // self.items_per_page
        max_pages_snort = (len(self.all_snort_data) + self.items_per_page - 1) // self.items_per_page
        max_pages = max(max_pages_ml, max_pages_snort) if max_pages_ml > 0 or max_pages_snort > 0 else 1

        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < max_pages)

    def load_current_page(self):
        """Charger la page actuelle sans bloquer l'interface"""
        # Charger la page actuelle pour ML
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.all_ml_data))
        ml_page_data = self.all_ml_data[start_idx:end_idx] if start_idx < len(self.all_ml_data) else []

        # Charger la page actuelle pour Snort
        start_idx_snort = (self.current_page - 1) * self.items_per_page
        end_idx_snort = min(start_idx_snort + self.items_per_page, len(self.all_snort_data))
        snort_page_data = self.all_snort_data[start_idx_snort:end_idx_snort] if start_idx_snort < len(
            self.all_snort_data) else []

        # Mettre à jour les tableaux (en lots pour éviter le blocage)
        self.populate_table_batch(self.ml_table, ml_page_data)
        self.populate_table_batch(self.snort_table, snort_page_data)

        # Mettre à jour les statistiques
        self.update_statistics()

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

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

    # ================== CHARGEMENT ASYNCHRONE DES ALERTES ==================
    def load_alerts_async(self):
        """Charger les alertes de manière asynchrone"""
        # Arrêter le thread précédent s'il existe
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()

        # Afficher l'overlay de chargement
        self.loading_overlay.show_with_fade()
        self.loading_overlay.update_progress(0)

        # Préparer les filtres
        filters = {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'severity': self.severity_combo.currentText(),
            'attack_type': self.attack_type_combo.currentText(),
            'ip_search': self.search_ip.text().strip()
        }

        # Créer et démarrer le thread de chargement
        self.loader_thread = DataLoaderThread(filters)
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.progress_update.connect(self.loading_overlay.update_progress)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.finished.connect(lambda: self.loading_overlay.hide_with_fade())
        self.loader_thread.start()

    def on_data_loaded(self, ml_data, snort_data):
        """Appelé quand les données sont chargées"""
        self.all_ml_data = ml_data
        self.all_snort_data = snort_data

        self.current_page = 1
        self.update_pagination_display()
        self.load_current_page()

        # Mettre à jour l'horodatage
        self.update_timestamp()

    def on_load_error(self, error_message):
        """Appelé en cas d'erreur de chargement"""
        QMessageBox.warning(self, "Erreur de chargement", error_message)

        # Charger des données d'exemple en cas d'erreur
        self.load_sample_data()

    def populate_table_batch(self, table, data):
        """Remplir le tableau par lots pour éviter le blocage"""
        table.setUpdatesEnabled(False)  # Désactiver les mises à jour pendant le remplissage
        table.setRowCount(len(data))

        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))

                # Colorer selon la gravité (colonne 4)
                if col == 4:
                    if value == "Élevée":
                        item.setBackground(QColor("#920004"))
                        item.setForeground(QColor("white"))
                    elif value == "Moyenne":
                        item.setBackground(QColor("#d24e01"))
                        item.setForeground(QColor("black"))
                    elif value == "Basse":
                        item.setBackground(QColor("#2B7337"))
                        item.setForeground(QColor("black"))

                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)

            # Permettre à l'interface de respirer
            if row % 50 == 0:
                QApplication.processEvents()

        table.setUpdatesEnabled(True)  # Réactiver les mises à jour

    def load_sample_data(self):
        """Charger des données d'exemple (utilisé en cas d'erreur)"""
        self.all_ml_data = []
        self.all_snort_data = []

        # Générer 250 alertes ML pour tester
        attacks_ml = ["DoS", "Brute Force", "Scan Port", "Malware"]
        severities = ["Élevée", "Moyenne", "Basse"]

        for i in range(250):
            date = f"14/03/2024 {14 + i // 10:02d}:{i % 60:02d}:{i % 60:02d}"
            src = f"192.168.1.{i % 255}"
            dst = f"192.168.1.{(i + 50) % 255}"
            attack = attacks_ml[i % len(attacks_ml)]
            severity = severities[i % len(severities)]
            self.all_ml_data.append([date, src, dst, attack, severity])

        # Générer 150 alertes Snort
        attacks_snort = ["ICMP Flood", "Port Scan", "SQL Injection", "XSS"]

        for i in range(150):
            date = f"14/03/2024 {15 + i // 10:02d}:{i % 60:02d}:{i % 60:02d}"
            src = f"10.0.0.{i % 255}"
            dst = f"192.168.1.{(i + 30) % 255}"
            attack = attacks_snort[i % len(attacks_snort)]
            severity = severities[i % len(severities)]
            self.all_snort_data.append([date, src, dst, attack, severity])

        self.current_page = 1
        self.update_pagination_display()
        self.load_current_page()

    # ================== HORODATAGE ==================
    def update_timestamp(self):
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.timestamp_label.setText(f"Dernière mise à jour: {current_time}")

    # ================== STATISTIQUES ==================
    def update_statistics(self):
        ml_visible = self.ml_table.rowCount()
        snort_visible = self.snort_table.rowCount()
        total_ml = len(self.all_ml_data)
        total_snort = len(self.all_snort_data)

        self.ml_stats.setText(f"🤖 ML: {ml_visible}/{total_ml} alertes (page {self.current_page})")
        self.snort_stats.setText(f"🛡️ Snort: {snort_visible}/{total_snort} alertes (page {self.current_page})")
        self.total_stats.setText(f"📊 Total: {ml_visible + snort_visible} affichées / {total_ml + total_snort} totales")

    # ================== RAFRAÎCHISSEMENT ==================
    def refresh_alerts(self):
        self.load_alerts_async()

    # ================== FILTRES ==================
    def apply_filters(self):
        """Appliquer les filtres en rechargeant les données"""
        self.load_alerts_async()

    def closeEvent(self, event):
        """Nettoyer les threads à la fermeture"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()
        event.accept()


# ================== LANCEMENT ==================
def main():
    app = QApplication(sys.argv)

    # Créer une animation de chargement par défaut si le GIF n'existe pas
    # Vous pouvez créer un fichier loading.gif ou utiliser une animation CSS

    window = AlertInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()