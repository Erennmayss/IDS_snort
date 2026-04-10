import subprocess
import time
import os


class SnortManager:
    def __init__(self):
        self.process = None
        self.snort_running = False
        self.snort_process = None

    def start_snort(self):
        try:
            # Interface réseau (enp0s3 dans votre cas)
            interface = "enp0s3"

            # Commande avec sudo (exactement comme vous avez testé)
            cmd = [
                "sudo", "snort",
                "-A", "fast",
                "-i", interface,
                "-c", "/etc/snort/snort.conf",
                "-l", "/var/log/snort",
                "-D"  # Mode daemon
            ]

            print(f"🚀 Lancement de Snort sur l'interface {interface}...")
            print(f"Commande: {' '.join(cmd)}")

            # Démarrer Snort
            self.snort_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Attendre que Snort démarre
            time.sleep(2)

            # Vérifier si le processus tourne
            if self.snort_process.poll() is None:
                self.snort_running = True
                print("✅ Snort démarré avec succès en mode daemon")
                return True
            else:
                # Lire l'erreur
                stdout, stderr = self.snort_process.communicate()
                if stderr:
                    print(f"❌ Erreur Snort: {stderr}")
                else:
                    print(f"❌ Snort a échoué: {stdout}")
                return False

        except FileNotFoundError:
            print("❌ Snort n'est pas installé ou n'est pas dans le PATH")
            print("   Installez Snort: sudo apt-get install snort")
            return False
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

    def get_active_interface(self):
        """Trouve l'interface réseau active"""
        try:
            # Vérifier si enp0s3 existe
            result = subprocess.run(
                ["ip", "addr", "show", "enp0s3"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Interface trouvée: enp0s3")
                return "enp0s3"

            # Fallback sur lo
            print("⚠️ Interface enp0s3 non trouvée, utilisation de 'lo'")
            return "lo"

        except Exception as e:
            print(f"❌ Erreur détection interface: {e}")
            return "lo"

    def stop_snort(self):
        try:
            # Arrêter le processus si existe
            if self.snort_process and self.snort_process.poll() is None:
                self.snort_process.terminate()
                time.sleep(2)
                if self.snort_process.poll() is None:
                    self.snort_process.kill()
                self.snort_process = None

            # Tuer tous les processus Snort
            subprocess.run(["sudo", "pkill", "-f", "snort"], capture_output=True)

            self.snort_running = False
            print("🛑 Snort arrêté")
            return True
        except Exception as e:
            print(f"❌ Erreur arrêt Snort: {e}")
            return False

    def is_running(self):
        """Vérifie si Snort tourne"""
        try:
            result = subprocess.run(["pgrep", "-f", "snort"], capture_output=True)
            return result.returncode == 0
        except:
            return False