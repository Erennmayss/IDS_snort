import psycopg2

def connect_db():
    conn = psycopg2.connect(
        host="192.168.1.2",
        database="ids_db",
        user="aya",
        password="aya",
        port="5432"
    )
    return conn