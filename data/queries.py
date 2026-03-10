import psycopg2
import db_connection
from data.db_connection import connect_db


def fetch_rules_from_db(interface):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT sid,rule FROM regles")  # ta table de règles
    rules = cursor.fetchall()
    print(rules)

    for r in rules:
        interface.add_rule_to_table(r[1],r[0])  # ajoute directement dans le QTableWidget

    conn.close()
