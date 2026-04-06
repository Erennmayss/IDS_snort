import psycopg2
import re
import sys
import os

# Ajout du chemin pour trouver db_connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db_connection import connect_db


def afficher_db():
    """Récupère toutes les règles de la BDD"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT sid, rule FROM regles ORDER BY sid;")
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        print(f"❌ Erreur lors de la lecture des règles : {e}")
        return []
    finally:
        conn.close()


def ajouter_regle(line):
    """Parse et ajoute une règle Snort à la BDD"""
    conn = connect_db()
    if conn is None:
        return

    try:
        # Parsing de la règle
        parts = line.split()
        action = parts[0]
        protocol = parts[1]
        src_ip = parts[2]
        src_port = parts[3]
        dst_ip = parts[5]
        dst_port = parts[6]

        msg = re.search(r'msg:"(.*?)"', line)
        sid_match = re.search(r'sid:(\d+)', line)

        message = msg.group(1) if msg else ""
        sid = sid_match.group(1) if sid_match else None

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO regles 
                (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, rule)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sid) DO NOTHING
                """,
                (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line)
            )
            conn.commit()
            print(f"✅ Règle {sid} ajoutée.")
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout : {e}")
    finally:
        conn.close()


def modifier_regle(first_sid, line):
    """Met à jour une règle existante"""
    conn = connect_db()
    if conn is None:
        return

    try:
        parts = line.split()
        action = parts[0]
        protocol = parts[1]
        src_ip = parts[2]
        src_port = parts[3]
        dst_ip = parts[5]
        dst_port = parts[6]

        msg = re.search(r'msg:"(.*?)"', line)
        message = msg.group(1) if msg else ""

        # Forcer le SID original dans la règle texte pour éviter les incohérences
        if f"sid:{first_sid}" not in line:
            line = re.sub(r'sid:\d+', f'sid:{first_sid}', line)

        with conn.cursor() as cursor:
            # Vérifier si l'enregistrement existe
            cursor.execute("SELECT COUNT(*) FROM regles WHERE sid = %s", (first_sid,))
            if cursor.fetchone()[0] == 0:
                # INSERT
                cursor.execute(
                    """
                    INSERT INTO regles (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, rule)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (first_sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line)
                )
            else:
                # UPDATE
                cursor.execute(
                    """
                    UPDATE regles
                    SET message = %s, protocol = %s, src_ip = %s, src_port = %s, 
                        dst_ip = %s, dst_port = %s, action = %s, rule = %s
                    WHERE sid = %s
                    """,
                    (message, protocol, src_ip, src_port, dst_ip, dst_port, action, line, first_sid)
                )
            conn.commit()
            print(f"✅ Règle {first_sid} modifiée.")
    except Exception as e:
        print(f"❌ Erreur lors de la modification : {e}")
    finally:
        conn.close()


def supprimer_regle(sid):
    """Supprime une règle par son SID"""
    conn = connect_db()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM regles WHERE sid = %s", (sid,))
            conn.commit()
            print(f"🗑️ Règle {sid} supprimée.")
    except Exception as e:
        print(f"❌ Erreur suppression : {e}")
    finally:
        conn.close()


def reset_db():
    """Vide la table des règles"""
    conn = connect_db()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE regles;")
            conn.commit()
            print("🧹 Base de données des règles réinitialisée.")
    except Exception as e:
        print(f"❌ Erreur reset : {e}")
    finally:
        conn.close()