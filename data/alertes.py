# data/alerts_db.py
import psycopg2
import sys
import os

# Ajout du chemin pour trouver db_connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.db_connection import connect_db


def get_attack_types():
    """Récupère tous les types d'attaque distincts de la BDD"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT attack_type FROM security_alerts ORDER BY attack_type")
            rows = cursor.fetchall()
            return [str(row[0]) for row in rows if row[0]]
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des types d'attaque : {e}")
        return []
    finally:
        conn.close()


def get_snort_alerts(filters=None):
    """
    Récupère les alertes Snort filtrées de la BDD

    Args:
        filters (dict): Dictionnaire contenant les filtres
            - date (str): Date au format YYYY-MM-DD
            - severity (str): Niveau de gravité
            - attack_type (str): Type d'attaque
            - ip_search (str): Recherche IP

    Returns:
        list: Liste des alertes Snort
    """
    conn = connect_db()
    if conn is None:
        return []

    filters = filters or {}

    try:
        with conn.cursor() as cursor:
            # Construction de la requête avec les filtres
            query = """
            SELECT timestamp, source_ip, destination_ip, attack_type, severity
            FROM security_alerts
            WHERE detection_engine = 'snort'
            """
            params = []

            # Filtre date
            if filters.get('date'):
                query += " AND DATE(timestamp) = %s"
                params.append(filters['date'])

            # Filtre gravité
            if filters.get('severity') and filters['severity'] != "Toutes":
                query += " AND severity = %s"
                params.append(filters['severity'])

            # Filtre type d'attaque
            if filters.get('attack_type') and filters['attack_type'] != "Tous":
                query += " AND attack_type = %s"
                params.append(filters['attack_type'])

            # Filtre recherche IP
            if filters.get('ip_search'):
                ip_pattern = f"%{filters['ip_search']}%"
                query += " AND (source_ip LIKE %s OR destination_ip LIKE %s)"
                params.extend([ip_pattern, ip_pattern])

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            snort_data = []
            for row in rows:
                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                src = row[1]
                dst = row[2]
                attack = row[3]
                severity = row[4]
                snort_data.append([date, src, dst, attack, severity])

            return snort_data

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes Snort : {e}")
        return []
    finally:
        conn.close()


def get_snort_alerts_count(filters=None):
    """Récupère le nombre d'alertes Snort avec les filtres"""
    conn = connect_db()
    if conn is None:
        return 0

    filters = filters or {}

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT COUNT(*)
            FROM security_alerts
            WHERE detection_engine = 'snort'
            """
            params = []

            if filters.get('date'):
                query += " AND DATE(timestamp) = %s"
                params.append(filters['date'])

            if filters.get('severity') and filters['severity'] != "Toutes":
                query += " AND severity = %s"
                params.append(filters['severity'])

            if filters.get('attack_type') and filters['attack_type'] != "Tous":
                query += " AND attack_type = %s"
                params.append(filters['attack_type'])

            if filters.get('ip_search'):
                ip_pattern = f"%{filters['ip_search']}%"
                query += " AND (source_ip LIKE %s OR destination_ip LIKE %s)"
                params.extend([ip_pattern, ip_pattern])

            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else 0

    except Exception as e:
        print(f"❌ Erreur lors du comptage des alertes Snort : {e}")
        return 0
    finally:
        conn.close()


def get_all_alerts(filters=None):
    """
    Récupère toutes les alertes (Snort + ML) avec filtres

    Args:
        filters (dict): Dictionnaire contenant les filtres

    Returns:
        tuple: (ml_data, snort_data) - listes d'alertes
    """
    conn = connect_db()
    if conn is None:
        return [], []

    filters = filters or {}

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT timestamp, source_ip, destination_ip, attack_type, severity, detection_engine
            FROM security_alerts
            WHERE 1=1
            """
            params = []

            if filters.get('date'):
                query += " AND DATE(timestamp) = %s"
                params.append(filters['date'])

            if filters.get('severity') and filters['severity'] != "Toutes":
                query += " AND severity = %s"
                params.append(filters['severity'])

            if filters.get('attack_type') and filters['attack_type'] != "Tous":
                query += " AND attack_type = %s"
                params.append(filters['attack_type'])

            if filters.get('ip_search'):
                ip_pattern = f"%{filters['ip_search']}%"
                query += " AND (source_ip LIKE %s OR destination_ip LIKE %s)"
                params.extend([ip_pattern, ip_pattern])

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            ml_data = []
            snort_data = []

            for row in rows:
                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                src = row[1]
                dst = row[2]
                attack = row[3]
                severity = row[4]
                engine = row[5]

                alert = [date, src, dst, attack, severity]

                if engine and engine.lower() == "ml":
                    ml_data.append(alert)
                elif engine and engine.lower() == "snort":
                    snort_data.append(alert)

            return ml_data, snort_data

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes : {e}")
        return [], []
    finally:
        conn.close()


def get_alerts_by_severity(filters=None):
    """Récupère le nombre d'alertes par niveau de gravité (uniquement Snort)"""
    conn = connect_db()
    if conn is None:
        return {}

    filters = filters or {}

    try:
        with conn.cursor() as cursor:
            query = """
            SELECT severity, COUNT(*)
            FROM security_alerts
            WHERE detection_engine = 'snort'
            """
            params = []

            if filters.get('date'):
                query += " AND DATE(timestamp) = %s"
                params.append(filters['date'])

            if filters.get('attack_type') and filters['attack_type'] != "Tous":
                query += " AND attack_type = %s"
                params.append(filters['attack_type'])

            if filters.get('ip_search'):
                ip_pattern = f"%{filters['ip_search']}%"
                query += " AND (source_ip LIKE %s OR destination_ip LIKE %s)"
                params.extend([ip_pattern, ip_pattern])

            query += " GROUP BY severity"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                severity = row[0]
                count = row[1]
                result[severity] = count

            return result

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes par gravité : {e}")
        return {}
    finally:
        conn.close()


def get_recent_snort_alerts(limit=50):
    """Récupère les alertes Snort les plus récentes"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, source_ip, destination_ip, attack_type, severity
                FROM security_alerts
                WHERE detection_engine = 'snort'
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

            alerts = []
            for row in rows:
                alerts.append({
                    'timestamp': row[0].strftime("%d/%m/%Y %H:%M:%S"),
                    'source_ip': row[1],
                    'destination_ip': row[2],
                    'attack_type': row[3],
                    'severity': row[4]
                })

            return alerts

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes récentes : {e}")
        return []
    finally:
        conn.close()


def get_snort_alerts_by_ip(ip, limit=100):
    """Récupère les alertes Snort associées à une IP spécifique"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, source_ip, destination_ip, attack_type, severity
                FROM security_alerts
                WHERE detection_engine = 'snort'
                AND (source_ip = %s OR destination_ip = %s)
                ORDER BY timestamp DESC
                LIMIT %s
            """, (ip, ip, limit))
            rows = cursor.fetchall()

            alerts = []
            for row in rows:
                alerts.append({
                    'timestamp': row[0].strftime("%d/%m/%Y %H:%M:%S"),
                    'source_ip': row[1],
                    'destination_ip': row[2],
                    'attack_type': row[3],
                    'severity': row[4]
                })

            return alerts

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes par IP : {e}")
        return []
    finally:
        conn.close()


def get_snort_alerts_by_date_range(start_date, end_date):
    """Récupère les alertes Snort sur une période donnée"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, source_ip, destination_ip, attack_type, severity
                FROM security_alerts
                WHERE detection_engine = 'snort'
                AND DATE(timestamp) BETWEEN %s AND %s
                ORDER BY timestamp DESC
            """, (start_date, end_date))
            rows = cursor.fetchall()

            alerts = []
            for row in rows:
                date = row[0].strftime("%d/%m/%Y %H:%M:%S")
                alerts.append([date, row[1], row[2], row[3], row[4]])

            return alerts

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des alertes par période : {e}")
        return []
    finally:
        conn.close()


def get_top_attack_types_snort(limit=5):
    """Récupère les types d'attaque Snort les plus fréquents"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT attack_type, COUNT(*) as count
                FROM security_alerts
                WHERE detection_engine = 'snort'
                GROUP BY attack_type
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

            return [(row[0], row[1]) for row in rows if row[0]]

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des types d'attaque : {e}")
        return []
    finally:
        conn.close()


def get_top_source_ips_snort(limit=5):
    """Récupère les IP sources Snort les plus actives"""
    conn = connect_db()
    if conn is None:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT source_ip, COUNT(*) as count
                FROM security_alerts
                WHERE detection_engine = 'snort'
                GROUP BY source_ip
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

            return [(row[0], row[1]) for row in rows if row[0]]

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des IP sources : {e}")
        return []
    finally:
        conn.close()


def add_alert(timestamp, source_ip, destination_ip, attack_type, severity, detection_engine):
    """Ajoute une nouvelle alerte dans la BDD"""
    conn = connect_db()
    if conn is None:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO security_alerts 
                (timestamp, source_ip, destination_ip, attack_type, severity, detection_engine)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (timestamp, source_ip, destination_ip, attack_type, severity, detection_engine))
            conn.commit()
            print(f"✅ Alerte ajoutée : {attack_type} depuis {source_ip}")
            return True
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de l'alerte : {e}")
        return False
    finally:
        conn.close()


def delete_old_alerts(days=30):
    """Supprime les alertes plus anciennes que X jours"""
    conn = connect_db()
    if conn is None:
        return 0

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM security_alerts
                WHERE timestamp < NOW() - INTERVAL '%s days'
            """, (days,))
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"🗑️ {deleted_count} alertes supprimées (plus de {days} jours)")
            return deleted_count
    except Exception as e:
        print(f"❌ Erreur lors de la suppression des anciennes alertes : {e}")
        return 0
    finally:
        conn.close()


def clear_all_alerts():
    """Supprime toutes les alertes (réinitialisation)"""
    conn = connect_db()
    if conn is None:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE security_alerts;")
            conn.commit()
            print("🧹 Toutes les alertes ont été supprimées.")
    except Exception as e:
        print(f"❌ Erreur lors de la suppression des alertes : {e}")
    finally:
        conn.close()