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

REQUIRED_FILES = {
    'model'   : 'lightgbm_final.pkl',
    'scaler'  : 'scaler.pkl',
    'encoder' : 'label_encoder.pkl',
    'features': 'feature_cols.pkl',
}

# Palette
BG      = "#060d1a"
PANEL   = "#0d1f3c"
PANEL2  = "#0a1628"
BORDER  = "#1a3a5c"
CYAN    = "#00d4ff"
GREEN   = "#00ff9d"
RED     = "#ff3860"
ORANGE  = "#ff9500"
TEXT    = "#c8d8f0"
MUTED   = "#445566"


# ══════════════════════════════════════════════════════════════════════
#  Worker
# ══════════════════════════════════════════════════════════════════════
class PredictionWorker(QThread):
    progress     = pyqtSignal(int)
    status_msg   = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error        = pyqtSignal(str)

    def __init__(self, csv_path, model, scaler, encoder, features):
        super().__init__()
        self.csv_path = csv_path
        self.model    = model
        self.scaler   = scaler
        self.encoder  = encoder
        self.features = features

    def run(self):
        try:
            self.status_msg.emit("Lecture CSV…"); self.progress.emit(10)
            df_raw = pd.read_csv(self.csv_path)
            n_rows = len(df_raw)

            label_col = self._detect_label(df_raw)
            y_true = None
            if label_col:
                y_true = df_raw[label_col].copy()
                df_raw = df_raw.drop(columns=[label_col])

            self.status_msg.emit("Alignement features…"); self.progress.emit(30)
            missing = [f for f in self.features if f not in df_raw.columns]
            if missing:
                raise ValueError(f"Colonnes manquantes : {missing[:5]}")
            df = df_raw[self.features].copy()
            for col in df.select_dtypes(include='object').columns:
                from sklearn.preprocessing import LabelEncoder as _LE
                df[col] = _LE().fit_transform(df[col].astype(str))
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(df.median(numeric_only=True)).fillna(0)

            self.status_msg.emit("Prédiction LightGBM…");
            self.progress.emit(55)
            X = self.scaler.transform(df.values.astype(np.float64))
            y_pred_enc = self.model.predict(X)

            if hasattr(self.model, 'predict_proba'):
                probas       = self.model.predict_proba(X)
                conf_per_row = probas.max(axis=1)
                global_conf  = float(conf_per_row.mean()) * 100
            else:
                conf_per_row = np.ones(len(y_pred_enc)) * 0.95
                global_conf  = 95.0

            self.status_msg.emit("Décodage classes…"); self.progress.emit(80)
            try:
                y_pred_labels = self.encoder.inverse_transform(y_pred_enc.astype(int))
            except Exception:
                y_pred_labels = y_pred_enc.astype(str)

            is_attack = np.array([
                str(l).lower() not in ('normal', '0', 'benign', 'legitimate')
                for l in y_pred_labels])
            n_attacks = int(is_attack.sum())
            n_normal  = n_rows - n_attacks

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
            preview.insert(0, 'Statut',     ['ATTAQUE' if a else 'NORMAL' for a in is_attack[:500]])
            preview.insert(1, 'Prédiction', y_pred_labels[:500])
            preview.insert(2, 'Confiance',  [f"{c*100:.1f}%" for c in conf_per_row[:500]])

            self.progress.emit(100)
            self.result_ready.emit({
                'n_rows': n_rows, 'n_attacks': n_attacks, 'n_normal': n_normal,
                'global_conf': global_conf, 'accuracy': accuracy,
                'attack_dist': attack_dist, 'preview': preview,
            })

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    @staticmethod
    def _detect_label(df):
        for c in ['label','Label','class','Class','attack','Attack','target','Target']:
            if c in df.columns:
                return c
        last = df.columns[-1]
        return last if df[last].dtype == object else None


# ══════════════════════════════════════════════════════════════════════
#  Carte métrique (dessin custom, zéro héritage de style global)
# ══════════════════════════════════════════════════════════════════════
class MetricCard(QWidget):
    def __init__(self, icon, title, value="—", accent=CYAN, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setMinimumHeight(88)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(3)

        top = QHBoxLayout(); top.setSpacing(6)
        self._icon = QLabel(icon)
        self._icon.setStyleSheet(f"color:{accent}; font-size:16px; background:transparent;")
        self._title = QLabel(title.upper())
        self._title.setStyleSheet(
            f"color:{accent}; font-size:8px; font-weight:bold; "
            f"letter-spacing:2px; font-family:'Courier New',monospace; background:transparent;")
        top.addWidget(self._icon); top.addWidget(self._title); top.addStretch()

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:white; font-size:24px; font-weight:bold; "
            f"font-family:'Courier New',monospace; background:transparent;")

        lay.addLayout(top)
        lay.addWidget(self._val)

    def set_value(self, v, color=None):
        self._val.setText(str(v))
        c = color or "white"
        self._val.setStyleSheet(
            f"color:{c}; font-size:24px; font-weight:bold; "
            f"font-family:'Courier New',monospace; background:transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        # Fond dégradé
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor(18, 32, 58))
        g.setColorAt(1, QColor(10, 18, 38))
        p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 8, 8)

        # Bordure accent gauche
        ac = QColor(self.accent)
        p.setBrush(QBrush(ac)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r.x(), r.y() + 12, 3, r.height() - 24, 2, 2)

        # Bordure extérieure
        p.setBrush(Qt.BrushStyle.NoBrush)
        ac.setAlpha(60); p.setPen(QPen(ac, 1))
        p.drawRoundedRect(r, 8, 8)


# ══════════════════════════════════════════════════════════════════════
#  Bouton cyberpunk
# ══════════════════════════════════════════════════════════════════════
class CyberButton(QPushButton):
    def __init__(self, text, accent=CYAN, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {accent};
                border: 1px solid {accent};
                border-radius: 5px;
                padding: 7px 18px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover  {{ background: {accent}20; }}
            QPushButton:pressed{{ background: {accent}40; }}
            QPushButton:disabled {{ color:#334455; border-color:#223; }}
        """)


# ══════════════════════════════════════════════════════════════════════
#  Widget section titre (transparent)
# ══════════════════════════════════════════════════════════════════════
def section_label(text, color=CYAN):
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color}; font-size:9px; font-weight:bold; "
        f"letter-spacing:3px; font-family:'Courier New',monospace; "
        f"background:transparent; padding:0px;")
    return l


# ══════════════════════════════════════════════════════════════════════
#  Panneau coloré (remplace QGroupBox)
# ══════════════════════════════════════════════════════════════════════
class Panel(QWidget):
    def __init__(self, bg=PANEL, border=BORDER, radius=10, parent=None):
        super().__init__(parent)
        self.bg = bg; self.border = border; self.radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor(self.bg))
        g.setColorAt(1, QColor(self.bg).darker(120))
        p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, self.radius, self.radius)
        bc = QColor(self.border); bc.setAlpha(120)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(bc, 1))
        p.drawRoundedRect(r, self.radius, self.radius)


# ══════════════════════════════════════════════════════════════════════
#  Fenêtre principale
# ══════════════════════════════════════════════════════════════════════
class IDSWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS · Network Intrusion Detection System")
        sz = QApplication.primaryScreen().size()
        self.setGeometry(0, 0, sz.width(), sz.height())

        self._model = self._scaler = self._encoder = self._features = None
        self._csv_path = None
        self._raw_df   = None
        self._worker   = None

        # Fond principal
        self.setStyleSheet(f"QMainWindow {{ background:{BG}; }}")

        self._build_ui()

    def _build_ui(self):
        root_w = QWidget(self)
        root_w.setStyleSheet(f"background:{BG};")
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setSpacing(0); root.setContentsMargins(0, 0, 0, 0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_toolbar())

        body_w = QWidget(); body_w.setStyleSheet(f"background:{BG};")
        body = QHBoxLayout(body_w)
        body.setSpacing(12); body.setContentsMargins(14, 10, 14, 10)
        body.addWidget(self._make_left_panel(), 26)
        body.addWidget(self._make_right_panel(), 74)
        root.addWidget(body_w, 1)

        self._sb = QStatusBar(); self.setStatusBar(self._sb)
        self._sb.setStyleSheet(
            f"QStatusBar {{ background:{PANEL2}; color:{CYAN}; "
            f"font-family:'Courier New',monospace; font-size:10px; "
            f"border-top:1px solid {BORDER}; }}")
        self._sb.showMessage("◉  SYSTÈME PRÊT  ·  Chargez le dossier modèle puis un fichier CSV")

        t = QTimer(self); t.timeout.connect(self._tick); t.start(1000)
        self._tick()

    # ── Header ────────────────────────────────────────────────────────
    def _make_header(self):
        w = Panel(bg="#0a1628", border=BORDER, radius=0)
        w.setFixedHeight(62)
        lay = QHBoxLayout(w); lay.setContentsMargins(18, 0, 18, 0); lay.setSpacing(12)

        logo = QLabel("⬡")
        logo.setStyleSheet(f"color:{CYAN}; font-size:26px; background:transparent;")

        col = QVBoxLayout(); col.setSpacing(1)
        t1 = QLabel("NETWORK IDS")
        t1.setStyleSheet(
            f"color:white; font-size:17px; font-weight:bold; "
            f"font-family:'Courier New',monospace; letter-spacing:3px; background:transparent;")
        t2 = QLabel("LightGBM · Intrusion Detection System")
        t2.setStyleSheet(
            f"color:{CYAN}; font-size:9px; letter-spacing:2px; "
            f"font-family:'Courier New',monospace; background:transparent;")
        col.addWidget(t1); col.addWidget(t2)

        lay.addWidget(logo); lay.addLayout(col); lay.addStretch()

        # Indicateurs pkl
        self._inds = {}
        ind_panel = Panel(bg=PANEL2, border=BORDER, radius=6)
        ind_panel.setFixedHeight(42)
        ind_lay = QHBoxLayout(ind_panel)
        ind_lay.setContentsMargins(14, 4, 14, 4); ind_lay.setSpacing(16)
        for key, fname in REQUIRED_FILES.items():
            short = (fname.replace('lightgbm_final','lgbm')
                     .replace('feature_cols','features')
                     .replace('label_encoder','encoder')
                     .replace('.pkl',''))
            vc = QVBoxLayout(); vc.setSpacing(0)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{RED}; font-size:12px; background:transparent;")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(short)
            lbl.setStyleSheet(f"color:{MUTED}; font-size:8px; letter-spacing:1px; "
                              f"font-family:'Courier New',monospace; background:transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vc.addWidget(dot); vc.addWidget(lbl)
            self._inds[key] = dot
            ind_lay.addLayout(vc)
        lay.addWidget(ind_panel)

        lay.addSpacing(14)
        self._time_lbl = QLabel()
        self._time_lbl.setStyleSheet(
            f"color:{CYAN}; font-size:11px; font-family:'Courier New',monospace; background:transparent;")
        lay.addWidget(self._time_lbl)
        return w

    # ── Toolbar ───────────────────────────────────────────────────────
    def _make_toolbar(self):
        w = Panel(bg=PANEL2, border=BORDER, radius=0)
        w.setFixedHeight(54)
        lay = QHBoxLayout(w); lay.setContentsMargins(14, 0, 14, 0); lay.setSpacing(10)

        self._btn_dir = CyberButton("📁  MODÈLE", CYAN)
        self._btn_dir.clicked.connect(self._load_model_dir)

        self._dir_lbl = QLabel("Aucun dossier")
        self._dir_lbl.setStyleSheet(
            f"color:{MUTED}; font-size:10px; font-family:'Courier New',monospace; background:transparent;")
        self._dir_lbl.setMaximumWidth(240)

        div1 = QFrame(); div1.setFrameShape(QFrame.Shape.VLine)
        div1.setFixedWidth(1); div1.setStyleSheet(f"background:{BORDER};")

        self._btn_csv = CyberButton("📂  CSV", GREEN)
        self._btn_csv.clicked.connect(self._browse_csv)

        self._csv_lbl = QLabel("Aucun fichier")
        self._csv_lbl.setStyleSheet(
            f"color:{MUTED}; font-size:10px; font-family:'Courier New',monospace; background:transparent;")
        self._csv_lbl.setMaximumWidth(240)

        div2 = QFrame(); div2.setFrameShape(QFrame.Shape.VLine)
        div2.setFixedWidth(1); div2.setStyleSheet(f"background:{BORDER};")

        self._run_btn = CyberButton("▶  ANALYSER", GREEN)
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._run)
        self._run_btn.setStyleSheet(self._run_btn.styleSheet().replace(
            "font-size: 11px", "font-size: 12px"))

        self._prog_lbl = QLabel("—")
        self._prog_lbl.setStyleSheet(
            f"color:{CYAN}; font-size:9px; font-family:'Courier New',monospace; background:transparent;")
        self._prog = QProgressBar()
        self._prog.setRange(0, 100); self._prog.setValue(0)
        self._prog.setFixedWidth(140); self._prog.setFixedHeight(5)
        self._prog.setTextVisible(False)
        self._prog.setStyleSheet(f"""
            QProgressBar {{ background:{PANEL}; border:1px solid {BORDER};
                           border-radius:2px; }}
            QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {CYAN}, stop:1 {GREEN}); border-radius:2px; }}
        """)
        pc = QVBoxLayout(); pc.setSpacing(2)
        pc.addWidget(self._prog_lbl); pc.addWidget(self._prog)

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
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setSpacing(10); lay.setContentsMargins(0, 0, 0, 0)

        # Carte confiance
        conf_panel = Panel(bg="#0b1c38", border=BORDER, radius=10)
        cl = QVBoxLayout(conf_panel); cl.setContentsMargins(18, 14, 18, 14); cl.setSpacing(6)
        cl.addWidget(section_label("◈  CONFIANCE GLOBALE"))
        self._conf_val = QLabel("—")
        self._conf_val.setStyleSheet(
            f"color:{CYAN}; font-size:58px; font-weight:bold; "
            f"font-family:'Courier New',monospace; background:transparent;")
        self._conf_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._conf_bar = QProgressBar()
        self._conf_bar.setRange(0, 100); self._conf_bar.setValue(0)
        self._conf_bar.setFixedHeight(7); self._conf_bar.setTextVisible(False)
        self._conf_bar.setStyleSheet(f"""
            QProgressBar {{ background:{PANEL}; border:none; border-radius:3px; }}
            QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {CYAN}, stop:1 {GREEN}); border-radius:3px; }}
        """)
        self._badge = QLabel("◉  EN ATTENTE")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            f"color:{MUTED}; font-size:10px; letter-spacing:2px; "
            f"font-family:'Courier New',monospace; background:transparent;")
        cl.addWidget(self._conf_val)
        cl.addWidget(self._conf_bar)
        cl.addWidget(self._badge)
        lay.addWidget(conf_panel)

        # Grille métriques
        self._cards = {}
        grid = QGridLayout(); grid.setSpacing(8)
        for i, (key, icon, title, acc) in enumerate([
                ("total",    "⬡", "Paquets",   CYAN),
                ("attacks",  "⚠", "Attaques",   RED),
                ("normal",   "✓", "Normal",     GREEN),
                ("accuracy", "◎", "Précision",  ORANGE)]):
            c = MetricCard(icon, title, "—", acc)
            self._cards[key] = c
            grid.addWidget(c, i // 2, i % 2)
        lay.addLayout(grid)

        # Distribution
        dist_panel = Panel(bg=PANEL, border=BORDER, radius=10)
        dl = QVBoxLayout(dist_panel); dl.setContentsMargins(14, 10, 14, 6); dl.setSpacing(6)
        dl.addWidget(section_label("◈  DISTRIBUTION"))
        self._dist_fig = Figure(figsize=(3, 2.2), facecolor=PANEL, dpi=90)
        self._dist_canvas = FigureCanvas(self._dist_fig)
        self._dist_canvas.setStyleSheet(f"background:{PANEL};")
        dl.addWidget(self._dist_canvas)
        lay.addWidget(dist_panel)

        # Boutons
        br = QHBoxLayout(); br.setSpacing(8)
        rst = CyberButton("↺  RESET", CYAN); rst.clicked.connect(self._reset)
        self._exp_btn = CyberButton("↓  EXPORTER", GREEN)
        self._exp_btn.clicked.connect(self._export)
        self._exp_btn.setEnabled(False)
        br.addWidget(rst); br.addWidget(self._exp_btn)
        lay.addLayout(br)
        return w

    # ── Panneau droit ─────────────────────────────────────────────────
    def _make_right_panel(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setSpacing(8); lay.setContentsMargins(0, 0, 0, 0)

        hdr = QHBoxLayout()
        hdr.addWidget(section_label("◈  JOURNAL DES CONNEXIONS"))
        hdr.addStretch()

        self._filter = QComboBox()
        self._filter.addItems(["TOUS", "ATTAQUES", "NORMAL"])
        self._filter.setFixedWidth(110)
        self._filter.setStyleSheet(f"""
            QComboBox {{ background:{PANEL}; color:{TEXT}; border:1px solid {BORDER};
                         border-radius:5px; padding:4px 8px;
                         font-family:'Courier New',monospace; font-size:10px; }}
            QComboBox QAbstractItemView {{ background:{PANEL}; color:{TEXT};
                border:1px solid {BORDER};
                selection-background-color:{CYAN}30; }}
        """)
        self._filter.currentIndexChanged.connect(self._apply_filter)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Rechercher…")
        self._search.setFixedWidth(190)
        self._search.setStyleSheet(f"""
            QLineEdit {{ background:{PANEL}; color:{TEXT};
                        border:1px solid {BORDER}; border-radius:5px;
                        padding:4px 8px; font-family:'Courier New',monospace; font-size:10px; }}
            QLineEdit:focus {{ border-color:{CYAN}; }}
        """)
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
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background:{PANEL}; border:1px solid {BORDER}; border-radius:8px;
                gridline-color:{BORDER}; font-family:'Courier New',monospace;
                font-size:10px; color:{TEXT}; alternate-background-color:{PANEL2};
                outline:none;
            }}
            QTableWidget::item {{ padding:3px 8px; border:none; }}
            QTableWidget::item:selected {{ background:{CYAN}20; color:white; }}
            QHeaderView::section {{
                background:{PANEL2}; color:{CYAN}; border:none;
                border-bottom:1px solid {BORDER}; border-right:1px solid {BORDER};
                padding:5px 8px; font-family:'Courier New',monospace;
                font-size:9px; font-weight:bold; letter-spacing:1px;
            }}
            QScrollBar:vertical {{ background:{PANEL2}; width:5px; border-radius:2px; }}
            QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:2px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
        """)
        lay.addWidget(self._table)
        return w

    # ══════════════════════════════════════════════════════════════════
    #  Logique
    # ══════════════════════════════════════════════════════════════════
    def _load_model_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier du modèle")
        if not d:
            return
        path = Path(d); loaded = {}; all_ok = True
        for key, fname in REQUIRED_FILES.items():
            fp = path / fname; dot = self._inds[key]
            if fp.exists():
                try:
                    with open(fp, 'rb') as f:
                        loaded[key] = pickle.load(f)
                    dot.setStyleSheet(f"color:{GREEN}; font-size:12px; background:transparent;")
                except Exception:
                    dot.setStyleSheet(f"color:{RED}; font-size:12px; background:transparent;")
                    all_ok = False
            else:
                dot.setStyleSheet(f"color:{RED}; font-size:12px; background:transparent;")
                all_ok = False

        if not all_ok:
            QMessageBox.warning(self, "Fichiers manquants",
                "Un ou plusieurs fichiers .pkl introuvables.")
            return

        self._model    = loaded['model']
        self._scaler   = loaded['scaler']
        self._encoder  = loaded['encoder']
        self._features = loaded['features']
        s = str(path)
        self._dir_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._dir_lbl.setStyleSheet(
            f"color:{GREEN}; font-size:10px; font-family:'Courier New',monospace; background:transparent;")
        self._sb.showMessage(f"◉  MODÈLE CHARGÉ  ·  {len(self._features)} features")
        self._check_ready()

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fichier CSV", "", "CSV (*.csv);;Tous (*)")
        if not path:
            return
        self._csv_path = path
        s = path
        self._csv_lbl.setText(("…" + s[-32:]) if len(s) > 32 else s)
        self._csv_lbl.setStyleSheet(
            f"color:{GREEN}; font-size:10px; font-family:'Courier New',monospace; background:transparent;")
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

        n   = res['n_rows']; att = res['n_attacks']
        nor = res['n_normal']; gc  = res['global_conf']
        pct = att / n * 100 if n else 0
        acc = res['accuracy']

        # Confiance
        self._conf_bar.setValue(int(gc))
        self._conf_val.setText(f"{gc:.1f}%")
        clr = GREEN if gc >= 90 else (ORANGE if gc >= 70 else RED)
        self._conf_val.setStyleSheet(
            f"color:{clr}; font-size:58px; font-weight:bold; "
            f"font-family:'Courier New',monospace; background:transparent;")

        if pct > 30:
            badge, bclr = "◉  CRITIQUE — MENACES DÉTECTÉES", RED
        elif pct > 5:
            badge, bclr = "◎  SUSPECT — SURVEILLER", ORANGE
        else:
            badge, bclr = "◉  RÉSEAU SÉCURISÉ", GREEN
        self._badge.setText(badge)
        self._badge.setStyleSheet(
            f"color:{bclr}; font-size:10px; letter-spacing:2px; "
            f"font-family:'Courier New',monospace; background:transparent;")

        self._cards["total"].set_value(f"{n:,}", CYAN)
        self._cards["attacks"].set_value(f"{att:,}  ({pct:.1f}%)", RED if att > 0 else GREEN)
        self._cards["normal"].set_value(f"{nor:,}  ({100-pct:.1f}%)", GREEN)
        self._cards["accuracy"].set_value(f"{acc:.1f}%" if acc else "N/A", ORANGE)

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
        feat  = [c for c in df.columns if c not in fixed][:14]
        cols  = fixed + feat
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
                    item.setText("▲ ATTAQUE" if is_att else "● NORMAL")
                    item.setForeground(QColor(RED if is_att else GREEN))
                    item.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
                elif col == 'Prédiction':
                    item.setForeground(QColor(RED if is_att else GREEN))
                elif col == 'Confiance':
                    item.setForeground(QColor(ORANGE))
                else:
                    item.setForeground(QColor("#8aa8c8"))
                if is_att:
                    item.setBackground(QColor(45, 8, 12))
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
        self._dist_fig.patch.set_facecolor(PANEL)
        ax = self._dist_fig.add_subplot(111)
        ax.set_facecolor(PANEL)

        labels, values, colors = [], [], []
        if n_normal:
            labels.append("Normal"); values.append(n_normal); colors.append(GREEN)
        palette = [RED, ORANGE, '#9b59b6', '#1abc9c', '#e91e63']
        for i, (k, v) in enumerate(sorted(attack_dist.items(), key=lambda x: -x[1])):
            labels.append(k); values.append(v); colors.append(palette[i % len(palette)])

        if values:
            wedges, texts, autos = ax.pie(
                values, colors=colors, autopct='%1.0f%%',
                startangle=90, pctdistance=0.72,
                wedgeprops=dict(edgecolor=BG, linewidth=2, width=0.55),
                textprops=dict(color='white', fontsize=8, fontfamily='Courier New'))
            for a in autos:
                a.set_fontweight('bold')
            patches = [mpatches.Patch(color=c, label=l[:14])
                       for c, l in zip(colors, labels)]
            ax.legend(handles=patches, loc='lower center',
                      bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False,
                      prop={'family': 'Courier New', 'size': 7},
                      labelcolor='#8aa8c8')

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
        self._table.clear(); self._table.setRowCount(0)
        self._dist_fig.clear(); self._dist_canvas.draw()
        self._conf_val.setText("—")
        self._conf_val.setStyleSheet(
            f"color:{CYAN}; font-size:58px; font-weight:bold; "
            f"font-family:'Courier New',monospace; background:transparent;")
        self._conf_bar.setValue(0)
        self._badge.setText("◉  EN ATTENTE")
        self._badge.setStyleSheet(
            f"color:{MUTED}; font-size:10px; letter-spacing:2px; "
            f"font-family:'Courier New',monospace; background:transparent;")
        self._prog.setValue(0); self._prog_lbl.setText("—")
        self._csv_lbl.setText("Aucun fichier")
        self._csv_lbl.setStyleSheet(
            f"color:{MUTED}; font-size:10px; font-family:'Courier New',monospace; background:transparent;")
        for c in self._cards.values():
            c.set_value("—")
        self._run_btn.setEnabled(False); self._exp_btn.setEnabled(False)
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