import psycopg2
import re
from data.db_connection import connect_db

conn =connect_db()

cursor = conn.cursor()

def afficher_db():
    cursor.execute(
        """
        SELECT sid,rule FROM regles;
        """
    )
    rows=cursor.fetchall()
    return rows

def ajouter_regle(rule):
    cursor.execute(
        """INSERT INTO regles (rule)
        VALUES (rule);"""

    )