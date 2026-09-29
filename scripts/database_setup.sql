-- ============================================================
-- Smart Gym Tracker & Performance Analytics Platform
-- Script de création de la base de données (SQLite)
-- Auteur : Karima Drif
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. TABLE Users
-- ============================================================
DROP TABLE IF EXISTS Users;
CREATE TABLE Users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                 TEXT NOT NULL,
    age                 INTEGER NOT NULL CHECK (age BETWEEN 14 AND 80),
    genre               TEXT NOT NULL CHECK (genre IN ('H', 'F')),
    niveau_initial      TEXT NOT NULL CHECK (niveau_initial IN ('Débutant', 'Intermédiaire', 'Avancé')),
    objectif            TEXT NOT NULL CHECK (objectif IN ('Prise de masse', 'Perte de poids', 'Force', 'Endurance', 'Maintien')),
    date_inscription    DATE NOT NULL
);

-- ============================================================
-- 2. TABLE Exercices
-- ============================================================
DROP TABLE IF EXISTS Exercices;
CREATE TABLE Exercices (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                 TEXT NOT NULL UNIQUE,
    groupe_musculaire   TEXT NOT NULL,
    type                TEXT NOT NULL CHECK (type IN ('Force', 'Cardio', 'Mobilité'))
);

-- ============================================================
-- 3. TABLE Seances
-- ============================================================
DROP TABLE IF EXISTS Seances;
CREATE TABLE Seances (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                     INTEGER NOT NULL,
    date_seance                 DATE NOT NULL,
    duree_minutes               INTEGER CHECK (duree_minutes > 0),
    calories_brulees            REAL CHECK (calories_brulees >= 0),
    frequence_cardiaque_moy     INTEGER CHECK (frequence_cardiaque_moy BETWEEN 40 AND 220),
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- ============================================================
-- 4. TABLE Performances
-- ============================================================
DROP TABLE IF EXISTS Performances;
CREATE TABLE Performances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seance_id       INTEGER NOT NULL,
    exercice_id     INTEGER NOT NULL,
    poids_kg        REAL CHECK (poids_kg >= 0),
    repetitions     INTEGER CHECK (repetitions > 0),
    sets            INTEGER CHECK (sets > 0),
    FOREIGN KEY (seance_id) REFERENCES Seances(id) ON DELETE CASCADE,
    FOREIGN KEY (exercice_id) REFERENCES Exercices(id) ON DELETE RESTRICT
);

-- ============================================================
-- 5. INDEX (optimisation des requêtes fréquentes)
-- ============================================================
CREATE INDEX idx_seances_user       ON Seances(user_id);
CREATE INDEX idx_seances_date       ON Seances(date_seance);
CREATE INDEX idx_perf_seance        ON Performances(seance_id);
CREATE INDEX idx_perf_exercice      ON Performances(exercice_id);

-- ============================================================
-- 6. REQUÊTES AVANCÉES (Window Functions)
--    Utiles plus tard pour l'analyse (Étape 3) et le dashboard
-- ============================================================

-- 6.1 Évolution du poids soulevé par utilisateur et par exercice
-- (comparaison avec la séance précédente grâce à LAG())
-- SELECT
--     u.nom,
--     e.nom AS exercice,
--     s.date_seance,
--     p.poids_kg,
--     LAG(p.poids_kg) OVER (
--         PARTITION BY s.user_id, p.exercice_id
--         ORDER BY s.date_seance
--     ) AS poids_precedent,
--     p.poids_kg - LAG(p.poids_kg) OVER (
--         PARTITION BY s.user_id, p.exercice_id
--         ORDER BY s.date_seance
--     ) AS progression
-- FROM Performances p
-- JOIN Seances s   ON p.seance_id = s.id
-- JOIN Users u     ON s.user_id = u.id
-- JOIN Exercices e ON p.exercice_id = e.id
-- ORDER BY u.nom, e.nom, s.date_seance;

-- 6.2 Moyenne mobile des calories brûlées (fenêtre glissante 5 séances)
-- SELECT
--     user_id,
--     date_seance,
--     calories_brulees,
--     AVG(calories_brulees) OVER (
--         PARTITION BY user_id
--         ORDER BY date_seance
--         ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
--     ) AS moyenne_mobile_calories
-- FROM Seances
-- ORDER BY user_id, date_seance;

-- 6.3 Classement des utilisateurs par volume total soulevé (poids x reps x sets)
-- SELECT
--     u.nom,
--     SUM(p.poids_kg * p.repetitions * p.sets) AS volume_total,
--     RANK() OVER (ORDER BY SUM(p.poids_kg * p.repetitions * p.sets) DESC) AS classement
-- FROM Performances p
-- JOIN Seances s ON p.seance_id = s.id
-- JOIN Users u   ON s.user_id = u.id
-- GROUP BY u.id;
