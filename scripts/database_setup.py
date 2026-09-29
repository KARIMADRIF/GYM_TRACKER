"""
database_setup.py
-------------------
Exécute le script SQL (database_setup.sql) pour créer la base de données
SQLite du projet Smart Gym Tracker.

Usage:
    python scripts/database_setup.py
"""

import sqlite3
from pathlib import Path

# Chemins relatifs à la racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "gym_data.db"
SQL_PATH = BASE_DIR / "scripts" / "database_setup.sql"


def create_database():
    """Crée (ou recrée) la base de données à partir du script SQL."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
        conn.executescript(sql_script)
        conn.commit()
        print(f"✅ Base de données créée avec succès : {DB_PATH}")

        # Vérification rapide des tables créées
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]
        print(f"📋 Tables créées : {tables}")

    except Exception as e:
        print(f"❌ Erreur lors de la création de la base : {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_database()
