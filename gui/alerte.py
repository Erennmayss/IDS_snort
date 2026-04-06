import sys
import os
import psycopg2
from datetime import datetime

# Permet d'importer depuis le dossier parent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout, QLineEdit,
    QDateEdit, QSpinBox, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QDate, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QThread, \
    pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

# === IMPORTATION DE NOTRE ARCHITECTURE ===
from config import DB_CONFIG, COLORS
from gui.components import AnimatedLabel, LoadingOverlay

# ================== STYLES MODERNES (SaaS) ==================
INPUT_STYLE = f"""
    QComboBox, QDateEdit, QLineEdit, QSpinBox {{
        background-color: #334155;  /* Fond plus clair pour les inputs */
        color: white;
        padding: 8px 12px;
        border: 1px solid #475569;
        border-radius: 6px;
        font-size: 13px;
    }}
    QComboBox:focus, QDateEdit:focus, QLineEdit:focus, QSpinBox:focus {{
        border: 1px solid {COLORS['info']};
        background-color: #3F51B5; /* Légère surbrillance au clic */
    }}
    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
    }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid white;
        width: 0;
        height: 0;
        margin-right: 8px;
    }}
"""

BTN_PRIMARY_STYLE = f"""
    QPushButton {{
        background-color: #0EA5E9; /* Bleu moderne et lumineux */
        color: white;
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: bold;
        border: none;
    }}
    QPushButton:hover {{
        background-color: #0284C7;
    }}
    QPushButton:pressed {{
        background-color: #0369A1;
    }}
"""

BTN_SECONDARY_STYLE = f"""
    QPushButton {{
        background-color: #334155; /* Plus clair que le fond */
        color: white;
        padding: 8px 15px;
        border-radius: 6px;
        font-weight: bold;
        border: 1px solid #475569;
    }}
    QPushButton:hover {{
        background-color: #475569;
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['accent']};
        border: 1px solid {COLORS['accent']};
    }}
"""


# ================== THREAD DE CHARGEMENT ==================
class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(list)
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, filters=None):
        super().__init__()
        self.filters = filters or {}
        self.running = True

    def run(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()

            query = """
            SELECT timestamp, source_ip, destination_ip, attack_type, severity, detection_engine
            FROM security_alerts WHERE 1=1
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
            cursor.execute(query, params)
            rows = cursor.fetchall()

            total_rows = len(rows)
            snort_data = []

            for i, row in enumerate(rows):
                if not self.running: break
                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                src, dst, attack, severity, engine = row[1], row[2], row[3], row[4], row[5]
                if engine.lower() == "snort":
                    snort_data.append([date, src, dst, attack, severity])
                if i % 100 == 0:
                    self.progress_update.emit(int((i + 1) / total_rows * 100) if total_rows > 0 else 0)

            self.progress_update.emit(100)
            self.data_loaded.emit(snort_data)

        except psycopg2.OperationalError as e:
            self.error_occurred.emit(f"Erreur DB: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Erreur chargement: {str(e)}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

    def stop(self):
        self.running = False


# ================== INTERFACE PRINCIPALE ==================
class AlertInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Système de Détection d'Intrusions - Alertes Snort")

        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height() - 80)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        self.current_page = 1
        self.items_per_page = 100
        self.all_snort_data = []
        self.loader_thread = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.title = AnimatedLabel("🛡️ DÉTECTION SNORT - ALERTES RÉSEAU")
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

        self.timestamp_label = QLabel()
        self.timestamp_label.setFont(QFont("Arial", 11))
        self.timestamp_label.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
        self.update_timestamp()
        main_layout.addWidget(self.timestamp_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.setup_filter_bar(main_layout)
        self.setup_table(main_layout)
        self.setup_pagination_bar(main_layout)
        self.setup_stats_bar(main_layout)

        self.loading_overlay = LoadingOverlay(self.centralWidget())
        self.loading_overlay.hide()
        self.loading_overlay.raise_()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_alerts)
        self.timer.start(30000)

        self.load_alerts_async()

    def setup_filter_bar(self, parent_layout):
        filter_widget = QGroupBox("Filtres d'analyse")
        filter_widget.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text']};
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                padding-bottom: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }}
        """)
        filter_layout = QGridLayout()
        filter_layout.setSpacing(15)

        gravite_label = QLabel("Gravité :")
        gravite_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(gravite_label, 0, 0)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["Toutes", "Élevée", "Moyenne", "Basse"])
        self.severity_combo.currentTextChanged.connect(self.on_filter_changed)
        self.severity_combo.setStyleSheet(INPUT_STYLE)
        filter_layout.addWidget(self.severity_combo, 0, 1)

        attack_label = QLabel("Type d'attaque :")
        attack_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(attack_label, 0, 2)

        self.attack_type_combo = QComboBox()
        self.populate_attack_types()
        self.attack_type_combo.currentTextChanged.connect(self.on_filter_changed)
        self.attack_type_combo.setStyleSheet(INPUT_STYLE)
        filter_layout.addWidget(self.attack_type_combo, 0, 3)

        date_label = QLabel("Date :")
        date_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(date_label, 0, 4)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.on_filter_changed)
        self.date_edit.setMinimumWidth(130)
        self.date_edit.setStyleSheet(INPUT_STYLE)
        filter_layout.addWidget(self.date_edit, 0, 5)

        ip_label = QLabel("Recherche IP :")
        ip_label.setStyleSheet("color: white; font-weight: bold;")
        filter_layout.addWidget(ip_label, 0, 6)

        self.search_ip = QLineEdit()
        self.search_ip.setPlaceholderText("Ex: 192.168...")
        self.search_ip.textChanged.connect(self.on_filter_changed)
        self.search_ip.setStyleSheet(INPUT_STYLE)
        filter_layout.addWidget(self.search_ip, 0, 7)

        refresh_button = QPushButton("🔄 Appliquer / Rafraîchir")
        refresh_button.clicked.connect(self.refresh_alerts)
        refresh_button.setStyleSheet(BTN_PRIMARY_STYLE)
        filter_layout.addWidget(refresh_button, 0, 8)

        filter_widget.setLayout(filter_layout)
        parent_layout.addWidget(filter_widget)

    def on_filter_changed(self):
        if hasattr(self, 'filter_timer'):
            self.filter_timer.stop()
        else:
            self.filter_timer = QTimer()
            self.filter_timer.setSingleShot(True)
            self.filter_timer.timeout.connect(self.apply_filters)
        self.filter_timer.start(500)

    def populate_attack_types(self):
        self.attack_type_combo.clear()
        self.attack_type_combo.addItem("Tous")

        class AttackTypesLoader(QThread):
            finished = pyqtSignal(list)

            def run(self):
                types = ["Tous"]
                try:
                    conn = psycopg2.connect(**DB_CONFIG)
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT attack_type::text FROM security_alerts ORDER BY attack_type")
                    for row in cur.fetchall():
                        if row[0]: types.append(str(row[0]))
                    cur.close()
                    conn.close()
                except Exception:
                    pass
                finally:
                    self.finished.emit(types)

        self.attack_loader = AttackTypesLoader()
        self.attack_loader.finished.connect(lambda types: self.attack_type_combo.addItems(types[1:]))
        self.attack_loader.start()

    def setup_pagination_bar(self, parent_layout):
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)

        self.prev_button = QPushButton("◀ Précédent")
        self.prev_button.setStyleSheet(BTN_SECONDARY_STYLE)
        self.prev_button.clicked.connect(self.previous_page)

        self.page_label = QLabel("Page 1")
        self.page_label.setStyleSheet(
            f"color: white; font-weight: bold; padding: 8px 15px; background-color: {COLORS['accent']}; border-radius: 6px;")

        self.next_button = QPushButton("Suivant ▶")
        self.next_button.setStyleSheet(BTN_SECONDARY_STYLE)
        self.next_button.clicked.connect(self.next_page)

        self.items_per_page_spin = QSpinBox()
        self.items_per_page_spin.setRange(10, 500)
        self.items_per_page_spin.setValue(100)
        self.items_per_page_spin.setSingleStep(10)
        self.items_per_page_spin.valueChanged.connect(self.items_per_page_changed)
        self.items_per_page_spin.setStyleSheet(INPUT_STYLE)

        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(QLabel("Alertes par page :", styleSheet="color: white; font-weight: bold;"))
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
        max_pages = (len(self.all_snort_data) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < max_pages:
            self.current_page += 1
            self.update_pagination_display()
            self.load_current_page()

    def update_pagination_display(self):
        self.page_label.setText(f"Page {self.current_page}")
        max_pages = (len(self.all_snort_data) + self.items_per_page - 1) // self.items_per_page
        max_pages = max_pages if max_pages > 0 else 1
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < max_pages)

    def load_current_page(self):
        start_idx = (self.current_page - 1) * self.items_per_page
        snort_page = self.all_snort_data[start_idx:start_idx + self.items_per_page]
        self.populate_table_batch(self.snort_table, snort_page)
        self.update_statistics()

    def setup_table(self, parent_layout):
        self.snort_table = QTableWidget()
        self.snort_table.setColumnCount(5)
        self.snort_table.setHorizontalHeaderLabels(["Date", "IP Source", "IP Destination", "Type Attaque", "Gravité"])
        self.snort_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {COLORS['bg_medium']}; 
                alternate-background-color: {COLORS['bg_dark']}; 
                color: white; 
                gridline-color: {COLORS['accent']}; 
                selection-background-color: {COLORS['info']}; 
                selection-color: {COLORS['bg_dark']}; 
                border-radius: 8px; 
                border: 1px solid #334155;
            }}
            QHeaderView::section {{ 
                background-color: #0B1120; 
                color: {COLORS['text_bright']}; 
                padding: 12px; 
                border: none; 
                border-right: 1px solid {COLORS['accent']};
                border-bottom: 2px solid {COLORS['info']};
                font-weight: bold; 
            }}
        """)
        header = self.snort_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.snort_table.setAlternatingRowColors(True)

        parent_layout.addWidget(self.snort_table)

    def setup_stats_bar(self, parent_layout):
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        self.total_stats = QLabel("🛡️ Alertes Snort: 0",
                                  styleSheet=f"background-color: #0EA5E9; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold;")

        stats_layout.addStretch()
        stats_layout.addWidget(self.total_stats)
        parent_layout.addWidget(stats_widget)

    def load_alerts_async(self):
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()

        self.loading_overlay.show_with_fade()
        filters = {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'severity': self.severity_combo.currentText(),
            'attack_type': self.attack_type_combo.currentText(),
            'ip_search': self.search_ip.text().strip()
        }

        self.loader_thread = DataLoaderThread(filters)
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.progress_update.connect(self.loading_overlay.update_progress)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.finished.connect(lambda: self.loading_overlay.hide_with_fade())
        self.loader_thread.start()

    def on_data_loaded(self, snort_data):
        self.all_snort_data = snort_data
        self.current_page = 1
        self.update_pagination_display()
        self.load_current_page()
        self.update_timestamp()

        heure_actuelle = datetime.now().strftime('%H:%M:%S')
        print(f"[{heure_actuelle}] ✅ Alertes récupérées | Total: {len(snort_data)}")

    def on_load_error(self, error_message):
        QMessageBox.warning(self, "Erreur BDD", f"{error_message}\n\nChargement des données de simulation...")
        heure_actuelle = datetime.now().strftime('%H:%M:%S')
        print(f"[{heure_actuelle}] ❌ Erreur critique BDD : {error_message}")
        self.load_sample_data()

    def load_sample_data(self):
        self.all_snort_data = []
        attacks_snort = ["ICMP Flood", "Port Scan", "SQL Injection", "XSS"]
        severities = ["Élevée", "Moyenne", "Basse"]

        for i in range(150):
            date = f"14/03/2026 {15 + i // 10:02d}:{i % 60:02d}:{i % 60:02d}"
            src = f"10.0.0.{i % 255}"
            dst = f"192.168.1.{(i + 30) % 255}"
            attack = attacks_snort[i % len(attacks_snort)]
            severity = severities[i % len(severities)]
            self.all_snort_data.append([date, src, dst, attack, severity])

        self.current_page = 1
        self.update_pagination_display()
        self.load_current_page()
        self.update_timestamp()

    def populate_table_batch(self, table, data):
        table.setUpdatesEnabled(False)
        table.setRowCount(len(data))
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col == 4:
                    if value == "Élevée":
                        item.setBackground(QColor(COLORS['danger']))
                    elif value == "Moyenne":
                        item.setBackground(QColor(COLORS['warning']))
                    elif value == "Basse":
                        item.setBackground(QColor(COLORS['success']))
                        item.setForeground(QColor(COLORS['bg_dark']))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)
        table.setUpdatesEnabled(True)

    def update_timestamp(self):
        self.timestamp_label.setText(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    def update_statistics(self):
        self.total_stats.setText(
            f"🛡️ Total Alertes Snort : {self.snort_table.rowCount()} affichées / {len(self.all_snort_data)} globales")

    def refresh_alerts(self):
        self.load_alerts_async()

    def apply_filters(self):
        self.load_alerts_async()

    def closeEvent(self, event):
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlertInterface()
    window.show()
    sys.exit(app.exec())