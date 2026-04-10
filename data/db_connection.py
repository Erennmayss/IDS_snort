import psycopg2

def connect_db():
    try:
        conn = psycopg2.connect(
            host="192.168.1.2",  # Changé de 192.168.1.2 à localhost
            database="ids_db",
            user="aya",
            password="aya",
            port="5432",
            connect_timeout=3
        )
        return conn
    except Exception as e:
        print(f"⚠️ Erreur de connexion : {e}")
        return None