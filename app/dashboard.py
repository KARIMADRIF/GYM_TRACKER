"""
dashboard.py
-------------------
Smart Gym Tracker — Dashboard interactif Streamlit.
Navigation en haut (onglets), thème marron/or clair, style sportif harmonieux.

Usage:
    streamlit run app/dashboard.py
"""

import time
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import psycopg2
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor

NIVEAUX = ["Débutant", "Intermédiaire", "Avancé"]
OBJECTIFS = ["Prise de masse", "Perte de poids", "Force", "Endurance", "Maintien"]

# Catalogue de référence des exercices (données de référence, pas des données utilisateur fictives)
EXERCICES_CATALOGUE = [
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


def get_write_connection():
    """Ouvre une connexion PostgreSQL (Supabase) à partir des secrets Streamlit."""
    pg = st.secrets["postgres"]
    return psycopg2.connect(
        host=pg["host"],
        port=pg["port"],
        dbname=pg["dbname"],
        user=pg["user"],
        password=pg["password"],
    )


def assurer_base():
    """Crée le schéma PostgreSQL s'il n'existe pas encore (idempotent)."""
    conn = get_write_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL,
            age INTEGER NOT NULL,
            genre TEXT NOT NULL,
            niveau_initial TEXT NOT NULL,
            objectif TEXT NOT NULL,
            date_inscription DATE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Exercices (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL UNIQUE,
            groupe_musculaire TEXT NOT NULL,
            type TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Seances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
            date_seance DATE NOT NULL,
            duree_minutes INTEGER,
            calories_brulees REAL,
            frequence_cardiaque_moy INTEGER
        );
        CREATE TABLE IF NOT EXISTS Performances (
            id SERIAL PRIMARY KEY,
            seance_id INTEGER NOT NULL REFERENCES Seances(id) ON DELETE CASCADE,
            exercice_id INTEGER NOT NULL REFERENCES Exercices(id) ON DELETE RESTRICT,
            poids_kg REAL,
            repetitions INTEGER,
            sets INTEGER
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def assurer_referentiel_exercices():
    """Seede le catalogue d'exercices s'il est vide (référentiel, pas des données factices)."""
    conn = get_write_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Exercices")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO Exercices (nom, groupe_musculaire, type) VALUES (%s, %s, %s)",
            EXERCICES_CATALOGUE,
        )
        conn.commit()
    cur.close()
    conn.close()


st.set_page_config(page_title="Smart Gym Tracker", page_icon="🏋️", layout="wide")

try:
    assurer_base()
    assurer_referentiel_exercices()
except Exception as e:
    st.error(
        "Impossible de se connecter à la base de données PostgreSQL (Supabase). "
        "Vérifie que le secret `[postgres] url = ...` est bien configuré "
        "(fichier `.streamlit/secrets.toml` en local, ou onglet Secrets sur Streamlit Community Cloud)."
    )
    st.exception(e)
    st.stop()

# ============================================================
# STYLE — marron foncé + or clair, navigation en haut, sans rouge
# ============================================================
BRUN_FONCE = "#17231D"
BRUN_PROFOND = "#0B120E"
OR = "#F0B429"        # or clair / jaune vif (au lieu du rouge par défaut)
OR_DOUX = "#FBE3A1"
NOIR = "#0B120E"
CREME = "#F4F6F0"
VERT = "#247A52"
VERT_CLAIR = "#DDF5D9"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

/* Fond clair forcé (indépendant du thème sombre/clair du navigateur) */
.stApp {{ background-color: {CREME} !important; }}
section.main > div {{ background-color: {CREME} !important; }}
.block-container {{ max-width: 1280px; padding-top: 1.4rem; padding-bottom: 3.5rem; }}

/* En-tête de marque tout en haut — titre et sous-titre resserrés, pas d'espace vide */
.brand-bar {{
    background: linear-gradient(90deg, {BRUN_FONCE}, {BRUN_PROFOND});
    padding: 18px 28px;
    border-radius: 10px;
    border-bottom: 3px solid {OR};
    margin-bottom: 6px;
}}
.brand-bar h1 {{
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 1.5px;
    font-size: 1.9rem;
    color: {OR};
    margin: 0;
    line-height: 1.1;
}}
.brand-bar span {{
    display: block;
    color: #C9B8A6;
    font-size: 0.85rem;
    font-family: 'Inter', sans-serif;
    margin-top: 2px;
}}

/* Titres de page */
.gym-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.1rem;
    letter-spacing: 1.5px;
    color: {BRUN_FONCE};
    margin-bottom: 0.1rem;
}}
.gym-subtitle {{
    font-family: 'Inter', sans-serif;
    color: #A08F7C;
    font-size: 0.92rem;
    margin-bottom: 1.3rem;
}}

/* Hero banner — bandeau riche avec dégradé, glow décoratif et chips de stats */
.hero {{
    background-color: {BRUN_PROFOND};
    background-image: linear-gradient(90deg, rgba(7,16,9,.98) 0%, rgba(7,16,9,.88) 43%, rgba(7,16,9,.18) 100%), url('https://images.pexels.com/photos/1552242/pexels-photo-1552242.jpeg?auto=compress&cs=tinysrgb&w=1800');
    background-size: cover;
    background-position: center;
    border-radius: 22px;
    padding: 48px 46px 38px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 18px 42px rgba(11,18,14,0.24);
}}
.hero::after {{
    content: "";
    position: absolute;
    top: -70px; right: -70px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, rgba(240,180,41,0.28), transparent 70%);
    border-radius: 50%;
}}
.hero::before {{
    content: "";
    position: absolute;
    bottom: -90px; left: 30%;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(240,180,41,0.10), transparent 70%);
    border-radius: 50%;
}}
.hero h1 {{
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 2px;
    font-size: clamp(2.7rem, 5vw, 4.4rem);
    color: {OR};
    margin: 0;
    position: relative;
    z-index: 1;
}}
.hero p.tagline {{
    color: #D6E2D7;
    margin: 8px 0 24px 0;
    font-size: 1rem;
    max-width: 500px;
    position: relative;
    z-index: 1;
}}
.hero-eyebrow {{
    display: inline-flex; align-items: center; gap: 8px; color: {OR};
    letter-spacing: 1.4px; text-transform: uppercase; font-size: .72rem;
    font-weight: 700; margin-bottom: 12px;
}}
.hero-eyebrow::before {{ content: ""; width: 22px; height: 2px; background: {OR}; }}

/* Cartes conteneurs pour les graphiques — profondeur et relief */
.chart-card {{
    background: #FFFFFF;
    border: 1px solid #EEE3D0;
    border-radius: 18px;
    padding: 18px 22px 8px 22px;
    margin-bottom: 22px;
    box-shadow: 0 4px 14px rgba(43,27,18,0.07);
    transition: box-shadow 0.25s ease, transform 0.25s ease;
}}
.section-kicker {{ color: {VERT}; font-size: .72rem; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: .25rem; }}
.welcome-card {{
    background: #FFFFFF; border: 1px solid #E0E9DC; border-radius: 18px; padding: 20px;
    margin: 0 0 18px; box-shadow: 0 8px 24px rgba(24,44,31,.06);
}}
.welcome-card strong {{ color: {BRUN_FONCE}; }}
.chart-card:hover {{
    box-shadow: 0 10px 26px rgba(43,27,18,0.14);
    transform: translateY(-3px);
}}
.chart-card h3 {{
    margin-top: 0;
    border-bottom: 2px solid {OR};
}}

/* Badges de profils (clustering) */
.badges-row {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 4px 0 18px 0;
}}
.profile-badge {{
    padding: 7px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
}}

/* --- Onglets de navigation (en haut) — sans icônes, style net et sobre --- */
div[data-baseweb="tab-list"] {{
    gap: 28px;
    background: #FFFFFF !important;
    border: 1px solid #D9E8D5;
    border-bottom: 3px solid {VERT};
    border-radius: 14px;
    padding: 6px 10px;
    margin: 6px 0 22px;
    box-shadow: 0 6px 18px rgba(24,44,31,.08);
}}
button[data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.92rem;
    letter-spacing: 0.2px;
    color: #506157 !important;
    padding: 10px 16px;
    background: transparent;
    border-radius: 9px;
    transition: background-color 0.2s ease, color 0.2s ease;
}}
button[data-baseweb="tab"]:hover {{
    color: {BRUN_FONCE} !important;
    background-color: {VERT_CLAIR};
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {BRUN_FONCE} !important;
    font-weight: 700;
    background-color: {OR} !important;
}}
button[data-baseweb="tab"] p {{
    font-size: 0.92rem !important;
    color: inherit !important;
}}
/* Barre de soulignement de l'onglet actif : noir au lieu du rouge Streamlit par défaut */
div[data-baseweb="tab-highlight"] {{
    background-color: transparent !important;
    height: 0 !important;
}}
div[data-baseweb="tab-border"] {{
    background-color: transparent !important;
}}

/* Metrics — padding renforcé, effet de relief au survol */
div[data-testid="stMetric"] {{
    background: linear-gradient(135deg, #FFFFFF, #EDF6E9);
    border: 1px solid #D9E8D5;
    border-left: 4px solid {OR};
    border-radius: 8px;
    padding: 20px 18px 14px 18px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: 0 10px 22px rgba(43,27,18,0.13);
}}
div[data-testid="stMetricValue"] {{
    color: {BRUN_FONCE};
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 1px;
}}
div[data-testid="stMetricLabel"] {{
    color: #A08F7C;
    text-transform: uppercase;
    font-size: 0.72rem;
    letter-spacing: 0.8px;
}}

/* Sous-titres de section */
h3 {{
    font-family: 'Inter', sans-serif;
    color: {BRUN_FONCE};
    font-weight: 700;
    font-size: 1.05rem;
    border-bottom: 2px solid {OR};
    padding-bottom: 6px;
}}

/* Boutons génériques (selectbox focus, etc.) — neutraliser le rouge Streamlit */
:root {{
    --primary-color: {NOIR};
}}
.stSelectbox div[data-baseweb="select"] > div {{
    border-color: #D8C8B4 !important;
}}

/* Coach IA */
.coach-header {{
    background: radial-gradient(circle at 88% 20%, rgba(217,255,87,.22), transparent 24%), linear-gradient(110deg, #0B120E, #173724);
    background-size: cover;
    background-position: center;
    padding: 20px 24px;
    border-radius: 10px;
    border-left: 5px solid {OR};
    color: {CREME};
    margin-bottom: 18px;
}}
.coach-header h2 {{
    margin: 0;
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 1.5px;
    font-size: 1.7rem;
    color: {OR};
}}
.coach-header p {{ margin: 4px 0 0 0; opacity: 0.85; font-size: 0.9rem; }}

@media (max-width: 700px) {{
    .hero {{ padding: 32px 25px; background-position: 64% center; }}
    .hero h1 {{ font-size: 2.7rem; }}
    div[data-baseweb="tab-list"] {{ gap: 4px; overflow-x: auto; }}
    button[data-baseweb="tab"] {{ padding: 10px 9px; white-space: nowrap; }}
}}

/* Thème sombre global : il suit automatiquement le thème sombre du système. */
@media (prefers-color-scheme: dark) {{
    .stApp, section.main > div, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: #0B120E !important;
        color: #EAF1E6 !important;
    }}
    .block-container {{ background: #0B120E !important; }}
    .gym-title, h1, h2, h3, [data-testid="stMarkdownContainer"] {{ color: #EAF1E6 !important; }}
    .gym-subtitle, [data-testid="stCaptionContainer"] {{ color: #B8C8B7 !important; }}

    div[data-baseweb="tab-list"], div[data-testid="stTabs"] [role="tab"] {{
        background: #142019 !important;
        border-color: #34523E !important;
        box-shadow: none !important;
    }}
    div[data-testid="stTabs"] [role="tab"],
    div[data-testid="stTabs"] [role="tab"] * {{ color: #CBDACB !important; }}
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{ background: #D9FF57 !important; }}
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{ color: #0B120E !important; }}
    div[data-testid="stTabs"] [role="tab"]:hover {{ background: #203527 !important; }}

    .chart-card, .welcome-card, div[data-testid="stMetric"],
    [data-testid="stDataFrame"], [data-testid="stExpander"] {{
        background: #142019 !important;
        border-color: #2B4635 !important;
        color: #EAF1E6 !important;
        box-shadow: none !important;
    }}
    div[data-testid="stMetric"] * {{ color: #EAF1E6 !important; }}
    div[data-testid="stMetricValue"] {{ color: #D9FF57 !important; }}
    .section-kicker {{ color: #A9E28E !important; }}
    .welcome-card strong {{ color: #D9FF57 !important; }}
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
        background: #142019 !important;
        border-color: #34523E !important;
        color: #EAF1E6 !important;
    }}
}}

/* Streamlit applique la couleur du thème sombre aux éléments internes des onglets.
   Cette règle volontairement plus spécifique garantit le contraste sur toutes les versions. */
div[data-testid="stTabs"] [role="tab"],
div[data-testid="stTabs"] [role="tab"] * {{
    color: #26372D !important;
    opacity: 1 !important;
}}
div[data-testid="stTabs"] [role="tab"] {{
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 9px !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    background: {OR} !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{
    color: #0B120E !important;
    font-weight: 800 !important;
}}
div[data-testid="stTabs"] [role="tab"]:hover {{
    background: {VERT_CLAIR} !important;
}}
div[data-testid="stTabs"] [role="tab"]:hover,
div[data-testid="stTabs"] [role="tab"]:hover * {{
    color: #0B120E !important;
}}

/* Placé après les règles Streamlit : le mode sombre conserve une navigation forêt. */
@media (prefers-color-scheme: dark) {{
    div[data-testid="stTabs"] [role="tab"] {{
        background: transparent !important;
        border-color: transparent !important;
    }}
    div[data-testid="stTabs"] [role="tab"],
    div[data-testid="stTabs"] [role="tab"] * {{ color: #CBDACB !important; }}
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{ background: #D9FF57 !important; }}
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{ color: #0B120E !important; }}
    div[data-testid="stTabs"] [role="tab"]:hover {{ background: #203527 !important; }}
    div[data-testid="stTabs"] [role="tab"]:hover * {{ color: #EAF1E6 !important; }}
}}

/* Finitions d'interface : mêmes repères visuels dans tous les écrans. */
div[data-testid="stForm"], [data-testid="stExpander"] {{
    border: 1px solid #D9E8D5 !important;
    border-radius: 16px !important;
    overflow: hidden;
    background: #FFFFFF;
}}
[data-testid="stExpander"] details summary {{
    padding: 5px 4px;
    font-weight: 700;
    color: {BRUN_FONCE};
}}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-testid="stDateInput"] input, div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {{
    border-radius: 10px !important;
}}
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within {{
    border-color: {VERT} !important;
    box-shadow: 0 0 0 3px rgba(36,122,82,.14) !important;
}}
div.stButton > button, div[data-testid="stFormSubmitButton"] > button {{
    border-radius: 10px !important;
    font-weight: 700 !important;
    transition: transform .18s ease, box-shadow .18s ease !important;
}}
div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button {{
    background: {VERT} !important;
    border-color: {VERT} !important;
    color: #FFFFFF !important;
}}
div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(36,122,82,.22) !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid #D9E8D5;
    border-radius: 14px;
    overflow: hidden;
}}
@media (prefers-color-scheme: dark) {{
    div[data-testid="stForm"], [data-testid="stExpander"], [data-testid="stDataFrame"] {{
        background: #142019 !important;
        border-color: #2B4635 !important;
    }}
    [data-testid="stExpander"] details summary {{ color: #EAF1E6 !important; }}
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
    div[data-testid="stDateInput"] input, div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input {{
        background: #142019 !important;
        color: #EAF1E6 !important;
        border-color: #34523E !important;
    }}
}}

/* Navigation principale : prolongement visuel du bandeau sportif. */
div[data-baseweb="tab-list"] {{
    background: linear-gradient(105deg, #17231D, #0B120E) !important;
    border: 1px solid rgba(217,255,87,.32) !important;
    border-bottom: 3px solid #D9FF57 !important;
    border-radius: 16px !important;
    padding: 7px 10px !important;
    box-shadow: 0 12px 26px rgba(11,18,14,.18) !important;
}}
div[data-testid="stTabs"] [role="tab"],
div[data-testid="stTabs"] [role="tab"] * {{
    color: #DDE8D8 !important;
    background: transparent !important;
    border-color: transparent !important;
}}
div[data-testid="stTabs"] [role="tab"] {{ border-radius: 10px !important; }}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    background: #D9FF57 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.22) !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{
    color: #0B120E !important;
    font-weight: 800 !important;
}}
div[data-testid="stTabs"] [role="tab"]:hover,
div[data-testid="stTabs"] [role="tab"]:hover * {{
    background: rgba(217,255,87,.14) !important;
    color: #FFFFFF !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]:hover,
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]:hover * {{
    background: #D9FF57 !important;
    color: #0B120E !important;
}}

/* La navigation est intégrée au bandeau supérieur plutôt que séparée du hero. */
.hero {{
    padding-bottom: 92px;
    margin-bottom: -70px;
}}
div[data-testid="stTabs"] {{
    position: relative;
    z-index: 5;
    margin: 0 30px 32px !important;
}}
div[data-baseweb="tab-list"] {{
    background: transparent !important;
    border: 0 !important;
    border-bottom: 1px solid rgba(217,255,87,.35) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 0 7px !important;
}}
div[data-testid="stTabs"] [role="tab"],
div[data-testid="stTabs"] [role="tab"] * {{
    color: #DDE8D8 !important;
    background: transparent !important;
}}
div[data-testid="stTabs"] [role="tab"] {{
    border: 0 !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {{
    background: #D9FF57 !important;
    color: #0B120E !important;
}}
div[data-testid="stTabs"] [role="tab"]:hover,
div[data-testid="stTabs"] [role="tab"]:hover * {{
    background: rgba(217,255,87,.16) !important;
    color: #FFFFFF !important;
}}
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]:hover,
div[data-testid="stTabs"] [role="tab"][aria-selected="true"]:hover * {{
    background: #D9FF57 !important;
    color: #0B120E !important;
}}
@media (max-width: 700px) {{
    .hero {{ padding-bottom: 116px; margin-bottom: -92px; }}
    div[data-testid="stTabs"] {{ margin: 0 16px 24px !important; }}
    div[data-baseweb="tab-list"] {{ flex-wrap: nowrap; overflow-x: auto; }}
}}

/* Direction finale : dashboard immersif, sans marge extérieure. */
html, body {{
    margin: 0 !important;
    background: #0B120E !important;
}}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{
    background: #0B120E !important;
}}
[data-testid="stAppViewContainer"], .stApp, section.main, section.main > div {{
    background: #F4F6F0 !important;
}}
.block-container {{
    max-width: none !important;
    padding: 0 0 56px !important;
}}
.hero {{
    min-height: 290px;
    border-radius: 0 !important;
    margin: 0 0 -84px !important;
    padding: 58px clamp(24px, 6vw, 88px) 126px !important;
    background-position: center 42% !important;
    box-shadow: none !important;
}}
.hero h1 {{
    max-width: 720px;
    font-size: clamp(3.2rem, 6vw, 5.5rem) !important;
    line-height: .92;
}}
.hero p.tagline {{ font-size: 1.05rem; max-width: 540px; }}
div[data-testid="stTabs"] {{
    margin: 0 clamp(16px, 5vw, 76px) 36px !important;
}}
div[data-baseweb="tab-list"] {{
    justify-content: flex-start;
    gap: 6px !important;
}}
button[data-baseweb="tab"], div[data-testid="stTabs"] [role="tab"] {{
    letter-spacing: .1px !important;
    font-size: .86rem !important;
}}
.gym-title {{
    padding: 12px clamp(20px, 5vw, 76px) 0;
    font-size: clamp(2rem, 3vw, 2.8rem) !important;
}}
.gym-subtitle {{
    padding: 0 clamp(20px, 5vw, 76px);
    margin-bottom: 2rem !important;
}}
div[data-testid="stMetric"] {{
    border-radius: 0 !important;
    border-top: 1px solid #D9E8D5;
    border-right: 0;
    border-bottom: 1px solid #D9E8D5;
    box-shadow: none !important;
}}
.chart-card {{
    border-radius: 12px !important;
    box-shadow: none !important;
}}
@media (prefers-color-scheme: dark) {{
    [data-testid="stAppViewContainer"], .stApp, section.main, section.main > div {{
        background: #0B120E !important;
    }}
    div[data-testid="stMetric"] {{
        border-color: #294234 !important;
    }}
}}
@media (max-width: 700px) {{
    .block-container {{ padding-bottom: 32px !important; }}
    .hero {{ min-height: 270px; padding: 44px 22px 132px !important; margin-bottom: -98px !important; }}
    .hero h1 {{ font-size: 3.25rem !important; }}
    div[data-testid="stTabs"] {{ margin: 0 18px 28px !important; }}
    .gym-title, .gym-subtitle {{ padding-left: 20px; padding-right: 20px; }}
}}

/* Espace de travail des onglets : même rythme visuel sur toutes les pages. */
div[role="tabpanel"] {{
    padding: 18px clamp(20px, 5vw, 76px) 56px !important;
    background: #F4F6F0;
}}
div[role="tabpanel"] .gym-title {{ padding: 8px 0 0 !important; }}
div[role="tabpanel"] .gym-subtitle {{ padding: 0 !important; }}
div[role="tabpanel"] [data-testid="stHorizontalBlock"] {{ gap: 18px; }}
div[role="tabpanel"] div[data-testid="stMetric"] {{
    min-height: 112px;
    border: 1px solid #D9E8D5 !important;
    border-left: 4px solid #247A52 !important;
    border-radius: 14px !important;
    padding: 18px !important;
    background: linear-gradient(135deg, #FFFFFF, #F1F8EE) !important;
}}
div[role="tabpanel"] div[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    border-color: #9DCF91 !important;
    box-shadow: 0 10px 22px rgba(24,44,31,.09) !important;
}}
div[role="tabpanel"] .chart-card {{
    padding: 22px 24px 12px !important;
    margin: 4px 0 22px !important;
    border: 1px solid #DCE8D8 !important;
    background: #FFFFFF !important;
}}
div[role="tabpanel"] .chart-card h3 {{
    color: #17231D !important;
    border-bottom: 1px solid #DCE8D8 !important;
    margin-bottom: 18px;
}}
div[role="tabpanel"] [data-testid="stDataFrame"],
div[role="tabpanel"] [data-testid="stDataEditor"] {{
    margin: 12px 0 24px;
    border-radius: 12px !important;
    border: 1px solid #DCE8D8 !important;
}}
div[role="tabpanel"] [data-testid="stExpander"],
div[role="tabpanel"] [data-testid="stForm"] {{
    margin: 12px 0 18px;
    border-radius: 14px !important;
}}
div[role="tabpanel"] [data-testid="stAlert"] {{
    border-radius: 12px !important;
    border: 0 !important;
}}
div[role="tabpanel"] [data-testid="stChatMessage"] {{
    border-radius: 14px;
    padding: 12px 16px;
    margin: 10px 0;
    background: #FFFFFF;
    border: 1px solid #DCE8D8;
}}
div[role="tabpanel"] [data-testid="stChatInput"] {{
    border: 1px solid #BFD8B9;
    border-radius: 14px;
    background: #FFFFFF;
}}
@media (prefers-color-scheme: dark) {{
    div[role="tabpanel"] {{ background: #0B120E !important; }}
    div[role="tabpanel"] div[data-testid="stMetric"],
    div[role="tabpanel"] .chart-card,
    div[role="tabpanel"] [data-testid="stChatMessage"],
    div[role="tabpanel"] [data-testid="stChatInput"] {{
        background: #142019 !important;
        border-color: #294234 !important;
        box-shadow: none !important;
    }}
    div[role="tabpanel"] .chart-card h3 {{
        color: #EAF1E6 !important;
        border-color: #294234 !important;
    }}
    div[role="tabpanel"] div[data-testid="stMetric"] {{
        border-left-color: #D9FF57 !important;
        background: linear-gradient(135deg, #17271D, #101A13) !important;
    }}
}}
@media (max-width: 700px) {{
    div[role="tabpanel"] {{ padding: 16px 20px 36px !important; }}
    div[role="tabpanel"] [data-testid="stHorizontalBlock"] {{ gap: 10px; }}
    div[role="tabpanel"] div[data-testid="stMetric"] {{ min-height: auto; padding: 14px !important; }}
    div[role="tabpanel"] .chart-card {{ padding: 16px 14px 8px !important; }}
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

sns.set_theme(style="whitegrid")
mpl.rcParams["axes.edgecolor"] = "#D8C8B4"
PALETTE_PROFILS = {"Athlète confirmé": "#B8860B", "Force en progression": OR,
                    "Débutant régulier": "#D9A441", "Irrégulier": BRUN_FONCE}
COULEUR_PRINCIPALE = OR
COULEUR_SECONDAIRE = BRUN_FONCE


def titre(texte, sous_titre=None):
    st.markdown(f'<div class="gym-title">{texte}</div>', unsafe_allow_html=True)
    if sous_titre:
        st.markdown(f'<div class="gym-subtitle">{sous_titre}</div>', unsafe_allow_html=True)


# ============================================================
# Chargement des données
# ============================================================
@st.cache_data
def charger_donnees_brutes():
    conn = get_write_connection()
    query = """
    SELECT
        u.id AS user_id, u.nom, u.age, u.genre, u.niveau_initial, u.objectif,
        u.date_inscription,
        s.id AS seance_id, s.date_seance, s.duree_minutes,
        s.calories_brulees, s.frequence_cardiaque_moy,
        e.nom AS exercice, e.groupe_musculaire, e.type AS type_exercice,
        p.poids_kg, p.repetitions, p.sets
    FROM Performances p
    JOIN Seances s   ON p.seance_id = s.id
    JOIN Users u     ON s.user_id = u.id
    JOIN Exercices e ON p.exercice_id = e.id
    """
    df = pd.read_sql_query(query, conn, parse_dates=["date_seance", "date_inscription"])
    conn.close()
    df["volume"] = df["poids_kg"] * df["repetitions"] * df["sets"]
    return df


def nommer_clusters(df_clusters, features):
    moyennes = df_clusters[features].mean()
    noms = {}
    for cid in sorted(df_clusters["cluster"].unique()):
        moy = df_clusters[df_clusters["cluster"] == cid][features].mean()
        volume_rel = moy["volume_moy"] / moyennes["volume_moy"]
        freq_rel = moy["seances_par_semaine"] / moyennes["seances_par_semaine"]
        if volume_rel > 1.15 and freq_rel > 1.1:
            noms[cid] = "Athlète confirmé"
        elif freq_rel < 0.7:
            noms[cid] = "Irrégulier"
        elif volume_rel > 1.05:
            noms[cid] = "Force en progression"
        else:
            noms[cid] = "Débutant régulier"
    return noms


@st.cache_data
def calculer_profils_et_clusters(df):
    features = ["age", "nb_seances", "duree_moy", "calories_moy", "fc_moy",
                "volume_moy", "poids_max", "seances_par_semaine"]

    if df.empty:
        colonnes = ["user_id", "age", "niveau_initial", "objectif"] + features + ["PC1", "PC2", "cluster", "profil"]
        return pd.DataFrame(columns=colonnes), features

    df = df.copy()
    df["anciennete_jours"] = (df["date_seance"] - df["date_inscription"]).dt.days

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

    agg["seances_par_semaine"] = (agg["nb_seances"] / (agg["anciennete_max"] / 7).replace(0, np.nan)).fillna(0)

    X = agg[features].fillna(0)

    if len(agg) < 2:
        # Pas assez d'utilisateurs pour un clustering ou une ACP significatifs
        agg["PC1"], agg["PC2"], agg["cluster"] = 0.0, 0.0, 0
        agg["profil"] = "Données insuffisantes"
        return agg, features

    X_scaled = StandardScaler().fit_transform(X)

    pca = PCA(n_components=2)
    comp = pca.fit_transform(X_scaled)
    agg["PC1"], agg["PC2"] = comp[:, 0], comp[:, 1]

    km = KMeans(n_clusters=2, random_state=42, n_init=10)
    agg["cluster"] = km.fit_predict(X_scaled)
    noms = nommer_clusters(agg, features)
    agg["profil"] = agg["cluster"].map(noms)

    return agg, features


df_complet = charger_donnees_brutes()
df = df_complet.copy()
df_users, FEATURES_CLUSTER = calculer_profils_et_clusters(df)


# ============================================================
# Formulaires de saisie de données réelles
# ============================================================
def render_saisie_donnees():
    with st.expander("Nouvel utilisateur", expanded=df.empty):
        with st.form("form_nouvel_utilisateur", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom complet")
            age = c2.number_input("Âge", min_value=14, max_value=90, value=25)
            c3, c4 = st.columns(2)
            genre = c3.selectbox("Genre", ["H", "F"])
            niveau_initial = c4.selectbox("Niveau initial", NIVEAUX)
            c5, c6 = st.columns(2)
            objectif = c5.selectbox("Objectif", OBJECTIFS)
            date_inscription = c6.date_input("Date d'inscription", value=date.today())
            submit_user = st.form_submit_button("Ajouter l'utilisateur")

        if submit_user:
            if not nom.strip():
                st.error("Le nom est obligatoire.")
            else:
                conn = get_write_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO Users (nom, age, genre, niveau_initial, objectif, date_inscription) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (nom.strip(), int(age), genre, niveau_initial, objectif, date_inscription.isoformat()),
                )
                conn.commit()
                cur.close()
                conn.close()
                charger_donnees_brutes.clear()
                calculer_profils_et_clusters.clear()
                st.success(f"Utilisateur « {nom.strip()} » ajouté.")
                st.rerun()

    st.write("")

    with st.expander("Enregistrer une séance", expanded=not df.empty):
        conn = get_write_connection()
        users_df = pd.read_sql_query("SELECT id, nom FROM Users ORDER BY nom", conn)
        exercices_df = pd.read_sql_query("SELECT nom FROM Exercices ORDER BY nom", conn)
        conn.close()

        if users_df.empty:
            st.info("Ajoute d'abord un utilisateur ci-dessus.")
        else:
            user_choisi = st.selectbox(
                "Utilisateur", options=users_df["id"],
                format_func=lambda uid: users_df.set_index("id").loc[uid, "nom"],
                key="saisie_user",
            )
            c1, c2, c3 = st.columns(3)
            date_seance = c1.date_input("Date de la séance", value=date.today(), key="saisie_date")
            duree = c2.number_input("Durée (min)", min_value=1, max_value=300, value=60, key="saisie_duree")
            calories = c3.number_input("Calories brûlées", min_value=0, max_value=2000, value=400, key="saisie_calories")
            fc_moy = st.number_input("Fréquence cardiaque moyenne (bpm)", min_value=40, max_value=220,
                                      value=130, key="saisie_fc")

            st.caption("Ajoute une ligne par exercice effectué pendant cette séance :")
            perf_defaut = pd.DataFrame([{
                "exercice": exercices_df["nom"].iloc[0] if not exercices_df.empty else "",
                "poids_kg": 20.0, "repetitions": 10, "sets": 3,
            }])
            perfs_saisies = st.data_editor(
                perf_defaut,
                num_rows="dynamic",
                column_config={
                    "exercice": st.column_config.SelectboxColumn("Exercice", options=list(exercices_df["nom"])),
                    "poids_kg": st.column_config.NumberColumn("Poids (kg)", min_value=0.0, step=0.5),
                    "repetitions": st.column_config.NumberColumn("Répétitions", min_value=1, step=1),
                    "sets": st.column_config.NumberColumn("Séries", min_value=1, step=1),
                },
                use_container_width=True,
                key="saisie_perfs",
            )

            if st.button("Enregistrer la séance", type="primary"):
                lignes_valides = perfs_saisies.dropna(subset=["exercice"])
                lignes_valides = lignes_valides[lignes_valides["exercice"] != ""]
                if lignes_valides.empty:
                    st.error("Ajoute au moins un exercice avec ses données.")
                else:
                    conn = get_write_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO Seances (user_id, date_seance, duree_minutes, calories_brulees, "
                        "frequence_cardiaque_moy) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (int(user_choisi), date_seance.isoformat(), int(duree), float(calories), int(fc_moy)),
                    )
                    seance_id = cur.fetchone()[0]
                    for _, ligne in lignes_valides.iterrows():
                        cur.execute("SELECT id FROM Exercices WHERE nom = %s", (ligne["exercice"],))
                        res = cur.fetchone()
                        if res:
                            cur.execute(
                                "INSERT INTO Performances (seance_id, exercice_id, poids_kg, repetitions, sets) "
                                "VALUES (%s, %s, %s, %s, %s)",
                                (seance_id, res[0], float(ligne["poids_kg"]), int(ligne["repetitions"]), int(ligne["sets"])),
                            )
                    conn.commit()
                    cur.close()
                    conn.close()
                    charger_donnees_brutes.clear()
                    calculer_profils_et_clusters.clear()
                    st.success("Séance enregistrée avec succès.")
                    st.rerun()

    st.write("")
    with st.expander("Zone avancée"):
        st.caption("Repartir de zéro : supprime tous les utilisateurs, séances et performances. "
                   "Le catalogue d'exercices est conservé.")
        confirmer = st.checkbox("Je confirme vouloir tout supprimer", key="confirm_reset")
        if st.button("Réinitialiser les données", disabled=not confirmer):
            conn = get_write_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM Performances;")
            cur.execute("DELETE FROM Seances;")
            cur.execute("DELETE FROM Users;")
            conn.commit()
            cur.close()
            conn.close()
            charger_donnees_brutes.clear()
            calculer_profils_et_clusters.clear()
            st.success("Toutes les données ont été supprimées.")
            st.rerun()


# ============================================================
# Hero — bandeau riche avec stats en direct + navigation horizontale
# ============================================================

st.markdown(
    f'''<div class="hero">
        <div class="hero-eyebrow">Performance au quotidien</div>
        <h1>SMART GYM TRACKER</h1>
        <p class="tagline">Plateforme d'analyse et de prédiction des performances sportives</p>
    </div>''',
    unsafe_allow_html=True,
)

if df_complet.empty:
    titre("Ajouter des données réelles", "Commence par enregistrer un utilisateur, puis sa première séance")
    render_saisie_donnees()
    st.stop()

tab_saisie, tab_global, tab_individuel, tab_cluster, tab_predict, tab_coach = st.tabs([
    "Ajouter des données", "Vue globale", "Suivi individuel", "Clustering & Profils",
    "Prédiction", "Coach IA",
])

with tab_saisie:
    titre("Ajouter des données réelles", "Enregistre de nouveaux utilisateurs et de nouvelles séances")
    render_saisie_donnees()


# ============================================================
# ONGLET 1 — Vue globale
# ============================================================
with tab_global:
    titre("Vue globale du gym", "Aperçu général de l'activité de tous les utilisateurs")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("Séances par jour de la semaine")
        seances_uniques = df.drop_duplicates("seance_id").copy()
        seances_uniques["jour"] = seances_uniques["date_seance"].dt.day_name()
        ordre = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        noms_fr = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mer", "Thursday": "Jeu",
                   "Friday": "Ven", "Saturday": "Sam", "Sunday": "Dim"}
        counts = seances_uniques["jour"].value_counts().reindex(ordre).rename(index=noms_fr)
        fig, ax = plt.subplots(figsize=(6, 4))
        counts.plot(kind="bar", color=COULEUR_PRINCIPALE, ax=ax)
        ax.set_ylabel("Nombre de séances")
        st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("Répartition par groupe musculaire")
        fig, ax = plt.subplots(figsize=(6, 4))
        df["groupe_musculaire"].value_counts().plot(kind="bar", color=COULEUR_SECONDAIRE, ax=ax)
        ax.set_ylabel("Occurrences")
        st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# ONGLET 2 — Suivi individuel
# ============================================================
with tab_individuel:
    titre("Suivi individuel", "Progression détaillée d'un utilisateur")

    users_liste = df[["user_id", "nom"]].drop_duplicates().sort_values("nom")
    choix = st.selectbox("Choisir un utilisateur", options=users_liste["user_id"],
                          format_func=lambda uid: users_liste.set_index("user_id").loc[uid, "nom"],
                          key="suivi_user")

    df_user = df[df["user_id"] == choix].sort_values("date_seance")
    infos = df_user.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Âge", int(infos["age"]))
    col2.metric("Niveau", infos["niveau_initial"])
    col3.metric("Objectif", infos["objectif"])
    col4.metric("Séances", df_user["seance_id"].nunique())

    dernier_entrainement = df_complet.loc[
        df_complet["user_id"] == choix, "date_seance"
    ].max()
    jours_sans_seance = (df_complet["date_seance"].max() - dernier_entrainement).days
    action_col, statut_col = st.columns([1, 2])
    export_suivi = df_user[[
        "date_seance", "exercice", "groupe_musculaire", "poids_kg",
        "repetitions", "sets", "duree_minutes", "calories_brulees",
    ]].sort_values("date_seance").rename(columns={
        "date_seance": "Date", "exercice": "Exercice", "groupe_musculaire": "Groupe musculaire",
        "poids_kg": "Poids (kg)", "repetitions": "Répétitions", "sets": "Séries",
        "duree_minutes": "Durée (min)", "calories_brulees": "Calories brûlées",
    })
    action_col.download_button(
        "Télécharger mon suivi CSV",
        data=export_suivi.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"suivi_{infos['nom'].replace(' ', '_')}.csv",
        mime="text/csv",
        key="telecharger_suivi",
    )
    if jours_sans_seance >= 14:
        statut_col.warning(f"Aucune séance depuis {jours_sans_seance} jours.")
    else:
        statut_col.success("Rythme d'entraînement récent : continue comme ça !")

    st.write("")
    exercices_user = sorted(df_user["exercice"].unique())
    exercice_choisi = st.selectbox("Exercice à suivre", exercices_user, key="suivi_exo")
    df_exo = df_user[df_user["exercice"] == exercice_choisi].sort_values("date_seance")

    st.subheader(f"Progression — {exercice_choisi}")
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_exo["date_seance"], df_exo["poids_kg"], marker="o", color=COULEUR_PRINCIPALE, markersize=4)
    ax.set_xlabel("Date"); ax.set_ylabel("Poids (kg)"); ax.grid(alpha=0.3)
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("Calories par séance")
        su = df_user.drop_duplicates("seance_id").sort_values("date_seance")
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.plot(su["date_seance"], su["calories_brulees"], color=COULEUR_SECONDAIRE)
        st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("Volume par groupe musculaire")
        fig, ax = plt.subplots(figsize=(8, 3.5))
        df_user.groupby("groupe_musculaire")["volume"].sum().plot(kind="bar", color=COULEUR_PRINCIPALE, ax=ax)
        st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# ONGLET 3 — Clustering & Profils
# ============================================================
with tab_cluster:
    titre("Clustering & Profils utilisateurs", "Segmentation automatique par comportement (K-Means)")

    profil_counts = df_users["profil"].value_counts()
    badges_html = "".join(
        f'<span class="profile-badge" style="background:{PALETTE_PROFILS.get(p, OR)}22;'
        f'color:{PALETTE_PROFILS.get(p, OR)};border:1px solid {PALETTE_PROFILS.get(p, OR)}77;">'
        f'{p} · {c}</span>'
        for p, c in profil_counts.items()
    )
    st.markdown(f'<div class="badges-row">{badges_html}</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.scatterplot(data=df_users, x="PC1", y="PC2", hue="profil",
                     palette=PALETTE_PROFILS, s=90, ax=ax)
    ax.set_title("Projection ACP des profils")
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.subheader("Caractéristiques moyennes par profil")
    st.dataframe(df_users.groupby("profil")[FEATURES_CLUSTER].mean().round(1))

    st.write("")
    st.subheader("Explorer un profil")
    profil_choisi = st.selectbox("Profil", sorted(df_users["profil"].unique()), key="cluster_profil")
    colonnes_identite = [c for c in ["user_id", "niveau_initial", "objectif"] if c not in FEATURES_CLUSTER]
    colonnes_affichees = colonnes_identite + FEATURES_CLUSTER
    st.dataframe(df_users[df_users["profil"] == profil_choisi][colonnes_affichees])


# ============================================================
# ONGLET 4 — Prédiction
# ============================================================
with tab_predict:
    titre("Prédiction de performance", "Estimation du poids à la prochaine séance (Random Forest)")

    users_liste = df[["user_id", "nom"]].drop_duplicates().sort_values("nom")
    choix = st.selectbox("Utilisateur", options=users_liste["user_id"],
                          format_func=lambda uid: users_liste.set_index("user_id").loc[uid, "nom"],
                          key="pred_user")

    df_user = df[(df["user_id"] == choix) & (df["type_exercice"] == "Force")]
    exos = sorted(df_user["exercice"].unique())

    if not exos:
        st.info("Aucun exercice de force enregistré pour cet utilisateur.")
    else:
        exercice_choisi = st.selectbox("Exercice", exos, key="pred_exo")
        historique = df_user[df_user["exercice"] == exercice_choisi].sort_values("date_seance")

        if len(historique) < 3:
            st.info("Pas assez d'historique (minimum 3 séances).")
        else:
            df_exo_g = df[(df["exercice"] == exercice_choisi) & (df["type_exercice"] == "Force")].copy()
            df_exo_g = df_exo_g.sort_values(["user_id", "date_seance"])
            df_exo_g["seance_num"] = df_exo_g.groupby("user_id").cumcount() + 1
            df_exo_g["poids_precedent"] = df_exo_g.groupby("user_id")["poids_kg"].shift(1)
            df_exo_g["poids_avant_precedent"] = df_exo_g.groupby("user_id")["poids_kg"].shift(2)
            df_exo_g["tendance"] = df_exo_g["poids_precedent"] - df_exo_g["poids_avant_precedent"]
            niveau_map = {"Débutant": 0, "Intermédiaire": 1, "Avancé": 2}
            df_exo_g["niveau_code"] = df_exo_g["niveau_initial"].map(niveau_map)
            df_train = df_exo_g.dropna(subset=["poids_precedent", "poids_avant_precedent", "tendance"])

            feats = ["seance_num", "poids_precedent", "poids_avant_precedent", "tendance", "niveau_code"]
            model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
            model.fit(df_train[feats], df_train["poids_kg"])

            derniere, avant = historique.iloc[-1], historique.iloc[-2]
            X_new = pd.DataFrame([{
                "seance_num": len(historique) + 1,
                "poids_precedent": derniere["poids_kg"],
                "poids_avant_precedent": avant["poids_kg"],
                "tendance": derniere["poids_kg"] - avant["poids_kg"],
                "niveau_code": niveau_map.get(derniere["niveau_initial"], 1),
            }])
            prediction = model.predict(X_new)[0]

            col1, col2 = st.columns(2)
            col1.metric("Dernier poids", f"{derniere['poids_kg']:.1f} kg")
            col2.metric("Poids prédit", f"{prediction:.1f} kg", delta=f"{prediction - derniere['poids_kg']:+.1f} kg")

            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(historique["date_seance"], historique["poids_kg"], marker="o", color=COULEUR_PRINCIPALE, label="Historique")
            ax.scatter([historique["date_seance"].iloc[-1]], [prediction], color=COULEUR_SECONDAIRE, s=100, zorder=5, label="Prédiction")
            ax.legend()
            st.pyplot(fig)
            st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# ONGLET 5 — Coach IA
# ============================================================
with tab_coach:
    st.markdown(
        '<div class="coach-header"><h2>Coach IA</h2>'
        '<p>Pose une question sur ta progression — le coach répond en analysant tes vraies données.</p></div>',
        unsafe_allow_html=True,
    )

    users_liste = df[["user_id", "nom"]].drop_duplicates().sort_values("nom")
    choix = st.selectbox("Tu es...", options=users_liste["user_id"],
                          format_func=lambda uid: users_liste.set_index("user_id").loc[uid, "nom"],
                          key="coach_user")

    user_row = df_users[df_users["user_id"] == choix].iloc[0]
    df_user_raw = df[df["user_id"] == choix]

    def generer_reponse(question):
        q = question.lower()
        nom = users_liste.set_index("user_id").loc[choix, "nom"]

        if any(w in q for w in ["progress", "évolu", "avance"]):
            exo_top = df_user_raw[df_user_raw["type_exercice"] == "Force"].groupby("exercice")["poids_kg"].agg(["first", "last"])
            if not exo_top.empty:
                exo_top["gain"] = exo_top["last"] - exo_top["first"]
                meilleur = exo_top["gain"].idxmax()
                gain = exo_top.loc[meilleur, "gain"]
                return (f"Ta progression est solide sur **{meilleur}** : +{gain:.1f} kg depuis le début. "
                        f"Sur l'ensemble, tu as fait {int(user_row['nb_seances'])} séances "
                        f"avec un rythme de {user_row['seances_par_semaine']:.1f} séances/semaine.")
            return "Pas encore assez de données pour analyser ta progression."

        if any(w in q for w in ["conseil", "recommand", "quoi faire", "améliorer"]):
            if user_row["profil"] == "Irrégulier":
                return ("Ton profil est **Irrégulier** — le plus gros levier pour toi est la régularité, "
                        "pas l'intensité. Vise 2 séances fixes par semaine avant d'augmenter les charges.")
            elif user_row["profil"] == "Athlète confirmé":
                return ("Tu es dans le profil **Athlète confirmé**. Pour continuer à progresser, "
                        "pense à varier les stimuli (périodisation) plutôt que d'ajouter du volume brut.")
            else:
                return ("Continue sur ta lancée — garde une progression de charge légère mais constante "
                        "(+0.5 à 1kg par semaine) plutôt que des sauts brusques.")

        if any(w in q for w in ["profil", "cluster", "catégorie"]):
            return (f"Ton profil calculé automatiquement (K-Means) est : **{user_row['profil']}**. "
                    f"Il est basé sur ton volume moyen, ta fréquence et ton poids max.")

        if any(w in q for w in ["objectif", "goal"]):
            return f"Ton objectif enregistré est **{user_row['objectif']}**, avec un niveau initial **{user_row['niveau_initial']}**."

        if any(w in q for w in ["calorie", "brûl"]):
            return f"Tu brûles en moyenne **{user_row['calories_moy']:.0f} kcal** par séance."

        return (f"Salut {nom.split()[0]}. Je peux te parler de ta progression, tes conseils personnalisés, "
                f"ton profil, ton objectif ou tes calories. Pose-moi une question sur l'un de ces sujets.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    question = st.chat_input("Ex : Comment je progresse ? Quel conseil pour moi ?")
    if question:
        st.session_state.chat_history.append(("user", question))
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            reponse = generer_reponse(question)
            texte_affiche = ""
            for mot in reponse.split(" "):
                texte_affiche += mot + " "
                placeholder.markdown(texte_affiche + "▌")
                time.sleep(0.02)
            placeholder.markdown(texte_affiche)
        st.session_state.chat_history.append(("assistant", reponse))

    st.caption("Le coach analyse tes données réelles (progression, profil K-Means, objectif) — "
               "logique de règles basée sur tes statistiques, sans modèle de langage externe.")