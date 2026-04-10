import sys
import os
import random
from datetime import datetime
from collections import defaultdict

# Permet d'importer depuis le dossier parent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# === IMPORTATION DE NOTRE ARCHITECTURE ===
from config import COLORS
from gui.components import AnimatedLabel


class TrafficAnalyzerInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analyseur de Trafic Réseau - Interface 3")
        screen = QApplication.primaryScreen()
        size = screen.size()

        self.setGeometry(QRect(0, 0, size.width(), size.height()))
        self.setFixedSize(size.width(), size.height() - 80)

        # Application du fond sombre SaaS
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS['bg_dark']))
        self.setPalette(palette)

        # Données simulées
        self.traffic_data = self.generate_traffic_data()

        self.setup_style()
        self.init_ui()

        # Timer pour mise à jour en temps réel
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(10000)

    def setup_style(self):
        """Configuration du style SaaS Moderne unifié"""
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_bright']};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }}
            QLabel#stat_label {{
                font-size: 13px;
                font-weight: bold;
                color: {COLORS['text']};
            }}
            QLabel#value_label {{
                font-size: 22px;
                font-weight: bold;
                color: {COLORS['text_bright']};
            }}
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                background-color: {COLORS['bg_medium']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: {COLORS['info']};
            }}
            QTableWidget {{
                background-color: {COLORS['bg_medium']};
                alternate-background-color: {COLORS['bg_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                gridline-color: {COLORS['accent']};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {COLORS['accent']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['info']};
                color: {COLORS['bg_dark']};
            }}
            QHeaderView::section {{
                background-color: #0B1120;
                color: {COLORS['text_bright']};
                padding: 10px;
                border: none;
                border-right: 1px solid {COLORS['accent']};
                border-bottom: 2px solid {COLORS['info']};
                font-weight: bold;
                font-size: 12px;
            }}
            QProgressBar {{
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 22px;
                background-color: {COLORS['bg_dark']};
                font-size: 11px;
            }}
            QPushButton {{
                background-color: #0EA5E9;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #0284C7; }}
            QPushButton:pressed {{ background-color: #0369A1; }}
            QPushButton#secondary {{
                background-color: {COLORS['accent']};
            }}
            QPushButton#secondary:hover {{ background-color: #475569; }}

            QTabWidget::pane {{
                border: 1px solid {COLORS['accent']};
                border-radius: 8px;
                background-color: {COLORS['bg_dark']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['text']};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['info']};
                color: {COLORS['bg_dark']};
            }}
            QLineEdit {{
                padding: 8px 12px;
                background-color: #334155;
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                color: white;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['info']};
            }}
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # En-tête avec titre animé
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)

        # Contenu principal avec onglets
        tab_widget = QTabWidget()

        overview_tab = self.create_overview_tab()
        tab_widget.addTab(overview_tab, "📊 Vue d'ensemble")

        ip_tab = self.create_ip_tab()
        tab_widget.addTab(ip_tab, "🌐 Adresses IP")

        ports_tab = self.create_ports_tab()
        tab_widget.addTab(ports_tab, "🔌 Ports")

        main_layout.addWidget(tab_widget)

    def create_header(self):
        header_layout = QHBoxLayout()

        # Remplacement par notre titre animé
        self.title = AnimatedLabel("🌐 ANALYSE DU TRAFIC RÉSEAU")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

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
        self.time_label = QLabel()
        self.time_label.setObjectName("stat_label")
        self.update_timestamp()

        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(self.time_label)

        return header_layout

    def create_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        stats_widget = self.create_stats_widget()
        layout.addWidget(stats_widget)

        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(15)

        protocol_group = QGroupBox("Répartition des protocoles")
        protocol_layout = QVBoxLayout()
        protocol_layout.setSpacing(12)

        # TCP (Bleu Info)
        tcp_layout = QHBoxLayout()
        tcp_label = QLabel("TCP")
        tcp_label.setObjectName("stat_label")
        tcp_label.setMinimumWidth(50)
        self.tcp_bar = QProgressBar()
        self.tcp_bar.setRange(0, 100)
        self.tcp_bar.setValue(60)
        self.tcp_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['info']}; border-radius: 4px; }}")
        self.tcp_percent = QLabel("60%")
        self.tcp_percent.setObjectName("value_label")
        self.tcp_percent.setStyleSheet(f"color: {COLORS['info']}; font-size: 18px;")
        tcp_layout.addWidget(tcp_label)
        tcp_layout.addWidget(self.tcp_bar)
        tcp_layout.addWidget(self.tcp_percent)
        protocol_layout.addLayout(tcp_layout)

        # UDP (Vert Success)
        udp_layout = QHBoxLayout()
        udp_label = QLabel("UDP")
        udp_label.setObjectName("stat_label")
        udp_label.setMinimumWidth(50)
        self.udp_bar = QProgressBar()
        self.udp_bar.setRange(0, 100)
        self.udp_bar.setValue(30)
        self.udp_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {COLORS['success']}; border-radius: 4px; }}")
        self.udp_percent = QLabel("30%")
        self.udp_percent.setObjectName("value_label")
        self.udp_percent.setStyleSheet(f"color: {COLORS['success']}; font-size: 18px;")
        udp_layout.addWidget(udp_label)
        udp_layout.addWidget(self.udp_bar)
        udp_layout.addWidget(self.udp_percent)
        protocol_layout.addLayout(udp_layout)

        # ICMP (Orange Warning)
        icmp_layout = QHBoxLayout()
        icmp_label = QLabel("ICMP")
        icmp_label.setObjectName("stat_label")
        icmp_label.setMinimumWidth(50)
        self.icmp_bar = QProgressBar()
        self.icmp_bar.setRange(0, 100)
        self.icmp_bar.setValue(10)
        self.icmp_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {COLORS['warning']}; border-radius: 4px; }}")
        self.icmp_percent = QLabel("10%")
        self.icmp_percent.setObjectName("value_label")
        self.icmp_percent.setStyleSheet(f"color: {COLORS['warning']}; font-size: 18px;")
        icmp_layout.addWidget(icmp_label)
        icmp_layout.addWidget(self.icmp_bar)
        icmp_layout.addWidget(self.icmp_percent)
        protocol_layout.addLayout(icmp_layout)

        protocol_group.setLayout(protocol_layout)
        chart_layout.addWidget(protocol_group)

        # Volume de données
        volume_group = QGroupBox("Volume de données")
        volume_layout = QVBoxLayout()

        self.volume_label = QLabel("2.4 GB")
        self.volume_label.setObjectName("value_label")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_label.setStyleSheet("font-size: 24px;")
        volume_layout.addWidget(self.volume_label)

        volume_detail = QLabel("↑ 1.2 GB · ↓ 1.2 GB")
        volume_detail.setObjectName("stat_label")
        volume_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volume_layout.addWidget(volume_detail)

        volume_group.setLayout(volume_layout)
        chart_layout.addWidget(volume_group)

        # Paquets par seconde
        pps_group = QGroupBox(" Paquets/s")
        pps_layout = QVBoxLayout()

        self.pps_label = QLabel("1,450")
        self.pps_label.setObjectName("value_label")
        self.pps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pps_label.setStyleSheet("font-size: 24px;")
        pps_layout.addWidget(self.pps_label)

        pps_trend = QLabel("+12% vs moyenne")
        pps_trend.setObjectName("stat_label")
        pps_trend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pps_trend.setStyleSheet(f"color: {COLORS['success']};")
        pps_layout.addWidget(pps_trend)

        pps_group.setLayout(pps_layout)
        chart_layout.addWidget(pps_group)

        layout.addLayout(chart_layout)

        ip_group = QGroupBox("Top 5 IP - Volume de données et Paquets")
        ip_layout = QVBoxLayout()

        self.ip_table = QTableWidget()
        self.ip_table.setColumnCount(5)
        self.ip_table.setHorizontalHeaderLabels(["Adresse IP", " Volume (MB)", " Paquets", "TCP/UDP/ICMP", "% Trafic"])

        header = self.ip_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.ip_table.setAlternatingRowColors(True)

        self.update_ip_table()
        ip_layout.addWidget(self.ip_table)

        ip_group.setLayout(ip_layout)
        layout.addWidget(ip_group)

        return tab

    def create_ip_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtrer par IP:")
        filter_label.setObjectName("stat_label")

        self.ip_filter = QLineEdit()
        self.ip_filter.setPlaceholderText("Ex: 192.168...")

        filter_btn = QPushButton("🔍 Rechercher")
        filter_btn.clicked.connect(self.filter_ips)

        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self.reset_filter)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.ip_filter)
        filter_layout.addWidget(filter_btn)
        filter_layout.addWidget(reset_btn)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        self.detailed_ip_table = QTableWidget()
        self.detailed_ip_table.setColumnCount(6)
        self.detailed_ip_table.setHorizontalHeaderLabels([
            "Adresse IP", "Paquets TCP", "Paquets UDP", "Paquets ICMP",
            "Volume Total", "Dernière activité"
        ])
        self.detailed_ip_table.horizontalHeader().setStretchLastSection(True)
        self.detailed_ip_table.setAlternatingRowColors(True)
        self.update_detailed_ip_table()

        layout.addWidget(self.detailed_ip_table)
        return tab

    def create_ports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        tcp_ports_group = QGroupBox(" Top ports TCP")
        tcp_ports_layout = QVBoxLayout()

        self.tcp_ports_table = QTableWidget()
        self.tcp_ports_table.setColumnCount(3)
        self.tcp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Connexions"])
        self.tcp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.tcp_ports_table.setAlternatingRowColors(True)
        self.update_tcp_ports_table()
        tcp_ports_layout.addWidget(self.tcp_ports_table)

        tcp_ports_group.setLayout(tcp_ports_layout)
        stats_layout.addWidget(tcp_ports_group)

        udp_ports_group = QGroupBox("Top ports UDP")
        udp_ports_layout = QVBoxLayout()

        self.udp_ports_table = QTableWidget()
        self.udp_ports_table.setColumnCount(3)
        self.udp_ports_table.setHorizontalHeaderLabels(["Port", "Service", "Datagrammes"])
        self.udp_ports_table.horizontalHeader().setStretchLastSection(True)
        self.udp_ports_table.setAlternatingRowColors(True)
        self.update_udp_ports_table()
        udp_ports_layout.addWidget(self.udp_ports_table)

        udp_ports_group.setLayout(udp_ports_layout)
        stats_layout.addWidget(udp_ports_group)

        layout.addLayout(stats_layout)

        ports_activity_group = QGroupBox("Activité en direct des ports (Top 5)")
        ports_activity_layout = QVBoxLayout()
        ports_activity_layout.setSpacing(12)

        ports_list = [80, 443, 22, 53, 3389]
        self.live_port_bars = []
        for port in ports_list:
            port_layout = QHBoxLayout()
            port_label = QLabel(f"Port {port}")
            port_label.setObjectName("stat_label")
            port_label.setMinimumWidth(80)

            port_bar = QProgressBar()
            port_bar.setRange(0, 100)
            val = random.randint(30, 95)
            port_bar.setValue(val)
            port_bar.setFormat(f"{val} conn/s")
            port_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['info']}; border-radius: 4px; }}")

            self.live_port_bars.append(port_bar)

            port_layout.addWidget(port_label)
            port_layout.addWidget(port_bar)
            ports_activity_layout.addLayout(port_layout)

        ports_activity_group.setLayout(ports_activity_layout)
        layout.addWidget(ports_activity_group)

        return tab

    def create_stats_widget(self):
        group = QGroupBox(" Statistiques en temps réel")
        layout = QHBoxLayout()
        layout.setSpacing(10)

        stats = [
            (" Connexions actives", "1,234", COLORS['info']),
            (" Taux de perte", "0.2%", COLORS['success']),
            (" Latence moyenne", "24ms", COLORS['warning']),
            (" Sessions TCP", "892", COLORS['danger'])
        ]

        for title, value, color in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(5)

            title_label = QLabel(title)
            title_label.setObjectName("stat_label")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            value_label = QLabel(value)
            value_label.setObjectName("value_label")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setStyleSheet(f"color: {color};")

            stat_layout.addWidget(title_label)
            stat_layout.addWidget(value_label)
            layout.addWidget(stat_widget)

        group.setLayout(layout)
        return group

    def generate_traffic_data(self):
        data = {
            'ips': {},
            'ports_tcp': defaultdict(int),
            'ports_udp': defaultdict(int)
        }

        base_ips = [
            "192.168.1.50", "192.168.1.100", "192.168.1.150",
            "192.168.1.200", "10.0.0.25", "10.0.0.50",
            "172.16.0.10", "172.16.0.20", "192.168.1.75",
            "192.168.1.125"
        ]

        for ip in base_ips:
            tcp = random.randint(500, 8000)
            udp = random.randint(200, 3000)
            icmp = random.randint(20, 800)
            data['ips'][ip] = {
                'tcp': tcp,
                'udp': udp,
                'icmp': icmp,
                'last_seen': datetime.now()
            }

        popular_ports = {
            80: 'HTTP', 443: 'HTTPS', 22: 'SSH', 53: 'DNS',
            3389: 'RDP', 8080: 'HTTP-Alt', 3306: 'MySQL',
            5432: 'PostgreSQL', 25: 'SMTP', 110: 'POP3'
        }

        for port, service in popular_ports.items():
            data['ports_tcp'][port] = random.randint(50, 1000)
            data['ports_udp'][port] = random.randint(20, 500)

        return data

    def update_data(self):
        tcp = random.randint(55, 65)
        udp = random.randint(25, 35)
        icmp = 100 - tcp - udp

        self.tcp_bar.setValue(tcp)
        self.udp_bar.setValue(udp)
        self.icmp_bar.setValue(icmp)

        self.tcp_percent.setText(f"{tcp}%")
        self.udp_percent.setText(f"{udp}%")
        self.icmp_percent.setText(f"{icmp}%")

        volume = random.uniform(1.8, 3.2)
        self.volume_label.setText(f"{volume:.1f} GB")

        pps = random.randint(1200, 1800)
        self.pps_label.setText(f"{pps:,}")

        # Mise à jour des barres d'activité live
        for bar in getattr(self, 'live_port_bars', []):
            val = random.randint(30, 95)
            bar.setValue(val)
            bar.setFormat(f"{val} conn/s")

        self.update_ip_table()
        self.update_detailed_ip_table()
        self.update_tcp_ports_table()
        self.update_udp_ports_table()
        self.update_timestamp()

    def update_timestamp(self):
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.setText(f"Dernière mise à jour : {current_time}")

    def update_ip_table(self):
        sorted_ips = sorted(
            self.traffic_data['ips'].items(),
            key=lambda x: (x[1]['tcp'] + x[1]['udp'] + x[1]['icmp']) * random.uniform(0.8, 1.5),
            reverse=True
        )[:5]

        self.ip_table.setRowCount(len(sorted_ips))
        total_volume = sum((data['tcp'] + data['udp'] + data['icmp']) * 0.001 for _, data in sorted_ips)

        for row, (ip, data) in enumerate(sorted_ips):
            packets = data['tcp'] + data['udp'] + data['icmp']
            volume = packets * random.uniform(0.0008, 0.0012)

            items_data = [
                (ip, COLORS['text_bright'], True),
                (f"{volume:.1f} MB", COLORS['warning'], False),
                (f"{packets:,}", COLORS['info'], False),
                (f"TCP:{data['tcp']:,} | UDP:{data['udp']:,} | ICMP:{data['icmp']}", COLORS['text'], False),
                (f"{(volume / total_volume * 100) if total_volume > 0 else 0:.1f}%", COLORS['success'], True)
            ]

            for col, (text, color, is_bold) in enumerate(items_data):
                item = QTableWidgetItem(text)
                item.setForeground(QColor(color))
                if is_bold:
                    item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                self.ip_table.setItem(row, col, item)

    def update_detailed_ip_table(self):
        ips = list(self.traffic_data['ips'].items())
        self.detailed_ip_table.setRowCount(len(ips))

        for row, (ip, data) in enumerate(ips):
            items = [
                (ip, COLORS['text_bright']),
                (f"{data['tcp']:,}", COLORS['info']),
                (f"{data['udp']:,}", COLORS['success']),
                (f"{data['icmp']:,}", COLORS['warning']),
                (f"{(data['tcp'] + data['udp'] + data['icmp']) * 0.001:.1f} MB", COLORS['text_bright']),
                (data['last_seen'].strftime("%H:%M:%S"), COLORS['text'])
            ]
            for col, (value, color) in enumerate(items):
                item = QTableWidgetItem(str(value))
                item.setForeground(QColor(color))
                self.detailed_ip_table.setItem(row, col, item)

    def update_tcp_ports_table(self):
        sorted_ports = sorted(self.traffic_data['ports_tcp'].items(), key=lambda x: x[1], reverse=True)[:10]
        self.tcp_ports_table.setRowCount(len(sorted_ports))

        services = {80: 'HTTP', 443: 'HTTPS', 22: 'SSH', 3389: 'RDP', 8080: 'HTTP-Alt', 3306: 'MySQL',
                    5432: 'PostgreSQL', 25: 'SMTP', 110: 'POP3', 143: 'IMAP', 993: 'IMAPS', 995: 'POP3S', 21: 'FTP',
                    23: 'Telnet'}

        for row, (port, count) in enumerate(sorted_ports):
            self.tcp_ports_table.setItem(row, 0, QTableWidgetItem(str(port)))
            self.tcp_ports_table.setItem(row, 1, QTableWidgetItem(services.get(port, 'Inconnu')))

            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setForeground(QColor(COLORS['info']))
            self.tcp_ports_table.setItem(row, 2, count_item)

    def update_udp_ports_table(self):
        sorted_ports = sorted(self.traffic_data['ports_udp'].items(), key=lambda x: x[1], reverse=True)[:10]
        self.udp_ports_table.setRowCount(len(sorted_ports))

        services = {53: 'DNS', 67: 'DHCP', 68: 'DHCP', 69: 'TFTP', 123: 'NTP', 161: 'SNMP', 162: 'SNMP-Trap',
                    500: 'IPsec', 1194: 'OpenVPN'}

        for row, (port, count) in enumerate(sorted_ports):
            self.udp_ports_table.setItem(row, 0, QTableWidgetItem(str(port)))
            self.udp_ports_table.setItem(row, 1, QTableWidgetItem(services.get(port, 'Inconnu')))

            count_item = QTableWidgetItem(f"{count:,}")
            count_item.setForeground(QColor(COLORS['success']))
            self.udp_ports_table.setItem(row, 2, count_item)

    def filter_ips(self):
        filter_text = self.ip_filter.text().lower()
        for row in range(self.detailed_ip_table.rowCount()):
            ip_item = self.detailed_ip_table.item(row, 0)
            if ip_item:
                self.detailed_ip_table.setRowHidden(row, filter_text not in ip_item.text().lower())

    def reset_filter(self):
        self.ip_filter.clear()
        for row in range(self.detailed_ip_table.rowCount()):
            self.detailed_ip_table.setRowHidden(row, False)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    window = TrafficAnalyzerInterface()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()