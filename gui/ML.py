import sys
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import matplotlib

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

import warnings

warnings.filterwarnings('ignore')

# ============================================================
# IMPORT DES STYLES DEPUIS CONFIG
# ============================================================
try:
    from config import COLORS, INPUT_STYLE, BTN_PRIMARY_STYLE, BTN_SECONDARY_STYLE
except ImportError:
    # Fallback si config n'existe pas
    COLORS = {
        'bg_dark': '#0f172a',
        'bg_medium': '#1e293b',
        'text_bright': '#f8fafc',
        'info': '#0EA5E9',
        'accent': '#06b6d4',
        'success': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b'
    }
    INPUT_STYLE = """
        QLineEdit, QComboBox, QTextEdit {
            background-color: #334155;
            color: white;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 8px;
        }
    """
    BTN_PRIMARY_STYLE = """
        QPushButton {
            background-color: #0EA5E9;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #0284C7; }
    """
    BTN_SECONDARY_STYLE = """
        QPushButton {
            background-color: #334155;
            color: white;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 8px 16px;
        }
        QPushButton:hover { background-color: #475569; }
    """

REQUIRED_FILES = {
    'model': 'lightgbm_final.pkl',
    'scaler': 'scaler.pkl',
    'encoder': 'label_encoder.pkl',
    'features': 'feature_cols.pkl',
}


# ============================================================
# WORKER
# ============================================================
class PredictionWorker(QThread):
    progress = pyqtSignal(int)
    status_msg = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, csv_path, model, scaler, encoder, features):
        super().__init__()
        self.csv_path = csv_path
        self.model = model
        self.scaler = scaler
        self.encoder = encoder
        self.features = features

    def run(self):
        try:
            self.status_msg.emit("Lecture CSV…")
            self.progress.emit(10)
            df_raw = pd.read_csv(self.csv_path)
            n_rows = len(df_raw)

            label_col = self._detect_label(df_raw)
            y_true = None
            if label_col:
                y_true = df_raw[label_col].copy()
                df_raw = df_raw.drop(columns=[label_col])

            self.status_msg.emit("Alignement features…")
            self.progress.emit(30)
            missing = [f for f in self.features if f not in df_raw.columns]
            if missing:
                raise ValueError(f"Colonnes manquantes : {missing[:5]}")
            df = df_raw[self.features].copy()
            for col in df.select_dtypes(include='object').columns:
                from sklearn.preprocessing import LabelEncoder as _LE
                df[col] = _LE().fit_transform(df[col].astype(str))
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(df.median(numeric_only=True)).fillna(0)

            self.status_msg.emit("Prédiction LightGBM…")
            self.progress.emit(55)
            X = self.scaler.transform(df.values.astype(np.float64))
            y_pred_enc = self.model.predict(X)

            if hasattr(self.model, 'predict_proba'):
                probas = self.model.predict_proba(X)
                conf_per_row = probas.max(axis=1)
                global_conf = float(conf_per_row.mean()) * 100
            else:
                conf_per_row = np.ones(len(y_pred_enc)) * 0.95
                global_conf = 95.0

            self.status_msg.emit("Décodage classes…")
            self.progress.emit(80)
            try:
                y_pred_labels = self.encoder.inverse_transform(y_pred_enc.astype(int))
            except Exception:
                y_pred_labels = y_pred_enc.astype(str)

            is_attack = np.array([
                str(l).lower() not in ('normal', '0', 'benign', 'legitimate')
                for l in y_pred_labels
            ])
            n_attacks = int(is_attack.sum())
            n_normal = n_rows - n_attacks

            accuracy = None
            if y_true is not None:
                try:
                    from sklearn.metrics import accuracy_score
                    y_t = self.encoder.transform(y_true.astype(str)) \
                        if hasattr(self.encoder, 'transform') else y_true.values
                    accuracy = accuracy_score(y_t[:len(y_pred_enc)], y_pred_enc) * 100
                except Exception:
                    pass

            attack_dist = {}
            for lbl, att in zip(y_pred_labels, is_attack):
                if att:
                    attack_dist[str(lbl)] = attack_dist.get(str(lbl), 0) + 1

            preview = df_raw[self.features].head(500).copy()
            preview.insert(0, 'Statut', ['ATTAQUE' if a else 'NORMAL' for a in is_attack[:500]])
            preview.insert(1, 'Prédiction', y_pred_labels[:500])
            preview.insert(2, 'Confiance', [f"{c * 100:.1f}%" for c in conf_per_row[:500]])

            self.progress.emit(100)
            self.result_ready.emit({
                'n_rows': n_rows,
                'n_attacks': n_attacks,
                'n_normal': n_normal,
                'global_conf': global_conf,
                'accuracy': accuracy,
                'attack_dist': attack_dist,
                'preview': preview,
            })

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    @staticmethod
    def _detect_label(df):
        for c in ['label', 'Label', 'class', 'Class', 'attack', 'Attack', 'target', 'Target']:
            if c in df.columns:
                return c
        last = df.columns[-1]
        return last if df[last].dtype == object else None


# ============================================================
# CARTE METRIQUE (STYLE UNIFIE AVEC BORDURE)
# ============================================================
class MetricCard(QWidget):
    def __init__(self, icon, title, value="—", accent=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.accent = accent or COLORS['info']
        self.setMinimumHeight(88)
        self.setMaximumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._icon = QLabel(icon)
        self._icon.setObjectName("card_icon")
        self._title = QLabel(title.upper())
        self._title.setObjectName("card_title")
        top.addWidget(self._icon)
        top.addWidget(self._title)
        top.addStretch()

        self._val = QLabel(value)
        self._val.setObjectName("card_value")
        self._val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addLayout(top)
        lay.addWidget(self._val)

    def set_value(self, v, color=None):
        self._val.setText(str(v))
        if color:
            self._val.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")


# ============================================================
# PANEL (STYLE UNIFIE)
# ============================================================
class Panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


# ============================================================
# BOUTON (STYLE UNIFIE)
# ============================================================
class CyberButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("cyber_button")


# ============================================================
# SECTION LABEL
# ============================================================
def section_label(text):
    l = QLabel(text)
    l.setObjectName("section_label")
    return l


# ============================================================
# FENETRE PRINCIPALE IDS - STYLE UNIFIE AVEC CARTES ENCADREES
# ============================================================
class IDSWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS · Network Intrusion Detection System")

        # ✅ Plein écran sans dépassement
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Application du style global
        self.setup_style()

        self._model = self._scaler = self._encoder = self._features = None
        self._csv_path = None
        self._raw_df = None
        self._worker = None

        self._build_ui()

    def setup_style(self):
        """Style global unifié - avec bordures pour les cartes"""
        self.setStyleSheet(f"""
            /* Widgets principaux */
            QMainWindow, QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_bright']};
                font-family: 'Segoe UI';
            }}

            /* Labels */
            QLabel {{
                font-size: 12px;
            }}

            QLabel#section_label {{
                color: {COLORS['info']};
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 3px;
                padding: 4px;
            }}

            /* Panel personnalisé */
            QWidget#panel {{
                background-color: {COLORS['bg_medium']};
                border-radius: 10px;
                border: 1px solid {COLORS['accent']};
            }}

            /* ✅ CARTES METRIQUES AVEC BORDURE ENCADREE */
            QWidget#card {{
                background-color: {COLORS['bg_medium']};
                border-radius: 12px;
                border: 2px solid {COLORS['accent']};
            }}

            QWidget#card:hover {{
                border: 2px solid {COLORS['info']};
                background-color: {COLORS['bg_medium']};
            }}

            QLabel#card_icon {{
                font-size: 18px;
                color: {COLORS['info']};
            }}

            QLabel#card_title {{
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 2px;
                color: {COLORS['accent']};
            }}

            QLabel#card_value {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS['text_bright']};
            }}

            /* GroupBox */
            QGroupBox {{
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                background-color: {COLORS['bg_medium']};
                margin-top: 12px;
                padding-top: 8px;
                font-weight: bold;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: {COLORS['info']};
            }}

            /* Tableaux */
            QTableWidget {{
                background-color: {COLORS['bg_medium']};
                alternate-background-color: {COLORS['bg_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                gridline-color: {COLORS['accent']};
            }}

            QTableWidget::item {{
                padding: 6px 8px;
            }}

            QTableWidget::item:selected {{
                background-color: {COLORS['info']}40;
            }}

            QHeaderView::section {{
                background-color: #0B1120;
                color: {COLORS['text_bright']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {COLORS['info']};
                font-weight: bold;
            }}

            /* ProgressBar */
            QProgressBar {{
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                background-color: {COLORS['bg_dark']};
                text-align: center;
                color: {COLORS['text_bright']};
            }}

            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['info']}, stop:1 {COLORS['success']});
                border-radius: 5px;
            }}

            /* ComboBox */
            QComboBox {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                padding: 6px 10px;
            }}

            QComboBox::drop-down {{
                border: none;
            }}

            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                selection-background-color: {COLORS['info']};
            }}

            /* LineEdit */
            QLineEdit {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                padding: 6px 10px;
            }}

            QLineEdit:focus {{
                border: 2px solid {COLORS['info']};
            }}

            /* StatusBar */
            QStatusBar {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['info']};
                border-top: 1px solid {COLORS['accent']};
            }}

            /* ScrollBar */
            QScrollBar:vertical {{
                background: {COLORS['bg_dark']};
                width: 8px;
                border-radius: 4px;
            }}

            QScrollBar::handle:vertical {{
                background: {COLORS['accent']};
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            /* INPUT STYLE */
            {INPUT_STYLE}

            /* BOUTONS */
            QPushButton#cyber_button {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['info']};
                border: 1px solid {COLORS['info']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}

            QPushButton#cyber_button:hover {{
                background-color: {COLORS['info']}20;
            }}

            QPushButton#cyber_button:disabled {{
                color: {COLORS['accent']}80;
                border-color: {COLORS['accent']}80;
            }}

            {BTN_PRIMARY_STYLE}
            {BTN_SECONDARY_STYLE}
        """)

    def _build_ui(self):
        root_w = QWidget(self)
        root_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(root_w)

        root = QVBoxLayout(root_w)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header avec taille fixe
        header = self._make_header()
        header.setFixedHeight(62)
        root.addWidget(header)

        # Toolbar avec taille fixe
        toolbar = self._make_toolbar()
        toolbar.setFixedHeight(54)
        root.addWidget(toolbar)

        # Corps avec expansion complète
        body_w = QWidget()
        body = QHBoxLayout(body_w)
        body.setSpacing(12)
        body.setContentsMargins(14, 10, 14, 10)

        left_panel = self._make_left_panel()
        right_panel = self._make_right_panel()

        body.addWidget(left_panel, 30)
        body.addWidget(right_panel, 70)
        root.addWidget(body_w, 1)

        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._sb.showMessage("◉  SYSTÈME PRÊT  ·  Chargez le dossier modèle puis un fichier CSV")

        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    # ── Header ────────────────────────────────────────────────────────
    def _make_header(self):
        w = Panel()
        w.setFixedHeight(62)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(12)

        logo = QLabel("🛡️")
        logo.setStyleSheet(f"font-size: 26px; color: {COLORS['info']};")

        col = QVBoxLayout()
        col.setSpacing(1)
        t1 = QLabel("NETWORK IDS")
        t1.setStyleSheet("font-size: 17px; font-weight: bold; letter-spacing: 3px;")
        t2 = QLabel("LightGBM · Intrusion Detection System")
        t2.setStyleSheet(f"color: {COLORS['info']}; font-size: 9px; letter-spacing: 2px;")
        col.addWidget(t1)
        col.addWidget(t2)

        lay.addWidget(logo)
        lay.addLayout(col)
        lay.addStretch()

        # Indicateurs pkl
        self._inds = {}
        ind_panel = Panel()
        ind_panel.setFixedHeight(42)
        ind_lay = QHBoxLayout(ind_panel)
        ind_lay.setContentsMargins(14, 4, 14, 4)
        ind_lay.setSpacing(16)

        for key, fname in REQUIRED_FILES.items():
            short = (fname.replace('lightgbm_final', 'lgbm')
                     .replace('feature_cols', 'features')
                     .replace('label_encoder', 'encoder')
                     .replace('.pkl', ''))
            vc = QVBoxLayout()
            vc.setSpacing(0)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(short)
            lbl.setStyleSheet("font-size: 8px; letter-spacing: 1px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vc.addWidget(dot)
            vc.addWidget(lbl)
            self._inds[key] = dot
            ind_lay.addLayout(vc)

        lay.addWidget(ind_panel)
        lay.addSpacing(14)

        self._time_lbl = QLabel()
        self._time_lbl.setStyleSheet(f"color: {COLORS['info']}; font-size: 11px;")
        lay.addWidget(self._time_lbl)

        return w

    # ── Toolbar ───────────────────────────────────────────────────────
    def _make_toolbar(self):
        w = Panel()
        w.setFixedHeight(54)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        self._btn_dir = CyberButton("📁  MODÈLE")
        self._btn_dir.clicked.connect(self._load_model_dir)

        self._dir_lbl = QLabel("Aucun dossier")
        self._dir_lbl.setStyleSheet("font-size: 10px;")
        self._dir_lbl.setMaximumWidth(240)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setFixedWidth(1)
        div1.setStyleSheet(f"background: {COLORS['accent']};")

        self._btn_csv = CyberButton("📂  CSV")
        self._btn_csv.clicked.connect(self._browse_csv)

        self._csv_lbl = QLabel("Aucun fichier")
        self._csv_lbl.setStyleSheet("font-size: 10px;")
        self._csv_lbl.setMaximumWidth(240)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setFixedWidth(1)
        div2.setStyleSheet(f"background: {COLORS['accent']};")

        self._run_btn = CyberButton("▶  ANALYSER")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._run)

        self._prog_lbl = QLabel("—")
        self._prog_lbl.setStyleSheet(f"color: {COLORS['info']}; font-size: 9px;")
        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedWidth(140)
        self._prog.setFixedHeight(5)
        self._prog.setTextVisible(False)

        pc = QVBoxLayout()
        pc.setSpacing(2)
        pc.addWidget(self._prog_lbl)
        pc.addWidget(self._prog)

        lay.addWidget(self._btn_dir)
        lay.addWidget(self._dir_lbl)
        lay.addWidget(div1)
        lay.addWidget(self._btn_csv)
        lay.addWidget(self._csv_lbl)
        lay.addWidget(div2)
        lay.addStretch()
        lay.addLayout(pc)
        lay.addWidget(self._run_btn)

        return w

    # ── Panneau gauche ────────────────────────────────────────────────
    def _make_left_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(0, 0, 0, 0)

        # Carte confiance
        conf_panel = Panel()
        cl = QVBoxLayout(conf_panel)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)
        cl.addWidget(section_label("◈  CONFIANCE GLOBALE"))

        self._conf_val = QLabel("—")
        self._conf_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._conf_val.setStyleSheet("font-size: 52px; font-weight: bold;")

        self._conf_bar = QProgressBar()
        self._conf_bar.setRange(0, 100)
        self._conf_bar.setValue(0)
        self._conf_bar.setFixedHeight(7)
        self._conf_bar.setTextVisible(False)

        self._badge = QLabel("◉  EN ATTENTE")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet("font-size: 10px; letter-spacing: 2px;")

        cl.addWidget(self._conf_val)
        cl.addWidget(self._conf_bar)
        cl.addWidget(self._badge)
        lay.addWidget(conf_panel)

        # Grille métriques - AVEC BORDURES
        self._cards = {}
        grid = QGridLayout()
        grid.setSpacing(8)

        metrics = [
            ("total", "📊", "PAQUETS", COLORS['info']),
            ("attacks", "⚠️", "ATTAQUES", COLORS['danger']),
            ("normal", "✓", "NORMAL", COLORS['success']),
            ("accuracy", "🎯", "PRÉCISION", COLORS['warning'])
        ]

        for i, (key, icon, title, color) in enumerate(metrics):
            c = MetricCard(icon, title, "—", color)
            self._cards[key] = c
            grid.addWidget(c, i // 2, i % 2)

        lay.addLayout(grid)

        # Distribution
        dist_panel = Panel()
        dl = QVBoxLayout(dist_panel)
        dl.setContentsMargins(14, 10, 14, 6)
        dl.setSpacing(6)
        dl.addWidget(section_label("◈  DISTRIBUTION"))

        self._dist_fig = Figure(figsize=(3, 2.2), dpi=90)
        self._dist_fig.patch.set_facecolor(COLORS['bg_medium'])
        self._dist_canvas = FigureCanvas(self._dist_fig)
        dl.addWidget(self._dist_canvas)
        lay.addWidget(dist_panel, 1)

        # Boutons
        br = QHBoxLayout()
        br.setSpacing(8)
        rst = CyberButton("↺  RESET")
        rst.clicked.connect(self._reset)
        self._exp_btn = CyberButton("↓  EXPORTER")
        self._exp_btn.clicked.connect(self._export)
        self._exp_btn.setEnabled(False)
        br.addWidget(rst)
        br.addWidget(self._exp_btn)
        lay.addLayout(br)

        return w

    # ── Panneau droit ─────────────────────────────────────────────────
    def _make_right_panel(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        hdr.addWidget(section_label("◈  JOURNAL DES CONNEXIONS"))
        hdr.addStretch()

        self._filter = QComboBox()
        self._filter.addItems(["TOUS", "ATTAQUES", "NORMAL"])
        self._filter.setFixedWidth(110)
        self._filter.currentIndexChanged.connect(self._apply_filter)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Rechercher…")
        self._search.setFixedWidth(190)
        self._search.textChanged.connect(self._apply_filter)

        hdr.addWidget(self._filter)
        hdr.addWidget(self._search)
        lay.addLayout(hdr)

        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(26)
        lay.addWidget(self._table, 1)

        return w

    # ══════════════════════════════════════════════════════════════════
    # LOGIQUE (INCHANGÉE)
    # ══════════════════════════════════════════════════════════════════
    def _load_model_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier du modèle")
        if not d:
            return
        path = Path(d)
        loaded = {}
        all_ok = True

        for key, fname in REQUIRED_FILES.items():
            fp = path / fname
            dot = self._inds[key]
            if fp.exists():
                try:
                    with open(fp, 'rb') as f:
                        loaded[key] = pickle.load(f)
                    dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
                except Exception:
                    dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                    all_ok = False
            else:
                dot.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
                all_ok = False

        if not all_ok:
            QMessageBox.warning(self, "Fichiers manquants",
                                "Un ou plusieurs fichiers .pkl introuvables.")
            return

        self._model = loaded['model']
        self._scaler = loaded['scaler']
        self._encoder = loaded['encoder']
        self._features = loaded['features']

        s = str(path)
        self._dir_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._dir_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")
        self._sb.showMessage(f"◉  MODÈLE CHARGÉ  ·  {len(self._features)} features")
        self._check_ready()

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fichier CSV", "", "CSV (*.csv);;Tous (*)")
        if not path:
            return
        self._csv_path = path
        s = path
        self._csv_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._csv_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")
        self._check_ready()

    def _check_ready(self):
        self._run_btn.setEnabled(self._model is not None and self._csv_path is not None)

    def _run(self):
        self._run_btn.setEnabled(False)
        self._prog.setValue(0)
        self._worker = PredictionWorker(
            self._csv_path, self._model, self._scaler, self._encoder, self._features)
        self._worker.progress.connect(self._prog.setValue)
        self._worker.status_msg.connect(lambda m: (
            self._prog_lbl.setText(m), self._sb.showMessage(f"◉  {m}")))
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, res):
        self._run_btn.setEnabled(True)
        self._exp_btn.setEnabled(True)
        self._prog_lbl.setText("TERMINÉ ✓")
        self._raw_df = res['preview']

        n = res['n_rows']
        att = res['n_attacks']
        nor = res['n_normal']
        gc = res['global_conf']
        pct = att / n * 100 if n else 0
        acc = res['accuracy']

        # Confiance
        self._conf_bar.setValue(int(gc))
        self._conf_val.setText(f"{gc:.1f}%")

        if gc >= 90:
            clr = COLORS['success']
        elif gc >= 70:
            clr = COLORS['warning']
        else:
            clr = COLORS['danger']
        self._conf_val.setStyleSheet(f"color: {clr}; font-size: 52px; font-weight: bold;")

        if pct > 30:
            badge, bclr = "⚠  CRITIQUE — MENACES DÉTECTÉES", COLORS['danger']
        elif pct > 5:
            badge, bclr = "◉  SUSPECT — SURVEILLER", COLORS['warning']
        else:
            badge, bclr = "✓  RÉSEAU SÉCURISÉ", COLORS['success']

        self._badge.setText(badge)
        self._badge.setStyleSheet(f"color: {bclr}; font-size: 10px; letter-spacing: 2px;")

        self._cards["total"].set_value(f"{n:,}", COLORS['info'])
        self._cards["attacks"].set_value(f"{att:,} ({pct:.1f}%)", COLORS['danger'] if att > 0 else COLORS['success'])
        self._cards["normal"].set_value(f"{nor:,} ({100 - pct:.1f}%)", COLORS['success'])
        self._cards["accuracy"].set_value(f"{acc:.1f}%" if acc else "N/A", COLORS['warning'])

        self._populate_table(self._raw_df)
        self._draw_dist(res['attack_dist'], nor, att)
        self._sb.showMessage(
            f"◉  ANALYSE COMPLÈTE  ·  {n:,} paquets  ·  {att:,} attaques ({pct:.1f}%)  ·  {badge}")

    def _on_error(self, msg):
        self._run_btn.setEnabled(True)
        self._prog_lbl.setText("ERREUR ✗")
        QMessageBox.critical(self, "Erreur d'analyse", msg[:800])

    def _populate_table(self, df):
        if df is None or df.empty:
            return
        fixed = ['Statut', 'Prédiction', 'Confiance']
        feat = [c for c in df.columns if c not in fixed][:14]
        cols = fixed + feat
        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels([c.upper() for c in cols])
        self._table.setRowCount(len(df))

        for ri, (_, row) in enumerate(df.iterrows()):
            is_att = str(row.get('Statut', '')) == 'ATTAQUE'
            for ci, col in enumerate(cols):
                val = str(row.get(col, ''))[:32]
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                if col == 'Statut':
                    item.setText("⚠ ATTAQUE" if is_att else "✓ NORMAL")
                    item.setForeground(QColor(COLORS['danger'] if is_att else COLORS['success']))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                elif col == 'Prédiction':
                    item.setForeground(QColor(COLORS['danger'] if is_att else COLORS['success']))
                elif col == 'Confiance':
                    item.setForeground(QColor(COLORS['warning']))
                else:
                    item.setForeground(QColor(COLORS['text_bright']))

                if is_att:
                    item.setBackground(QColor(COLORS['danger'] + '20'))
                self._table.setItem(ri, ci, item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)

    def _apply_filter(self):
        if self._raw_df is None:
            return
        df = self._raw_df.copy()
        mode = self._filter.currentText()
        if mode == "ATTAQUES":
            df = df[df['Statut'] == 'ATTAQUE']
        elif mode == "NORMAL":
            df = df[df['Statut'] == 'NORMAL']
        s = self._search.text().lower()
        if s:
            df = df[df.apply(lambda r: any(s in str(v).lower() for v in r), axis=1)]
        self._populate_table(df)

    def _draw_dist(self, attack_dist, n_normal, n_attacks):
        self._dist_fig.clear()
        self._dist_fig.patch.set_facecolor(COLORS['bg_medium'])
        ax = self._dist_fig.add_subplot(111)
        ax.set_facecolor(COLORS['bg_medium'])

        labels, values, colors = [], [], []
        if n_normal:
            labels.append("Normal")
            values.append(n_normal)
            colors.append(COLORS['success'])

        palette = [COLORS['danger'], COLORS['warning'], '#8b5cf6', '#ec4899', '#14b8a6']
        for i, (k, v) in enumerate(sorted(attack_dist.items(), key=lambda x: -x[1])):
            labels.append(k[:15])
            values.append(v)
            colors.append(palette[i % len(palette)])

        if values:
            wedges, texts, autos = ax.pie(
                values, colors=colors, autopct='%1.0f%%',
                startangle=90, pctdistance=0.72,
                wedgeprops=dict(edgecolor=COLORS['bg_dark'], linewidth=2, width=0.55),
                textprops=dict(color=COLORS['text_bright'], fontsize=8))
            for a in autos:
                a.set_fontweight('bold')

            patches = [mpatches.Patch(color=c, label=l) for c, l in zip(colors, labels)]
            ax.legend(handles=patches, loc='lower center',
                      bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False,
                      prop={'size': 7}, labelcolor=COLORS['text_bright'])

        self._dist_fig.tight_layout(pad=0.2)
        self._dist_canvas.draw()

    def _export(self):
        if self._raw_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer", "resultats_ids.csv", "CSV (*.csv)")
        if path:
            self._raw_df.to_csv(path, index=False)
            QMessageBox.information(self, "Export", f"Enregistré :\n{path}")

    def _reset(self):
        self._csv_path = self._raw_df = None
        self._table.clear()
        self._table.setRowCount(0)
        self._dist_fig.clear()
        self._dist_canvas.draw()
        self._conf_val.setText("—")
        self._conf_val.setStyleSheet(f"color: {COLORS['info']}; font-size: 52px; font-weight: bold;")
        self._conf_bar.setValue(0)
        self._badge.setText("◉  EN ATTENTE")
        self._badge.setStyleSheet("font-size: 10px; letter-spacing: 2px;")
        self._prog.setValue(0)
        self._prog_lbl.setText("—")
        self._csv_lbl.setText("Aucun fichier")
        self._csv_lbl.setStyleSheet("font-size: 10px;")
        for c in self._cards.values():
            c.set_value("—")
        self._run_btn.setEnabled(False)
        self._exp_btn.setEnabled(False)
        self._sb.showMessage("◉  RÉINITIALISÉ")

    def _tick(self):
        self._time_lbl.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))


# ══════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = IDSWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()