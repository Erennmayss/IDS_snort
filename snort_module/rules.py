import psycopg2
import re

def fetch_rules_from_db():
    conn = psycopg2.connect(
        dbname="ma_db",
        user="mon_user",
        password="mon_mdp",
        host="localhost",
        port=5432
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, value FROM rules_table")  # ta table de règles
    rules = cursor.fetchall()

    for r in rules:
        rule_dict = {"id": r[0], "name": r[1], "value": r[2]}
        #add_rule_to_table(rule_dict)  # ajoute directement dans le QTableWidget

    conn.close()
conn = psycopg2.connect(
    host="localhost",
    database="ids_db",
    user="aya",
    password="aya",
    port="5432"
)

cursor = conn.cursor()
cursor.execute("SELECT rule FROM regles")
rules = cursor.fetchall()
print(rules)