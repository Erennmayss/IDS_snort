import sys
import pandas as pd
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QComboBox, QHeaderView, QMessageBox,
                             QFileDialog, QGroupBox, QGridLayout, QFrame, QStatusBar)
from PyQt6.QtCore import Qt, QDate, QTimer, QRect
from PyQt6.QtGui import QFont, QPalette, QColor, QBrush
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class RapportInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Générateur de Rapports de Sécurité - Console SOC")

        # Configuration de la base de données
        self.db_config = {
            'host': os.getenv('DB_HOST', '192.168.1.2'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'ids_db'),
            'user': os.getenv('DB_USER', 'marwa'),
            'password': os.getenv('marwa', 'marwa')
        }

        # Taille de la fenêtre
        screen = QApplication.primaryScreen()
        size = screen.size()
        self.setGeometry(0, 0, size.width(), size.height())
        self.setFixedSize(size.width(), size.height() - 80)

        # Couleurs pour l'interface
        self.colors = {
            'bg_dark': '#0A1929',
            'bg_medium': '#132F4C',
            'accent': '#1E4976',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'info': '#3498db',
            'text': '#E0E0E0',
            'text_bright': '#FFFFFF',
            'terminal_green': '#00ff00'
        }

        # Configuration du style
        self.setup_style()

        # Initialisation des données
        self.charger_donnees_mois()

        self.init_ui()

    def get_db_connection(self):
        """Établir une connexion à la base de données"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "❌ Erreur BD",
                                 f"Impossible de se connecter à la base de données:\n{str(e)}")
            return None

    def charger_donnees_mois(self):
        """Charger les données depuis PostgreSQL pour tous les mois"""
        self.donnees_rapports = {}

        conn = self.get_db_connection()
        if not conn:
            # Utiliser des données vides en cas d'erreur
            self.initialiser_donnees_vides()
            return

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Récupérer tous les mois disponibles dans la base
            cursor.execute("""
                SELECT 
                    TO_CHAR(timestamp, 'YYYY-MM') as mois,
                    COUNT(*) as total_attaques,
                    SUM(CASE WHEN attack_type = 'DoS' THEN 1 ELSE 0 END) as dos_count,
                    SUM(CASE WHEN attack_type = 'Scan Port' THEN 1 ELSE 0 END) as scans_count,
                    SUM(CASE WHEN attack_type = 'Brute Force' THEN 1 ELSE 0 END) as brute_force_count
                FROM security_alerts
                GROUP BY TO_CHAR(timestamp, 'YYYY-MM')
                ORDER BY mois
            """)

            mois_stats = cursor.fetchall()

            # Pour chaque mois, charger les détails
            for stat in mois_stats:
                mois_nom = self.convertir_mois_en_francais(stat['mois'])

                # Récupérer les détails pour ce mois
                cursor.execute("""
                    SELECT 
                        timestamp::date as date,
                        attack_type as type,
                        source_ip as source,
                        severity as severite
                    FROM security_alerts
                    WHERE TO_CHAR(timestamp, 'YYYY-MM') = %s
                    ORDER BY timestamp DESC
                """, (stat['mois'],))

                details = cursor.fetchall()

                self.donnees_rapports[mois_nom] = {
                    'attaques': stat['total_attaques'],
                    'dos': stat['dos_count'] or 0,
                    'scans': stat['scans_count'] or 0,
                    'brute_force': stat['brute_force_count'] or 0,
                    'details': [dict(d) for d in details]  # Convertir en dict standard
                }

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            QMessageBox.critical(self, "❌ Erreur BD",
                                 f"Erreur lors du chargement des données:\n{str(e)}")
            self.initialiser_donnees_vides()

    def initialiser_donnees_vides(self):
        """Initialiser des données vides en cas d'erreur"""
        mois_francais = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]

        for mois in mois_francais:
            self.donnees_rapports[mois] = {
                'attaques': 0,
                'dos': 0,
                'scans': 0,
                'brute_force': 0,
                'details': []
            }

    def convertir_mois_en_francais(self, mois_annee):
        """Convertir YYYY-MM en nom de mois français"""
        mois_en = {
            '01': 'janvier', '02': 'février', '03': 'mars', '04': 'avril',
            '05': 'mai', '06': 'juin', '07': 'juillet', '08': 'août',
            '09': 'septembre', '10': 'octobre', '11': 'novembre', '12': 'décembre'
        }
        mois_num = mois_annee.split('-')[1]
        return mois_en.get(mois_num, mois_annee)

    def setup_style(self):
        """Style optimisé pour informaticien"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['bg_dark']};
            }}
            QLabel {{
                color: {self.colors['text']};
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            QLabel#title_label {{
                font-size: 20px;
                font-weight: bold;
                color: {self.colors['text_bright']};
                padding: 10px;
                background-color: {self.colors['accent']};
                border-radius: 5px;
                letter-spacing: 1px;
            }}
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {self.colors['info']};
                border: 2px solid {self.colors['accent']};
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: rgba(10, 25, 41, 0.95);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: {self.colors['info']};
            }}
            QComboBox {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['text_bright']};
                border: 1px solid {self.colors['info']};
                border-radius: 3px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                min-width: 200px;
            }}
            QComboBox:hover {{
                border: 1px solid {self.colors['success']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['info']};
                width: 0;
                height: 0;
            }}
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', monospace;
            }}
            QPushButton:hover {{
                background-color: {self.colors['info']};
            }}
            QPushButton#pdf_button {{
                background-color: {self.colors['danger']};
            }}
            QPushButton#pdf_button:hover {{
                background-color: #c0392b;
            }}
            QPushButton#refresh_button {{
                background-color: {self.colors['success']};
            }}
            QPushButton#refresh_button:hover {{
                background-color: #27ae60;
            }}
            QTableWidget {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['info']};
                gridline-color: {self.colors['accent']};
                font-family: 'Consolas', monospace;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.colors['accent']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.colors['info']};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.colors['accent']};
                color: {self.colors['text_bright']};
                padding: 10px;
                border: 1px solid {self.colors['bg_dark']};
                font-weight: bold;
                font-size: 13px;
            }}
            QFrame#header_frame {{
                background-color: {self.colors['accent']};
                border-radius: 5px;
                padding: 10px;
            }}
            QFrame#toolbar_frame {{
                background-color: {self.colors['bg_medium']};
                border-radius: 5px;
                padding: 8px;
            }}
            QStatusBar {{
                background-color: {self.colors['bg_medium']};
                color: {self.colors['terminal_green']};
                font-family: 'Consolas', monospace;
            }}
        """)

    def init_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # En-tête
        self.creer_en_tete(main_layout)

        # Zone de contrôle
        self.creer_zone_controle(main_layout)

        # Tableau des détails
        self.creer_tableau_details(main_layout)

        # Barre d'outils inférieure
        self.creer_barre_outils(main_layout)

        # Barre d'état
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✓ Connecté à la base de données - Prêt à générer des rapports")

    def creer_en_tete(self, layout):
        # Frame d'en-tête
        header_frame = QFrame()
        header_frame.setObjectName("header_frame")

        header_layout = QHBoxLayout(header_frame)

        # Titre
        title_label = QLabel("GÉNÉRATEUR DE RAPPORTS DE SÉCURITÉ")
        title_label.setObjectName("title_label")
        header_layout.addWidget(title_label)

        # Horodatage
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {self.colors['terminal_green']}; font-size: 14px;")

        # Timer pour mettre à jour l'heure
        self.timer = QTimer()
        self.timer.timeout.connect(self.mettre_a_jour_heure)
        self.timer.start(1000)
        self.mettre_a_jour_heure()

        header_layout.addStretch()
        header_layout.addWidget(self.time_label)

        layout.addWidget(header_frame)

    def mettre_a_jour_heure(self):
        """Mettre à jour l'affichage de l'heure"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(f"🕒 {current_time}")

    def creer_zone_controle(self, layout):
        # Groupe de contrôle
        control_group = QGroupBox(" PÉRIODE DU RAPPORT")

        control_layout = QHBoxLayout(control_group)

        # Sélecteur de mois
        control_layout.addWidget(QLabel("⌂ Sélectionner le mois:"))

        self.mois_combo = QComboBox()

        # Ajouter les mois disponibles depuis la base de données
        mois_disponibles = ["Tous les mois"] + sorted([m for m in self.donnees_rapports.keys()
                                                       if self.donnees_rapports[m]['attaques'] > 0])

        # Si aucun mois avec données, ajouter tous les mois
        if len(mois_disponibles) == 1:  # Seulement "Tous les mois"
            mois_disponibles = ["Tous les mois"] + [
                "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"
            ]

        self.mois_combo.addItems(mois_disponibles)
        self.mois_combo.currentTextChanged.connect(self.mettre_a_jour_rapport)
        control_layout.addWidget(self.mois_combo)

        # Bouton de rafraîchissement
        self.refresh_btn = QPushButton("🔄 RAFRAÎCHIR")
        self.refresh_btn.setObjectName("refresh_button")
        self.refresh_btn.clicked.connect(self.rafraichir_donnees)
        control_layout.addWidget(self.refresh_btn)

        # Bouton PDF
        self.pdf_btn = QPushButton("⬇ EXPORTER EN PDF")
        self.pdf_btn.setObjectName("pdf_button")
        self.pdf_btn.clicked.connect(self.exporter_pdf)
        control_layout.addWidget(self.pdf_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

    def rafraichir_donnees(self):
        """Rafraîchir les données depuis la base"""
        self.status_bar.showMessage("🔄 Rafraîchissement des données...")
        self.charger_donnees_mois()

        # Mettre à jour le combo box
        current_text = self.mois_combo.currentText()
        self.mois_combo.clear()

        mois_disponibles = ["Tous les mois"] + sorted([m for m in self.donnees_rapports.keys()
                                                       if self.donnees_rapports[m]['attaques'] > 0])

        if len(mois_disponibles) == 1:
            mois_disponibles = ["Tous les mois"] + [
                "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"
            ]

        self.mois_combo.addItems(mois_disponibles)

        # Restaurer la sélection précédente si possible
        index = self.mois_combo.findText(current_text)
        if index >= 0:
            self.mois_combo.setCurrentIndex(index)

        self.mettre_a_jour_rapport()
        self.status_bar.showMessage("✓ Données rafraîchies avec succès")

    def creer_tableau_details(self, layout):
        # Groupe du tableau
        table_group = QGroupBox(" DÉTAILS DES ÉVÉNEMENTS DE SÉCURITÉ")
        table_layout = QVBoxLayout(table_group)

        # Tableau des détails
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(4)
        self.details_table.setHorizontalHeaderLabels(["Date", "Type d'attaque", "Source", "Sévérité"])

        # Ajustement des colonnes
        header = self.details_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        table_layout.addWidget(self.details_table)
        layout.addWidget(table_group)

    def creer_barre_outils(self, layout):
        # Barre d'outils inférieure
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbar_frame")

        toolbar_layout = QHBoxLayout(toolbar_frame)

        # Statistiques supplémentaires
        self.stats_label = QLabel("⚡ Données chargées depuis PostgreSQL")
        self.stats_label.setStyleSheet(f"color: {self.colors['info']}; font-size: 12px;")
        toolbar_layout.addWidget(self.stats_label)

        toolbar_layout.addStretch()

        layout.addWidget(toolbar_frame)

    def mettre_a_jour_rapport(self):
        mois = self.mois_combo.currentText()

        if mois == "Tous les mois":
            # Rassembler tous les détails de tous les mois
            tous_les_details = []
            for mois_data in self.donnees_rapports.values():
                tous_les_details.extend(mois_data.get('details', []))

            # Trier par date (plus récent en premier)
            tous_les_details.sort(key=lambda x: x['date'], reverse=True)

            # Mettre à jour le tableau
            self.details_table.setRowCount(len(tous_les_details))

            for i, detail in enumerate(tous_les_details):
                # Formater la date
                date_str = detail['date'].strftime('%Y-%m-%d') if hasattr(detail['date'], 'strftime') else str(
                    detail['date'])

                self.details_table.setItem(i, 0, QTableWidgetItem(date_str))
                self.details_table.setItem(i, 1, QTableWidgetItem(detail['type']))
                self.details_table.setItem(i, 2, QTableWidgetItem(detail['source']))

                # Coloration selon la sévérité
                severite_item = QTableWidgetItem(detail['severite'])
                if detail['severite'].lower() == 'haute' or detail['severite'].lower() == 'high':
                    severite_item.setBackground(QBrush(QColor(231, 76, 60, 100)))
                elif detail['severite'].lower() == 'moyenne' or detail['severite'].lower() == 'medium':
                    severite_item.setBackground(QBrush(QColor(243, 156, 18, 100)))
                else:
                    severite_item.setBackground(QBrush(QColor(46, 204, 113, 100)))

                self.details_table.setItem(i, 3, severite_item)

            # Mise à jour du label
            self.stats_label.setText(f"Rapport annuel chargé - {len(tous_les_details)} événements détaillés")
            self.status_bar.showMessage(f"✓ Rapport annuel chargé - {len(tous_les_details)} événements")

        elif mois in self.donnees_rapports:
            donnees = self.donnees_rapports[mois]

            # Mise à jour du tableau
            details = donnees.get('details', [])
            self.details_table.setRowCount(len(details))

            for i, detail in enumerate(details):
                # Formater la date
                date_str = detail['date'].strftime('%Y-%m-%d') if hasattr(detail['date'], 'strftime') else str(
                    detail['date'])

                self.details_table.setItem(i, 0, QTableWidgetItem(date_str))
                self.details_table.setItem(i, 1, QTableWidgetItem(detail['type']))
                self.details_table.setItem(i, 2, QTableWidgetItem(detail['source']))

                # Coloration selon la sévérité
                severite_item = QTableWidgetItem(detail['severite'])
                if detail['severite'].lower() == 'haute' or detail['severite'].lower() == 'high':
                    severite_item.setBackground(QBrush(QColor(231, 76, 60, 100)))
                elif detail['severite'].lower() == 'moyenne' or detail['severite'].lower() == 'medium':
                    severite_item.setBackground(QBrush(QColor(243, 156, 18, 100)))
                else:
                    severite_item.setBackground(QBrush(QColor(46, 204, 113, 100)))

                self.details_table.setItem(i, 3, severite_item)

            # Mise à jour du label
            self.stats_label.setText(f" Rapport {mois.capitalize()} chargé - {len(details)} événements détaillés")
            self.status_bar.showMessage(f"✓ Rapport {mois} chargé - {len(details)} événements")

    def exporter_pdf(self):
        mois = self.mois_combo.currentText()

        if mois == "Tous les mois":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer le rapport PDF",
                f"rapport_securite_annuel_{datetime.now().strftime('%Y%m%d')}.pdf",
                "Fichiers PDF (*.pdf)"
            )

            if filename:
                try:
                    self.generer_pdf_annuel(filename)
                    QMessageBox.information(self, "✅ Succès", f"Rapport annuel PDF généré avec succès:\n{filename}")
                    self.status_bar.showMessage(f"✓ PDF généré: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la génération du PDF:\n{str(e)}")

        elif mois in self.donnees_rapports:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer le rapport PDF",
                f"rapport_securite_{mois}_{datetime.now().strftime('%Y%m%d')}.pdf",
                "Fichiers PDF (*.pdf)"
            )

            if filename:
                try:
                    self.generer_pdf(filename, mois)
                    QMessageBox.information(self, "✅ Succès", f"Rapport PDF généré avec succès:\n{filename}")
                    self.status_bar.showMessage(f"✓ PDF généré: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "❌ Erreur", f"Erreur lors de la génération du PDF:\n{str(e)}")
        else:
            QMessageBox.warning(self, "⚠ Attention", "Aucune donnée disponible pour cette période")

    def generer_pdf(self, filename, mois):
        donnees = self.donnees_rapports[mois]

        # Création du document PDF
        doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0A1929'),
            spaceAfter=20,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        title = Paragraph(f"Rapport de Sécurité - {mois.capitalize()} {datetime.now().year}", title_style)
        story.append(title)

        # Date de génération
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1E4976'),
            alignment=2,
            fontName='Helvetica'
        )
        date_text = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        story.append(Paragraph(date_text, date_style))
        story.append(Spacer(1, 0.3 * inch))

        # Statistiques par type d'attaque
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#132F4C'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("Résumé des attaques par type", summary_style))

        # Compter les attaques par type
        types_attaques = {}
        for detail in donnees['details']:
            type_attaque = detail['type']
            types_attaques[type_attaque] = types_attaques.get(type_attaque, 0) + 1

        # Tableau des statistiques par type
        stats_data = [['Type d\'attaque', 'Nombre']]
        for type_attaque, count in types_attaques.items():
            stats_data.append([type_attaque, str(count)])

        stats_table = Table(stats_data, colWidths=[3 * inch, 1.5 * inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E4976')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#132F4C')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F0F0F0')])
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3 * inch))

        # Statistiques par IP source
        story.append(Paragraph("Statistiques par adresse IP source", summary_style))

        # Compter les attaques par IP
        ip_stats = {}
        for detail in donnees['details']:
            ip = detail['source']
            if ip not in ip_stats:
                ip_stats[ip] = {
                    'total': 0,
                    'types': {},
                    'severites': {'Haute': 0, 'Moyenne': 0, 'Basse': 0}
                }
            ip_stats[ip]['total'] += 1
            ip_stats[ip]['types'][detail['type']] = ip_stats[ip]['types'].get(detail['type'], 0) + 1

            # Compter par sévérité
            sev = detail['severite'].capitalize()
            if 'Haute' in sev or 'High' in sev:
                ip_stats[ip]['severites']['Haute'] += 1
            elif 'Moyenne' in sev or 'Medium' in sev:
                ip_stats[ip]['severites']['Moyenne'] += 1
            else:
                ip_stats[ip]['severites']['Basse'] += 1

        # Tableau des statistiques par IP
        ip_data = [['Adresse IP', 'Total', 'Haute', 'Moyenne', 'Basse', 'Types d\'attaques']]
        for ip, stats in ip_stats.items():
            # Formater les types d'attaques sur plusieurs lignes si nécessaire
            types_list = []
            for t, c in stats['types'].items():
                types_list.append(f"{t}:{c}")
            types_str = '\n'.join(types_list)  # Utiliser des sauts de ligne

            ip_data.append([
                ip,
                str(stats['total']),
                str(stats['severites']['Haute']),
                str(stats['severites']['Moyenne']),
                str(stats['severites']['Basse']),
                types_str
            ])

        # Ajuster les largeurs pour que tout tienne dans les cases
        ip_table = Table(ip_data, colWidths=[1.2 * inch, 0.5 * inch, 0.5 * inch, 0.6 * inch, 0.5 * inch, 2.5 * inch])
        ip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#132F4C')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')]),
            ('WORDWRAP', (5, 1), (5, -1), True)  # Activer le retour à la ligne pour la colonne des types
        ]))
        story.append(ip_table)
        story.append(Spacer(1, 0.3 * inch))

        # Détails des événements
        story.append(Paragraph("Détail des événements", summary_style))

        if donnees['details']:
            # En-têtes du tableau détaillé
            details_data = [['Date', 'Type', 'Source', 'Sévérité']]

            # Ajout des données
            for detail in donnees['details']:
                date_str = detail['date'].strftime('%Y-%m-%d') if hasattr(detail['date'], 'strftime') else str(
                    detail['date'])
                details_data.append([
                    date_str,
                    detail['type'],
                    detail['source'],
                    detail['severite']
                ])

            # Création du tableau détaillé - Largeurs ajustées
            details_table = Table(details_data, colWidths=[0.9 * inch, 1.8 * inch, 1.8 * inch, 0.8 * inch])

            # Style du tableau détaillé
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1E4976')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')])
            ]

            # Coloration selon la sévérité
            for i, detail in enumerate(donnees['details'], start=1):
                if detail['severite'].lower() in ['haute', 'high']:
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#FFE6E6')))
                    table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#CC0000')))
                elif detail['severite'].lower() in ['moyenne', 'medium']:
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#FFF4CC')))
                    table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#996600')))
                else:
                    table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#E6FFE6')))
                    table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#006600')))

            details_table.setStyle(TableStyle(table_style))
            story.append(details_table)
        else:
            story.append(Paragraph("Aucun détail d'événement disponible", styles['Normal']))

        # Pied de page
        story.append(Spacer(1, 0.3 * inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            fontName='Helvetica-Oblique'
        )
        footer_text = "Rapport généré automatiquement - Console SOC"
        story.append(Paragraph(footer_text, footer_style))

        # Génération du PDF
        doc.build(story)

    def generer_pdf_annuel(self, filename):
        # Rassembler tous les détails de tous les mois
        tous_les_details = []
        for mois, donnees in self.donnees_rapports.items():
            for detail in donnees.get('details', []):
                detail_avec_mois = dict(detail)
                detail_avec_mois['mois'] = mois
                tous_les_details.append(detail_avec_mois)

        # Trier par date (plus récent en premier)
        tous_les_details.sort(key=lambda x: x['date'], reverse=True)

        # Création du document PDF
        doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()

        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0A1929'),
            spaceAfter=20,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        title = Paragraph(f"Rapport de Sécurité Annuel {datetime.now().year}", title_style)
        story.append(title)

        # Date de génération
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1E4976'),
            alignment=2,
            fontName='Helvetica'
        )
        date_text = f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        story.append(Paragraph(date_text, date_style))
        story.append(Spacer(1, 0.3 * inch))

        # Statistiques annuelles par type d'attaque
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#132F4C'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("Résumé annuel des attaques par type", summary_style))

        # Compter les attaques par type pour l'année
        types_attaques_annuels = {}
        for detail in tous_les_details:
            type_attaque = detail['type']
            types_attaques_annuels[type_attaque] = types_attaques_annuels.get(type_attaque, 0) + 1

        # Tableau des statistiques par type
        stats_data = [['Type d\'attaque', 'Nombre']]
        for type_attaque, count in sorted(types_attaques_annuels.items(), key=lambda x: x[1], reverse=True):
            stats_data.append([type_attaque, str(count)])

        stats_table = Table(stats_data, colWidths=[3 * inch, 1.5 * inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E4976')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#132F4C')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F0F0F0')])
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3 * inch))

        # Statistiques par IP source
        story.append(Paragraph("Statistiques annuelles par adresse IP source", summary_style))

        # Compter les attaques par IP pour l'année
        ip_stats_annuels = {}
        for detail in tous_les_details:
            ip = detail['source']
            if ip not in ip_stats_annuels:
                ip_stats_annuels[ip] = {
                    'total': 0,
                    'types': {},
                    'severites': {'Haute': 0, 'Moyenne': 0, 'Basse': 0},
                    'mois': set()
                }
            ip_stats_annuels[ip]['total'] += 1
            ip_stats_annuels[ip]['types'][detail['type']] = ip_stats_annuels[ip]['types'].get(detail['type'], 0) + 1
            ip_stats_annuels[ip]['mois'].add(detail['mois'])

            # Compter par sévérité
            sev = detail['severite'].capitalize()
            if 'Haute' in sev or 'High' in sev:
                ip_stats_annuels[ip]['severites']['Haute'] += 1
            elif 'Moyenne' in sev or 'Medium' in sev:
                ip_stats_annuels[ip]['severites']['Moyenne'] += 1
            else:
                ip_stats_annuels[ip]['severites']['Basse'] += 1

        # Tableau des statistiques par IP
        ip_data = [['Adresse IP', 'Total', 'Haute', 'Moy.', 'Basse', 'Mois actifs', 'Types d\'attaques']]
        for ip, stats in sorted(ip_stats_annuels.items(), key=lambda x: x[1]['total'], reverse=True):
            mois_str = ', '.join(sorted([m[:3] for m in stats['mois']]))

            # Formater les types d'attaques sur plusieurs lignes
            types_list = []
            for t, c in sorted(stats['types'].items()):
                types_list.append(f"{t}:{c}")
            types_str = '\n'.join(types_list)  # Utiliser des sauts de ligne

            ip_data.append([
                ip,
                str(stats['total']),
                str(stats['severites']['Haute']),
                str(stats['severites']['Moyenne']),
                str(stats['severites']['Basse']),
                mois_str,
                types_str
            ])

        # Ajuster les largeurs pour que tout tienne dans les cases
        ip_table = Table(ip_data,
                         colWidths=[1.1 * inch, 0.4 * inch, 0.4 * inch, 0.4 * inch, 0.4 * inch, 0.8 * inch, 2.5 * inch])
        ip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (1, 1), (4, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#132F4C')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')]),
            ('WORDWRAP', (6, 1), (6, -1), True)  # Activer le retour à la ligne pour la colonne des types
        ]))
        story.append(ip_table)
        story.append(Spacer(1, 0.3 * inch))

        # Détails des événements
        story.append(Paragraph("Détail des événements annuels", summary_style))

        if tous_les_details:
            # Limiter à 50 événements pour éviter un PDF trop long
            details_a_afficher = tous_les_details[0:]
            if len(tous_les_details) > 50:
                story.append(
                    Paragraph(f"Affichage des 50 événements les plus récents sur {len(tous_les_details)} au total",
                              ParagraphStyle('Note', parent=styles['Normal'], fontSize=8,
                                             textColor=colors.HexColor('#666666'))))
                story.append(Spacer(1, 0.1 * inch))

            # En-têtes du tableau détaillé
            details_data = [['Date', 'Mois', 'Type', 'Source', 'Sévérité']]

            # Ajout des données
            for detail in details_a_afficher:
                date_str = detail['date'].strftime('%Y-%m-%d') if hasattr(detail['date'], 'strftime') else str(
                    detail['date'])
                details_data.append([
                    date_str,
                    detail['mois'].capitalize()[:3],
                    detail['type'],
                    detail['source'],
                    detail['severite']
                ])

            # Création du tableau détaillé - Largeur augmentée pour la colonne Type
            details_table = Table(details_data, colWidths=[0.7 * inch, 0.4 * inch, 2.5 * inch, 1.3 * inch, 0.7 * inch])

            # Style du tableau détaillé
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#132F4C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (1, -1), 'CENTER'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1E4976')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')]),
                ('WORDWRAP', (2, 1), (2, -1), True)  # Ajout du WORDWRAP pour la colonne Type (index 2)
            ]

            # Coloration selon la sévérité
            for i, detail in enumerate(details_a_afficher, start=1):
                if detail['severite'].lower() in ['haute', 'high']:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#FFE6E6')))
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#CC0000')))
                elif detail['severite'].lower() in ['moyenne', 'medium']:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#FFF4CC')))
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#996600')))
                else:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#E6FFE6')))
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#006600')))

            details_table.setStyle(TableStyle(table_style))
            story.append(details_table)
        else:
            story.append(Paragraph("Aucun détail d'événement disponible", styles['Normal']))

        # Pied de page
        story.append(Spacer(1, 0.3 * inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            fontName='Helvetica-Oblique'
        )
        footer_text = "Rapport annuel généré automatiquement - Console SOC"
        story.append(Paragraph(footer_text, footer_style))

        # Génération du PDF
        doc.build(story)


def main():
    app = QApplication(sys.argv)

    # Application du style global
    app.setStyle('Fusion')

    # Police pour informaticien
    font = QFont("Consolas", 9)
    app.setFont(font)

    # Palette de couleurs adaptée
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(10, 25, 41))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(19, 47, 76))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 73, 118))
    palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Button, QColor(30, 73, 118))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    app.setPalette(palette)

    # Création et affichage de la fenêtre principale
    window = RapportInterface()
    window.show()

    # Chargement initial du rapport
    window.mettre_a_jour_rapport()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()