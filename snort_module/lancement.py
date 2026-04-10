import subprocess
import time
import signal
import os


class SnortManager:
    def __init__(self):
        self.snort_running = False

    def start_snort(self):
        try:
            interface = "enp0s3"

            # Version 1: Utiliser shell=True avec nohup pour garder Snort en vie
            cmd = f"sudo snort -A fast -i {interface} -c /etc/snort/snort.conf -l /var/log/snort -D"

            print(f"🚀 Lancement de Snort sur l'interface {interface}...")
            print(f"Commande: {cmd}")

            # Exécuter la commande et ignorer la sortie
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            # Snort en mode daemon se lance toujours avec succès
            # Le code de retour peut être 0 ou 1, on vérifie si le processus existe
            time.sleep(2)

            # Vérifier si Snort tourne vraiment
            check = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)

            if check.returncode == 0:
                self.snort_running = True
                print("✅ Snort démarré avec succès en mode daemon")
                return True
            else:
                print("❌ Snort n'a pas démarré correctement")
                return False

        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

    def stop_snort(self):
        try:
            # Tuer tous les processus Snort
            subprocess.run("sudo pkill -f snort", shell=True, capture_output=True)
            time.sleep(1)
            self.snort_running = False
            print("🛑 Snort arrêté")
            return True
        except Exception as e:
            print(f"❌ Erreur arrêt: {e}")
            return False

    def is_running(self):
        """Vérifie si Snort tourne"""
        try:
            result = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)
            running = result.returncode == 0
            self.snort_running = running
            return running
        except:
            return False