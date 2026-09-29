"""
analytics_acp.py
-------------------
Étape 3 du projet Smart Gym Tracker :
    - Extraction des données depuis SQLite vers Pandas
    - Nettoyage & Feature Engineering
    - Analyse exploratoire (EDA)
    - ACP (Analyse en Composantes Principales)

Usage:
    python scripts/analytics_acp.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # pas d'affichage interactif, on sauvegarde les figures
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "gym_data.db"
FIG_DIR = BASE_DIR / "data" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")


# ------------------------------------------------------------------
# 1. Extraction des données (SQL -> Pandas)
# ------------------------------------------------------------------
def extraire_donnees():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        u.id AS user_id,
        u.age,
        u.genre,
        u.niveau_initial,
        u.objectif,
        u.date_inscription,
        s.id AS seance_id,
        s.date_seance,
        s.duree_minutes,
        s.calories_brulees,
        s.frequence_cardiaque_moy,
        e.nom AS exercice,
        e.groupe_musculaire,
        e.type AS type_exercice,
        p.poids_kg,
        p.repetitions,
        p.sets
    FROM Performances p
    JOIN Seances s   ON p.seance_id = s.id
    JOIN Users u     ON s.user_id = u.id
    JOIN Exercices e ON p.exercice_id = e.id
    """
    df = pd.read_sql_query(query, conn, parse_dates=["date_seance", "date_inscription"])
    conn.close()
    return df


# ------------------------------------------------------------------
# 2. Nettoyage & Feature Engineering
# ------------------------------------------------------------------
def nettoyer_et_enrichir(df):
    # Valeurs manquantes / aberrantes
    print(f"Valeurs manquantes par colonne :\n{df.isna().sum()[df.isna().sum() > 0]}\n")
    df = df.dropna(subset=["poids_kg", "repetitions", "sets"])

    # Volume soulevé (indicateur clé en musculation)
    df["volume"] = df["poids_kg"] * df["repetitions"] * df["sets"]

    # Ancienneté de l'utilisateur au moment de la séance (en jours)
    df["anciennete_jours"] = (df["date_seance"] - df["date_inscription"]).dt.days

    return df


def construire_dataset_utilisateur(df):
    """
    Agrège les données au niveau utilisateur pour l'EDA et l'ACP.
    Chaque ligne = un profil résumé d'utilisateur.
    """
    agg = df.groupby("user_id").agg(
        age=("age", "first"),
        niveau_initial=("niveau_initial", "first"),
        objectif=("objectif", "first"),
        nb_seances=("seance_id", "nunique"),
        duree_moy=("duree_minutes", "mean"),
        calories_moy=("calories_brulees", "mean"),
        fc_moy=("frequence_cardiaque_moy", "mean"),
        volume_moy=("volume", "mean"),
        volume_total=("volume", "sum"),
        poids_max=("poids_kg", "max"),
        anciennete_max=("anciennete_jours", "max"),
    ).reset_index()

    # Régularité approximative : nb séances / semaines d'ancienneté
    agg["seances_par_semaine"] = agg["nb_seances"] / (agg["anciennete_max"] / 7).replace(0, np.nan)
    agg["seances_par_semaine"] = agg["seances_par_semaine"].fillna(0)

    return agg


# ------------------------------------------------------------------
# 3. Analyse exploratoire (EDA)
# ------------------------------------------------------------------
def analyse_exploratoire(df, df_users):
    print("=== Statistiques descriptives (niveau séance/performance) ===")
    print(df[["poids_kg", "repetitions", "sets", "volume", "calories_brulees"]].describe())
    print()

    print("=== Moyennes par niveau initial ===")
    print(df_users.groupby("niveau_initial")[["volume_moy", "nb_seances", "seances_par_semaine"]].mean())
    print()

    # Figure 1 : distribution du volume par niveau
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df_users, x="niveau_initial", y="volume_moy",
                order=["Débutant", "Intermédiaire", "Avancé"])
    plt.title("Volume moyen soulevé par niveau initial")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "volume_par_niveau.png", dpi=120)
    plt.close()

    # Figure 2 : répartition des séances par groupe musculaire
    plt.figure(figsize=(9, 5))
    df["groupe_musculaire"].value_counts().plot(kind="bar", color="#2E5E4E")
    plt.title("Nombre de performances par groupe musculaire")
    plt.ylabel("Nombre d'occurrences")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "groupe_musculaire.png", dpi=120)
    plt.close()

    # Figure 3 : corrélations entre variables numériques (niveau utilisateur)
    plt.figure(figsize=(8, 6))
    num_cols = ["age", "nb_seances", "duree_moy", "calories_moy", "fc_moy",
                "volume_moy", "poids_max", "seances_par_semaine"]
    sns.heatmap(df_users[num_cols].corr(), annot=True, fmt=".2f", cmap="RdYlGn", center=0)
    plt.title("Matrice de corrélation - profils utilisateurs")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "correlation_matrix.png", dpi=120)
    plt.close()

    print(f"📊 Figures EDA sauvegardées dans : {FIG_DIR}")


# ------------------------------------------------------------------
# 4. ACP (Analyse en Composantes Principales)
# ------------------------------------------------------------------
def appliquer_acp(df_users):
    features = ["age", "nb_seances", "duree_moy", "calories_moy", "fc_moy",
                "volume_moy", "poids_max", "seances_par_semaine"]

    X = df_users[features].fillna(0)

    # Standardisation (indispensable avant ACP)
    X_scaled = StandardScaler().fit_transform(X)

    pca = PCA(n_components=2)
    composantes = pca.fit_transform(X_scaled)

    df_users["PC1"] = composantes[:, 0]
    df_users["PC2"] = composantes[:, 1]

    variance_expliquee = pca.explained_variance_ratio_
    print("=== ACP ===")
    print(f"Variance expliquée par PC1 : {variance_expliquee[0]:.2%}")
    print(f"Variance expliquée par PC2 : {variance_expliquee[1]:.2%}")
    print(f"Variance totale expliquée (2 composantes) : {sum(variance_expliquee):.2%}\n")

    # Contribution des variables à chaque composante
    loadings = pd.DataFrame(
        pca.components_.T, columns=["PC1", "PC2"], index=features
    ).sort_values("PC1", ascending=False)
    print("=== Contribution des variables (loadings) ===")
    print(loadings)
    print()

    # Visualisation : projection des utilisateurs dans l'espace ACP
    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=df_users, x="PC1", y="PC2",
        hue="niveau_initial", style="objectif",
        palette={"Débutant": "#4CAF50", "Intermédiaire": "#FF9800", "Avancé": "#C62828"},
        s=80, alpha=0.8,
    )
    plt.title("Projection ACP des profils utilisateurs")
    plt.xlabel(f"PC1 ({variance_expliquee[0]:.1%} de variance)")
    plt.ylabel(f"PC2 ({variance_expliquee[1]:.1%} de variance)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "acp_projection.png", dpi=120)
    plt.close()

    print(f"📊 Figure ACP sauvegardée dans : {FIG_DIR / 'acp_projection.png'}")

    return df_users, pca, loadings


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    print("🔄 Extraction des données...")
    df = extraire_donnees()
    print(f"   {len(df)} lignes extraites (Performances x Séances x Users x Exercices)\n")

    print("🧹 Nettoyage & Feature Engineering...")
    df = nettoyer_et_enrichir(df)
    df_users = construire_dataset_utilisateur(df)
    print(f"   {len(df_users)} profils utilisateurs agrégés\n")

    print("📈 Analyse exploratoire...")
    analyse_exploratoire(df, df_users)
    print()

    print("🧮 Application de l'ACP...")
    df_users, pca, loadings = appliquer_acp(df_users)

    # Sauvegarde du dataset enrichi pour l'étape suivante (ML)
    output_path = BASE_DIR / "data" / "users_features.csv"
    df_users.to_csv(output_path, index=False)
    print(f"\n💾 Dataset utilisateurs (avec PC1/PC2) sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
