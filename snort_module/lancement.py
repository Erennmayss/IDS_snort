import subprocess
import time


class SnortManager:
    def __init__(self):
        self.process = None
        self.snort_running = False
        self.snort_process = None

    def start_snort(self):
        try:
            cmd = [
                "sudo", "snort",  # Enlever le -n pour ne pas avoir besoin de mot de passe
                "-A", "fast",
                "-i", "enp0s3",  # Vérifiez que c'est votre interface réseau
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort",
                "-D"  # Mode daemon (tourne en arrière-plan)
            ]

            # Vérifier si Snort est déjà en cours
            if self.snort_process and self.snort_process.poll() is None:
                print("⚠️ Snort déjà en cours")
                self.snort_running = True
                return True

            print("🚀 Lancement de Snort...")
            self.snort_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Attendre un peu pour vérifier
            time.sleep(3)

            # Vérifier si le processus tourne toujours
            if self.snort_process.poll() is None:
                self.snort_running = True
                print("✅ Snort démarré avec succès")
                return True
            else:
                # Récupérer l'erreur
                _, error = self.snort_process.communicate()
                self.snort_running = False
                print(f"❌ Snort a échoué: {error.decode()}")
                return False

        except Exception as e:
            self.snort_running = False
            print(f"❌ Exception lors du démarrage de Snort: {e}")
            return False

    def stop_snort(self):
        try:
            if self.snort_process and self.snort_process.poll() is None:
                self.snort_process.terminate()
                time.sleep(2)
                if self.snort_process.poll() is None:
                    self.snort_process.kill()
                self.snort_process = None

            # Tuer tous les processus Snort en secours
            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

            self.snort_running = False
            print("🛑 Snort arrêté")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'arrêt de Snort: {e}")
            return False

    def is_running(self):
        """Vérifie si Snort est en cours d'exécution"""
        try:
            result = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)
            return result.returncode == 0
        except:
            return False