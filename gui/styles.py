# ============================================================
# STYLES MODULAIRES - À placer dans un fichier séparé (styles.py)
# ============================================================

# Couleurs de base
COLORS = {
    'bg_dark': '#060d1a',
    'bg_panel': '#0d1f3c',
    'bg_input': '#334155',
    'border': '#475569',
    'text': '#c8d8f0',
    'text_light': 'white',
    'info': '#0EA5E9',
    'info_hover': '#0284C7',
    'info_pressed': '#0369A1',
    'success': '#00ff9d',
    'warning': '#ff9500',
    'danger': '#ff3860',
    'accent': '#00d4ff'
}

# Style pour les inputs (version moderne)
INPUT_STYLE = f"""
    QComboBox, QDateEdit, QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_light']};
        padding: 8px 12px;
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        font-size: 13px;
        font-family: 'Segoe UI', 'Courier New', monospace;
    }}
    QComboBox:focus, QDateEdit:focus, QLineEdit:focus, QSpinBox:focus,
    QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {COLORS['info']};
        background-color: #3F51B5;
    }}
    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {COLORS['text_light']};
        width: 0;
        height: 0;
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_light']};
        selection-background-color: {COLORS['info']};
        border: 1px solid {COLORS['border']};
    }}
"""

# Style pour bouton principal (bleu moderne)
BTN_PRIMARY_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['info']};
        color: {COLORS['text_light']};
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: bold;
        border: none;
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['info_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['info_pressed']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['accent']};
        border: 1px solid {COLORS['accent']};
    }}
"""

# Style pour bouton secondaire (gris)
BTN_SECONDARY_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['bg_input']};
        color: {COLORS['text_light']};
        padding: 8px 15px;
        border-radius: 6px;
        font-weight: bold;
        border: 1px solid {COLORS['border']};
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['border']};
    }}
    QPushButton:pressed {{
        background-color: #1f2937;
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['accent']};
        border: 1px solid {COLORS['accent']};
    }}
"""

# Style pour bouton danger (rouge)
BTN_DANGER_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['danger']};
        color: {COLORS['text_light']};
        padding: 8px 15px;
        border-radius: 6px;
        font-weight: bold;
        border: none;
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: #e6002e;
    }}
    QPushButton:pressed {{
        background-color: #cc0028;
    }}
"""

# Style pour labels
LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text']};
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 12px;
        background: transparent;
    }}
"""

# Style pour les groupes (GroupBox)
GROUPBOX_STYLE = f"""
    QGroupBox {{
        color: {COLORS['accent']};
        font-weight: bold;
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
        font-family: 'Segoe UI', 'Courier New', monospace;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px;
        color: {COLORS['accent']};
    }}
"""

# Style pour les tableaux (version moderne)
TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLORS['bg_panel']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        gridline-color: {COLORS['border']};
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 11px;
        color: {COLORS['text']};
        alternate-background-color: #0a1628;
    }}
    QTableWidget::item {{
        padding: 5px 8px;
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS['accent']}30;
        color: white;
    }}
    QHeaderView::section {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['accent']};
        border: none;
        border-bottom: 1px solid {COLORS['border']};
        padding: 6px 8px;
        font-weight: bold;
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 10px;
    }}
"""

# Style pour les barres de progression (version moderne)
PROGRESS_STYLE = f"""
    QProgressBar {{
        background-color: {COLORS['bg_input']};
        border: none;
        border-radius: 4px;
        text-align: center;
        color: white;
        font-weight: bold;
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLORS['info']}, stop:1 {COLORS['success']});
        border-radius: 4px;
    }}
"""

# Style pour les scrollbars (modernes)
SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: {COLORS['bg_panel']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border']};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""

# Style pour les onglets (TabWidget)
TAB_STYLE = f"""
    QTabWidget::pane {{
        background: {COLORS['bg_panel']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
    }}
    QTabBar::tab {{
        background: {COLORS['bg_dark']};
        color: {COLORS['text']};
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-family: 'Segoe UI', 'Courier New', monospace;
    }}
    QTabBar::tab:selected {{
        background: {COLORS['bg_panel']};
        color: {COLORS['accent']};
        border-bottom: 2px solid {COLORS['accent']};
    }}
    QTabBar::tab:hover {{
        background: {COLORS['bg_input']};
    }}
"""


# ============================================================
# CLASSE UTILITAIRE POUR APPLIQUER LES STYLES
# ============================================================

class StyleManager:
    """Gestionnaire de styles pour appliquer facilement les styles à des widgets"""

    @staticmethod
    def apply_input_style(widget):
        """Applique le style input à un widget spécifique"""
        if hasattr(widget, 'setStyleSheet'):
            current = widget.styleSheet()
            widget.setStyleSheet(current + INPUT_STYLE if current else INPUT_STYLE)

    @staticmethod
    def apply_button_primary(widget):
        """Applique le style bouton primaire"""
        if hasattr(widget, 'setStyleSheet'):
            current = widget.styleSheet()
            widget.setStyleSheet(current + BTN_PRIMARY_STYLE if current else BTN_PRIMARY_STYLE)

    @staticmethod
    def apply_button_secondary(widget):
        """Applique le style bouton secondaire"""
        if hasattr(widget, 'setStyleSheet'):
            current = widget.styleSheet()
            widget.setStyleSheet(current + BTN_SECONDARY_STYLE if current else BTN_SECONDARY_STYLE)

    @staticmethod
    def apply_button_danger(widget):
        """Applique le style bouton danger"""
        if hasattr(widget, 'setStyleSheet'):
            current = widget.styleSheet()
            widget.setStyleSheet(current + BTN_DANGER_STYLE if current else BTN_DANGER_STYLE)

    @staticmethod
    def apply_table_style(widget):
        """Applique le style tableau"""
        if hasattr(widget, 'setStyleSheet'):
            current = widget.styleSheet()
            widget.setStyleSheet(current + TABLE_STYLE if current else TABLE_STYLE)


# ============================================================
# EXEMPLE D'UTILISATION DANS UNE AUTRE INTERFACE
# ============================================================

class MyOtherInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Autre Interface")

        # Appliquer le fond global (optionnel - garde le thème global)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {COLORS['bg_dark']};
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Formulaire avec des inputs stylisés
        form_layout = QFormLayout()

        # Champs avec style input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Entrez le nom")
        StyleManager.apply_input_style(self.name_input)  # Applique le style

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Type 1", "Type 2", "Type 3"])
        StyleManager.apply_input_style(self.type_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        StyleManager.apply_input_style(self.date_edit)

        self.spin_box = QSpinBox()
        self.spin_box.setRange(0, 100)
        StyleManager.apply_input_style(self.spin_box)

        form_layout.addRow("Nom:", self.name_input)
        form_layout.addRow("Type:", self.type_combo)
        form_layout.addRow("Date:", self.date_edit)
        form_layout.addRow("Valeur:", self.spin_box)

        layout.addLayout(form_layout)

        # Boutons avec différents styles
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 Enregistrer")
        StyleManager.apply_button_primary(self.save_btn)

        self.cancel_btn = QPushButton("❌ Annuler")
        StyleManager.apply_button_secondary(self.cancel_btn)

        self.delete_btn = QPushButton("🗑 Supprimer")
        StyleManager.apply_button_danger(self.delete_btn)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Tableau avec style moderne
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Type", "Date"])
        StyleManager.apply_table_style(self.table)

        layout.addWidget(self.table)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setStyleSheet(PROGRESS_STYLE)
        layout.addWidget(self.progress)


# ============================================================
# ALTERNATIVE : APPLIQUER LE STYLE À TOUTE UNE APPLICATION
# ============================================================

def apply_global_style(app):
    """Applique le style moderne à toute l'application"""
    app.setStyleSheet(f"""
        /* Style global */
        QMainWindow, QDialog, QWidget {{
            background-color: {COLORS['bg_dark']};
        }}

        /* Inputs */
        QComboBox, QDateEdit, QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {{
            background-color: {COLORS['bg_input']};
            color: {COLORS['text_light']};
            padding: 8px 12px;
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            font-size: 13px;
            font-family: 'Segoe UI', 'Courier New', monospace;
        }}

        QComboBox:focus, QDateEdit:focus, QLineEdit:focus, QSpinBox:focus {{
            border: 2px solid {COLORS['info']};
            background-color: #3F51B5;
        }}

        /* Boutons */
        QPushButton {{
            background-color: {COLORS['info']};
            color: {COLORS['text_light']};
            padding: 8px 18px;
            border-radius: 6px;
            font-weight: bold;
            border: none;
            font-family: 'Segoe UI', 'Courier New', monospace;
            font-size: 12px;
        }}

        QPushButton:hover {{
            background-color: {COLORS['info_hover']};
        }}

        QPushButton:pressed {{
            background-color: {COLORS['info_pressed']};
        }}

        QPushButton[secondary="true"] {{
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
        }}

        QPushButton[danger="true"] {{
            background-color: {COLORS['danger']};
        }}

        /* Labels */
        QLabel {{
            color: {COLORS['text']};
            font-family: 'Segoe UI', 'Courier New', monospace;
            font-size: 12px;
        }}

        /* GroupBox */
        QGroupBox {{
            color: {COLORS['accent']};
            font-weight: bold;
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px;
        }}

        /* Tables */
        QTableWidget {{
            background-color: {COLORS['bg_panel']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            gridline-color: {COLORS['border']};
            alternate-background-color: #0a1628;
        }}

        QHeaderView::section {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['accent']};
            padding: 6px 8px;
            font-weight: bold;
        }}
    """)