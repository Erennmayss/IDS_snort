import subprocess
import time
import threading
import re
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db_connection import connect_db


class SnortManager:
    def __init__(self, interface="enp0s3"):
        self.snort_running = False
        self.snort_process = None
        self.output_thread = None
        self.interface = interface
        self.connection = None
        self.cursor = None
        self.alert_count = 0
        self.db_count = 0
        self.init_db()

    def init_db(self):
        """Initialise la connexion à la base"""
        try:
            self.connection = connect_db()
            if self.connection:
                self.cursor = self.connection.cursor()
                print("✅ Connexion DB établie")
        except Exception as e:
            print(f"⚠️ DB non disponible: {e}")

    def parse_alert_line(self, line):
        """Parse une ligne d'alerte au format CSV"""
        # Format: Timestamp | SID | IP Source | IP Dest | Attack Type | Severity | Proto | Src Port | Dst Port | Loss | Traffic | Services
        parts = [p.strip() for p in line.split("|")]

        if len(parts) >= 12:
            return {
                'timestamp': parts[0],
                'sid': parts[1],
                'source_ip': parts[2],
                'destination_ip': parts[3],
                'attack_type': parts[4],
                'severity': int(parts[5]) if parts[5].isdigit() else 0,
                'protocol': parts[6],
                'source_port': int(parts[7]) if parts[7].isdigit() else None,
                'destination_port': int(parts[8]) if parts[8].isdigit() else None,
                'loss': parts[9],
                'traffic': parts[10],
                'services': parts[11]
            }
        return None

    def save_to_db(self, alert):
        """Sauvegarde l'alerte dans la base"""
        if not self.connection:
            return False

        try:
            self.cursor.execute("""
                INSERT INTO alertes 
                (timestamp, source_ip, destination_ip, attack_type, severity, 
                 protocol, source_port, destination_port, loss, volume, service, detection_engine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert['timestamp'],
                alert['source_ip'],
                alert['destination_ip'],
                alert['attack_type'],
                alert['severity'],
                alert['protocol'],
                alert['source_port'],
                alert['destination_port'],
                alert['loss'],
                alert['traffic'],
                alert['services'],
                'Snort'
            ))
            self.connection.commit()
            self.db_count += 1
            return True
        except Exception as e:
            print(f"❌ Erreur insertion: {e}")
            return False

    def start_snort(self):
        try:
            print(f"\n{'=' * 80}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU")
            print(f"{'=' * 80}")
            print(f"📡 Interface: {self.interface}")
            print(f"💾 Base de données: {'✅ Activée' if self.connection else '❌ Désactivée'}")
            print(f"{'=' * 80}\n")

            # Commande Snort avec sortie en mode console
            cmd = f"sudo snort -A console -i {self.interface} -c /etc/snort/snort.conf"

            print(f"🔄 Démarrage de Snort...\n")

            self.snort_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self.output_thread = threading.Thread(target=self.process_output, daemon=True)
            self.output_thread.start()

            # Thread stats
            stats_thread = threading.Thread(target=self.show_stats, daemon=True)
            stats_thread.start()

            self.snort_running = True
            return True

        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

    def process_output(self):
        """Traite la sortie Snort"""
        for line in iter(self.snort_process.stdout.readline, ''):
            if line:
                line = line.strip()
                if line and "|" in line and not line.startswith("Timestamp"):
                    # C'est une alerte au format CSV
                    alert = self.parse_alert_line(line)
                    if alert:
                        self.alert_count += 1
                        print(f"\n\033[91m🚨 {alert['attack_type']}\033[0m")
                        print(
                            f"   📍 {alert['source_ip']}:{alert['source_port']} -> {alert['destination_ip']}:{alert['destination_port']}")
                        print(f"   📡 {alert['protocol']} | Severity: {alert['severity']}")

                        if self.connection:
                            if self.save_to_db(alert):
                                print(f"   💾 Sauvegardé en DB")
                elif "ALERT" in line:
                    print(f"\n\033[91m🚨 {line}\033[0m")
                else:
                    print(line)

    def show_stats(self):
        """Affiche les stats toutes les 30 secondes"""
        while self.snort_running:
            time.sleep(30)
            if self.alert_count > 0:
                print(f"\n\033[96m{'=' * 80}")
                print(f"📊 STATS: {self.alert_count} alertes détectées, {self.db_count} en DB")
                print(f"{'=' * 80}\033[0m")

    def stop_snort(self):
        try:
            if self.snort_process:
                self.snort_process.terminate()
            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

            if self.connection:
                self.cursor.close()
                self.connection.close()

            self.snort_running = False
            print(f"\n📋 RAPPORT: {self.alert_count} alertes, {self.db_count} en DB")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False


if __name__ == "__main__":
    manager = SnortManager(interface="enp0s8")  # Change l'interface si besoin
    try:
        manager.start_snort()
        while manager.snort_running:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_snort()