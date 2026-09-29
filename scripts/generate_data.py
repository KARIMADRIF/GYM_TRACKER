"""
generate_data.py
-------------------
Génère des données synthétiques réalistes pour le projet Smart Gym Tracker
et les insère dans la base de données SQLite (gym_data.db).

Simule :
    - 80 utilisateurs avec profils variés (âge, niveau, objectif)
    - 6 à 12 mois d'historique d'entraînement par utilisateur
    - Progression réaliste : montée graduelle, plateaux, interruptions/reprises

Usage:
    python scripts/generate_data.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
from faker import Faker

fake = Faker("fr_FR")
random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "gym_data.db"

N_USERS = 80
MIN_MONTHS, MAX_MONTHS = 6, 12
END_DATE = date(2026, 8, 1)

# ------------------------------------------------------------------
# Référentiel des exercices
# ------------------------------------------------------------------
EXERCICES = [
    ("Développé couché", "Pectoraux", "Force"),
    ("Squat", "Jambes", "Force"),
    ("Soulevé de terre", "Dos", "Force"),
    ("Tractions", "Dos", "Force"),
    ("Développé militaire", "Épaules", "Force"),
    ("Curl biceps", "Bras", "Force"),
    ("Extension triceps", "Bras", "Force"),
    ("Presse à cuisses", "Jambes", "Force"),
    ("Rowing barre", "Dos", "Force"),
    ("Fentes", "Jambes", "Force"),
    ("Course à pied", "Cardio", "Cardio"),
    ("Vélo elliptique", "Cardio", "Cardio"),
    ("Rameur", "Cardio", "Cardio"),
    ("Corde à sauter", "Cardio", "Cardio"),
    ("Étirements dynamiques", "Full body", "Mobilité"),
    ("Mobilité hanches", "Hanches", "Mobilité"),
]

NIVEAUX = ["Débutant", "Intermédiaire", "Avancé"]
OBJECTIFS = ["Prise de masse", "Perte de poids", "Force", "Endurance", "Maintien"]

# Poids de départ approximatifs par exercice de force (kg), utilisés comme base
POIDS_BASE = {
    "Développé couché": 30, "Squat": 40, "Soulevé de terre": 45,
    "Tractions": 0, "Développé militaire": 20, "Curl biceps": 8,
    "Extension triceps": 10, "Presse à cuisses": 60, "Rowing barre": 25,
    "Fentes": 15,
}

FORCE_EXOS = [e for e in EXERCICES if e[2] == "Force"]
CARDIO_EXOS = [e for e in EXERCICES if e[2] == "Cardio"]
MOBILITE_EXOS = [e for e in EXERCICES if e[2] == "Mobilité"]


# ------------------------------------------------------------------
# Génération des utilisateurs
# ------------------------------------------------------------------
def generer_utilisateurs(n):
    utilisateurs = []
    for i in range(n):
        niveau = random.choices(NIVEAUX, weights=[0.45, 0.35, 0.20])[0]
        duree_mois = random.randint(MIN_MONTHS, MAX_MONTHS)
        date_inscription = END_DATE - timedelta(days=duree_mois * 30)

        utilisateurs.append({
            "nom": fake.name(),
            "age": random.randint(16, 65),
            "genre": random.choice(["H", "F"]),
            "niveau_initial": niveau,
            "objectif": random.choice(OBJECTIFS),
            "date_inscription": date_inscription.isoformat(),
            # attributs internes pour la simulation (non stockés en DB)
            "_duree_mois": duree_mois,
            "_regularite": random.choice(["régulier", "irrégulier", "sporadique"]),
        })
    return utilisateurs


# ------------------------------------------------------------------
# Génération des séances + performances pour un utilisateur
# ------------------------------------------------------------------
def generer_seances_et_performances(user_id, user):
    """
    Simule un historique réaliste :
      - fréquence d'entraînement selon la régularité du profil
      - progression du poids soulevé avec plateaux occasionnels
      - interruptions (pause de 2 à 5 semaines) pour les profils irréguliers/sporadiques
    """
    seances = []
    performances = []

    date_debut = date.fromisoformat(user["date_inscription"])
    nb_semaines = user["_duree_mois"] * 4

    freq_par_semaine = {
        "régulier": (3, 5),
        "irrégulier": (1, 3),
        "sporadique": (0, 2),
    }[user["_regularite"]]

    # Facteur de progression selon le niveau initial (les débutants progressent plus vite)
    facteur_progression = {"Débutant": 1.4, "Intermédiaire": 1.0, "Avancé": 0.5}[user["niveau_initial"]]

    # Poids courant par exercice de force (état de progression)
    poids_courant = {
        nom: POIDS_BASE[nom] * random.uniform(0.7, 1.3) * (
            1.0 if user["niveau_initial"] == "Débutant" else
            1.5 if user["niveau_initial"] == "Intermédiaire" else 2.2
        )
        for nom, _, _ in FORCE_EXOS
    }

    en_pause = False
    semaines_pause_restantes = 0

    for semaine in range(nb_semaines):
        # Gestion des interruptions (uniquement pour profils non réguliers)
        if user["_regularite"] != "régulier" and not en_pause and random.random() < 0.08:
            en_pause = True
            semaines_pause_restantes = random.randint(2, 5)

        if en_pause:
            semaines_pause_restantes -= 1
            if semaines_pause_restantes <= 0:
                en_pause = False
            continue

        nb_seances_semaine = random.randint(*freq_par_semaine)

        for _ in range(nb_seances_semaine):
            jour_offset = semaine * 7 + random.randint(0, 6)
            date_seance = date_debut + timedelta(days=jour_offset)
            if date_seance > END_DATE:
                continue

            duree = random.randint(35, 90)
            fc_moy = random.randint(110, 175)
            calories = round(duree * random.uniform(6.5, 11.5), 1)

            seances.append({
                "user_id": user_id,
                "date_seance": date_seance.isoformat(),
                "duree_minutes": duree,
                "calories_brulees": calories,
                "frequence_cardiaque_moy": fc_moy,
            })
            seance_index = len(seances) - 1  # position temporaire (sera remappée après insertion)

            # Choix des exercices de la séance (mix force + un peu de cardio/mobilité)
            nb_exos_force = random.randint(2, 4)
            exos_force_choisis = random.sample(FORCE_EXOS, k=nb_exos_force)

            for nom, groupe, typ in exos_force_choisis:
                # Progression légère à chaque séance + bruit aléatoire + plateau occasionnel
                if random.random() < 0.15:
                    progression = 0  # plateau
                else:
                    progression = random.uniform(0.1, 0.6) * facteur_progression
                poids_courant[nom] = max(0, poids_courant[nom] + progression)
                poids_final = round(poids_courant[nom] * random.uniform(0.95, 1.05), 1)

                performances.append({
                    "_seance_index": seance_index,
                    "exercice_nom": nom,
                    "poids_kg": poids_final,
                    "repetitions": random.randint(6, 15),
                    "sets": random.randint(3, 5),
                })

            if random.random() < 0.4:
                nom, groupe, typ = random.choice(CARDIO_EXOS)
                performances.append({
                    "_seance_index": seance_index,
                    "exercice_nom": nom,
                    "poids_kg": 0,
                    "repetitions": 1,
                    "sets": 1,
                })

    return seances, performances


# ------------------------------------------------------------------
# Insertion en base de données
# ------------------------------------------------------------------
def inserer_donnees(conn, utilisateurs):
    cur = conn.cursor()

    # 1. Exercices (référentiel fixe)
    cur.executemany(
        "INSERT INTO Exercices (nom, groupe_musculaire, type) VALUES (?, ?, ?)",
        EXERCICES,
    )
    conn.commit()

    # Récupération des id d'exercices générés
    cur.execute("SELECT id, nom FROM Exercices")
    exercice_id_par_nom = {nom: eid for eid, nom in cur.fetchall()}

    total_seances, total_perfs = 0, 0

    for user in utilisateurs:
        cur.execute(
            """INSERT INTO Users (nom, age, genre, niveau_initial, objectif, date_inscription)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user["nom"], user["age"], user["genre"], user["niveau_initial"],
             user["objectif"], user["date_inscription"]),
        )
        user_id = cur.lastrowid

        seances, performances = generer_seances_et_performances(user_id, user)

        # Insertion des séances, une par une pour récupérer leur id réel
        seance_ids = []
        for s in seances:
            cur.execute(
                """INSERT INTO Seances (user_id, date_seance, duree_minutes, calories_brulees, frequence_cardiaque_moy)
                   VALUES (?, ?, ?, ?, ?)""",
                (s["user_id"], s["date_seance"], s["duree_minutes"],
                 s["calories_brulees"], s["frequence_cardiaque_moy"]),
            )
            seance_ids.append(cur.lastrowid)

        # Insertion des performances, en remappant l'index temporaire vers le vrai seance_id
        perf_rows = [
            (
                seance_ids[p["_seance_index"]],
                exercice_id_par_nom[p["exercice_nom"]],
                p["poids_kg"],
                p["repetitions"],
                p["sets"],
            )
            for p in performances
        ]
        cur.executemany(
            """INSERT INTO Performances (seance_id, exercice_id, poids_kg, repetitions, sets)
               VALUES (?, ?, ?, ?, ?)""",
            perf_rows,
        )

        total_seances += len(seances)
        total_perfs += len(performances)

    conn.commit()
    return total_seances, total_perfs


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Base introuvable : {DB_PATH}\n"
            "Lance d'abord : python scripts/database_setup.py"
        )

    conn = sqlite3.connect(DB_PATH)

    # Reset des données (garde le schéma, vide les tables)
    cur = conn.cursor()
    for table in ["Performances", "Seances", "Exercices", "Users"]:
        cur.execute(f"DELETE FROM {table}")
    conn.commit()

    utilisateurs = generer_utilisateurs(N_USERS)
    total_seances, total_perfs = inserer_donnees(conn, utilisateurs)

    print(f"✅ {N_USERS} utilisateurs générés")
    print(f"✅ {total_seances} séances générées")
    print(f"✅ {total_perfs} lignes de performance générées")
    print(f"📦 Base de données : {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
