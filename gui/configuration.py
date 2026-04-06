import re
import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QCheckBox, QSpinBox,
    QPushButton, QLabel, QTextEdit, QMessageBox,
    QTabWidget, QListWidget, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QColor, QPalette

# On importe les couleurs de ta config centrale pour la cohérence
from config import COLORS
from data.rules import afficher_db, ajouter_regle, modifier_regle, supprimer_regle, reset_db

# ================== STYLES UNIFIÉS (Inspire de alerte.py) ==================
INPUT_STYLE = f"""
    QComboBox, QDateEdit, QLineEdit, QSpinBox, QTextEdit, QListWidget {{
        background-color: #334155;
        color: white;
        padding: 8px;
        border: 1px solid {COLORS['accent']};
        border-radius: 6px;
    }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {COLORS['info']};
    }}
"""

BTN_PRIMARY_STYLE = """
    QPushButton {
        background-color: #0EA5E9;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover { background-color: #0284C7; }
"""

BTN_DANGER_STYLE = """
    QPushButton {
        background-color: #EF4444;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #B91C1C; }
"""

TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLORS['bg_medium']};
        alternate-background-color: {COLORS['bg_dark']};
        color: white;
        gridline-color: {COLORS['accent']};
        border-radius: 8px;
        border: 1px solid {COLORS['accent']};
    }}
    QHeaderView::section {{
        background-color: #0B1120;
        color: white;
        padding: 10px;
        border: none;
        border-bottom: 2px solid {COLORS['info']};
        font-weight: bold;
    }}
"""


class InterfaceParametresIDS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fichier_config = "configuration_ids.json"

        # Fond sombre SaaS
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        self.initUI()
        self.load_rules()

    def initUI(self):
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height() - 80)
        self.setWindowTitle("🔐 Configuration IDS - Console d'Administration")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # En-tête
        header_layout = QHBoxLayout()
        title_label = QLabel("🛡️ CONFIGURATION AVANCÉE DU SYSTÈME")
        title_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 20px; font-weight: bold; padding: 10px;")

        self.status_label = QLabel("● STATUT: ACTIF")
        self.status_label.setStyleSheet(
            f"color: {COLORS['success']}; background-color: #1E293B; padding: 8px 15px; border-radius: 6px; border: 1px solid {COLORS['accent']}; font-weight: bold;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)

        # Onglets stylisés
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLORS['accent']}; border-radius: 8px; background-color: {COLORS['bg_dark']}; }}
            QTabBar::tab {{ background-color: {COLORS['bg_medium']}; color: {COLORS['text']}; padding: 12px 25px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }}
            QTabBar::tab:selected {{ background-color: {COLORS['info']}; color: {COLORS['bg_dark']}; font-weight: bold; }}
        """)

        tabs.addTab(self.create_general_tab(), "⚙️ Général")
        tabs.addTab(self.create_seuils_tab(), "📊 Seuils")
        tabs.addTab(self.create_regles_tab(), "📋 Règles")
        tabs.addTab(self.create_securite_tab(), "🛡️ Sécurité Réseau")

        main_layout.addWidget(tabs)

        # Barre d'outils inférieure
        toolbar_layout = QHBoxLayout()
        self.btn_appliquer = QPushButton("🚀 APPLIQUER")
        self.btn_appliquer.setStyleSheet(BTN_PRIMARY_STYLE)
        self.btn_appliquer.clicked.connect(self.appliquer_configuration)

        self.btn_reset = QPushButton("🔄 RESET")
        self.btn_reset.setStyleSheet(BTN_DANGER_STYLE)
        self.btn_reset.clicked.connect(self.reset_configuration)

        self.btn_save = QPushButton("💾 SAUVEGARDER")
        self.btn_save.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", COLORS['accent']))
        self.btn_save.clicked.connect(self.sauvegarder_configuration)

        toolbar_layout.addWidget(self.btn_appliquer)
        toolbar_layout.addWidget(self.btn_reset)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addStretch()

        self.status_bar = QLabel("Prêt | Console synchronisée")
        self.status_bar.setStyleSheet(
            f"color: {COLORS['text']}; background-color: #1E293B; padding: 10px; border-radius: 6px;")
        toolbar_layout.addWidget(self.status_bar)

        main_layout.addLayout(toolbar_layout)
        self.charger_configuration_auto()

    def create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group_activation = self.create_styled_group("Activation du Système")
        activation_layout = QVBoxLayout()
        self.cb_activer_ids = QCheckBox("Activer la surveillance temps-réel")
        self.cb_activer_ids.setStyleSheet("color: white; font-size: 13px;")
        self.cb_activer_ids.setChecked(True)
        self.cb_activer_ids.toggled.connect(self.toggle_ids)
        activation_layout.addWidget(self.cb_activer_ids)
        group_activation.setLayout(activation_layout)

        group_demarrage = self.create_styled_group("Options de Boot")
        dem_layout = QVBoxLayout()
        self.cb_demarrage_auto = QCheckBox("Lancement automatique au boot")
        self.cb_redemarrage_auto = QCheckBox("Auto-restart en cas de crash")
        for cb in [self.cb_demarrage_auto, self.cb_redemarrage_auto]:
            cb.setStyleSheet("color: white; font-size: 13px;")
            cb.setChecked(True)
            dem_layout.addWidget(cb)
        group_demarrage.setLayout(dem_layout)

        layout.addWidget(group_activation)
        layout.addWidget(group_demarrage)
        layout.addStretch()
        return widget

    def create_seuils_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = self.create_styled_group("Seuils de Tolérance")
        grid = QGridLayout()

        labels = ["Max Paquets/s :", "Volume Max (MB/s) :", "Max Connexions :", "Tentatives Login :"]
        self.spin_max_paquets = QSpinBox()
        self.spin_volume_max = QSpinBox()
        self.spin_max_connexions = QSpinBox()
        self.spin_max_tentatives = QSpinBox()

        spins = [self.spin_max_paquets, self.spin_volume_max, self.spin_max_connexions, self.spin_max_tentatives]
        for i, text in enumerate(labels):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: white;")
            grid.addWidget(lbl, i, 0)
            spins[i].setStyleSheet(INPUT_STYLE)
            spins[i].setRange(1, 100000)
            grid.addWidget(spins[i], i, 1)

        group.setLayout(grid)
        layout.addWidget(group)
        layout.addStretch()
        return widget

    def create_regles_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table
        self.table_regles = QTableWidget()
        self.table_regles.setColumnCount(2)
        self.table_regles.setHorizontalHeaderLabels(["SID", "DÉFINITION DE LA RÈGLE"])
        self.table_regles.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_regles.setStyleSheet(TABLE_STYLE)
        self.table_regles.setAlternatingRowColors(True)

        # Editor
        group_edit = self.create_styled_group("⌨️ Éditeur Quick-Rule")
        edit_layout = QVBoxLayout()
        self.edit_regle = QTextEdit()
        self.edit_regle.setStyleSheet(INPUT_STYLE)
        self.edit_regle.setMaximumHeight(80)
        edit_layout.addWidget(self.edit_regle)

        btn_lay = QHBoxLayout()
        self.btn_ajouter = QPushButton("➕ Ajouter")
        self.btn_modifier = QPushButton("✏️ Modifier")
        self.btn_supprimer = QPushButton("❌ Supprimer")

        for btn in [self.btn_ajouter, self.btn_modifier, self.btn_supprimer]:
            btn.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", "#334155"))
            btn_lay.addWidget(btn)

        edit_layout.addLayout(btn_lay)
        group_edit.setLayout(edit_layout)

        layout.addWidget(self.table_regles, 70)
        layout.addWidget(group_edit, 30)

        self.btn_ajouter.clicked.connect(self.add_rules)
        self.btn_supprimer.clicked.connect(self.delete_rule)
        self.btn_modifier.clicked.connect(self.update_rule)
        self.table_regles.itemDoubleClicked.connect(self.charger_regle_pour_modification)
        return widget

    def create_securite_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = self.create_styled_group("Blacklist IP")
        vbox = QVBoxLayout()
        self.blacklist = QListWidget()
        self.blacklist.setStyleSheet(INPUT_STYLE)
        vbox.addWidget(self.blacklist)

        self.edit_nouvelle_ip = QLineEdit()
        self.edit_nouvelle_ip.setStyleSheet(INPUT_STYLE)
        self.edit_nouvelle_ip.setPlaceholderText("Ajouter une IP (ex: 192.168.1.100)")
        vbox.addWidget(self.edit_nouvelle_ip)

        btn_lay = QHBoxLayout()
        self.btn_blacklist_ajouter = QPushButton("Ajouter")
        self.btn_blacklist_supprimer = QPushButton("Supprimer")
        for b in [self.btn_blacklist_ajouter, self.btn_blacklist_supprimer]:
            b.setStyleSheet(BTN_PRIMARY_STYLE.replace("#0EA5E9", "#334155"))
            btn_lay.addWidget(b)
        vbox.addLayout(btn_lay)
        group.setLayout(vbox)

        layout.addWidget(group)
        self.btn_blacklist_ajouter.clicked.connect(lambda: self.ajouter_ip("blacklist"))
        self.btn_blacklist_supprimer.clicked.connect(lambda: self.supprimer_ip("blacklist"))
        return widget

    def create_styled_group(self, title):
        group = QGroupBox(f" {title} ")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['info']}; font-weight: bold; border: 1px solid {COLORS['accent']};
                border-radius: 8px; margin-top: 15px; padding-top: 20px; background-color: {COLORS['bg_medium']};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 15px; padding: 0 5px; }}
        """)
        return group

    # --- GARDE TOUTE TA LOGIQUE CI-DESSOUS ---
    def toggle_ids(self, etat):
        status = "ACTIF" if etat else "INACTIF"
        self.status_label.setText(f"● STATUT: {status}")
        self.status_label.setStyleSheet(
            f"color: {COLORS['success'] if etat else COLORS['danger']}; background-color: #1E293B; padding: 8px 15px; border-radius: 6px; border: 1px solid {COLORS['accent']}; font-weight: bold;")

    def load_rules(self):
        try:
            rules = afficher_db()
            self.table_regles.setRowCount(0)
            for sid, rule in rules:
                row = self.table_regles.rowCount()
                self.table_regles.insertRow(row)
                self.table_regles.setItem(row, 0, QTableWidgetItem(str(sid)))
                self.table_regles.setItem(row, 1, QTableWidgetItem(rule))
        except:
            pass

    def add_rules(self):
        rule = self.edit_regle.toPlainText()
        if rule:
            ajouter_regle(rule)
            self.load_rules()
            self.edit_regle.clear()

    def charger_regle_pour_modification(self, item):
        row = item.row()
        self.sid = int(self.table_regles.item(row, 0).text())
        self.edit_regle.setText(self.table_regles.item(row, 1).text())

    def update_rule(self):
        if hasattr(self, 'sid'):
            modifier_regle(self.sid, self.edit_regle.toPlainText())
            self.load_rules()

    def delete_rule(self):
        if hasattr(self, 'sid'):
            supprimer_regle(self.sid)
            self.load_rules()

    def ajouter_ip(self, t):
        ip = self.edit_nouvelle_ip.text().strip()
        if ip: self.blacklist.addItem(ip); self.edit_nouvelle_ip.clear()

    def supprimer_ip(self, t):
        current = self.blacklist.currentItem()
        if current: self.blacklist.takeItem(self.blacklist.row(current))

    def appliquer_configuration(self):
        QMessageBox.information(self, "Succès", "✅ Configuration poussée vers le moteur IDS avec succès.")

    def reset_configuration(self):
        if QMessageBox.question(self, "Confirmer",
                                "Réinitialiser la BDD des règles ?") == QMessageBox.StandardButton.Yes:
            reset_db()
            self.load_rules()

    def sauvegarder_configuration(self):
        config = {"date": str(datetime.now()), "rules_count": self.table_regles.rowCount()}
        path, _ = QFileDialog.getSaveFileName(self, "Sauver JSON", "config.json", "*.json")
        if path:
            with open(path, 'w') as f: json.dump(config, f)
            QMessageBox.information(self, "Ok", "Fichier config généré.")

    def charger_configuration_auto(self):
        self.status_bar.setText("✓ Configuration temps-réel synchronisée")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InterfaceParametresIDS()
    window.show()
    sys.exit(app.exec())