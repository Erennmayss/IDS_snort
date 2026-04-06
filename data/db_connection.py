import psycopg2

def connect_db():
    try:
        conn = psycopg2.connect(
            host="192.168.1.2",
            database="ids_db",
            user="aya", # ou "aya" selon ta config
            password="aya",
            port="5432",
            connect_timeout=3 # Limite l'attente à 3 secondes
        )
        return conn
    except Exception as e:
        print(f"⚠️ Erreur de connexion : {e}")
        return None