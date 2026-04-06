# config.py
import os

# Configuration de la base de données centralisée
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.2'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ids_db'),
    'user': os.getenv('DB_USER', 'aya'),
    'password': os.getenv('DB_PASSWORD', 'aya'),
    'connect_timeout': 5
}


# Palette de couleurs unifiée (Charte "Slate/Sky")
COLORS = {
    'bg_dark': '#0F172A',       # Fond principal
    'bg_medium': '#1E293B',     # Fond secondaire (cartes, tableaux)
    'accent': '#334155',        # Bordures, boutons inactifs
    'success': '#10B981',       # Vert (Normal/Succès)
    'warning': '#F59E0B',       # Orange (Moyen)
    'danger': '#EF4444',        # Rouge (Alerte/Erreur)
    'info': '#38BDF8',          # Bleu technologique (Titres, Focus)
    'text': '#94A3B8',          # Texte secondaire
    'text_bright': '#F8FAFC',   # Texte principal
    'terminal_green': '#10B981' # Texte type terminal

}
COLORS['sidebar_bg'] = '#273549'  # Un bleu-gris plus clair et distingué
COLORS['sidebar_item_hover'] = '#334155'