# app.py — Suivi de poids pour iPhone (Streamlit)
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import altair as alt

st.set_page_config(page_title="Suivi de poids", page_icon="🏃‍♀️", layout="wide")

DATE_FMT = "%d.%m.%Y"
COLS = ["Date", "Poids (kg)", "Calories (kcal)", "Protéines (g)", "Lipides (g)", "Glucides (g)",
        "Type séance", "Fait (✅/❌)", "Pas", "Notes"]

DEFAULT_TYPES = ["Force + Aquafit", "Marche 10 km", "Repos"]

@st.cache_data
def load_df():
    return pd.DataFrame(columns=COLS)

def forecast_series(start_date, start_weight, weekly_loss, days=400, goal_weight=None):
    if goal_weight is None:
        goal_weight = max(30.0, start_weight - 100)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    weights = [max(start_weight - weekly_loss*(i/7.0), goal_weight) for i in range(days)]
    return pd.DataFrame({"Date": dates, "Prévu (kg)": weights})

# Réglages (modifiables dans la barre latérale)
if "start_weight" not in st.session_state: st.session_state.start_weight = 83.0
if "start_date"   not in st.session_state: st.session_state.start_date   = date(2025, 7, 27)
if "target_loss"  not in st.session_state: st.session_state.target_loss  = 30.0
if "weekly_loss"  not in st.session_state: st.session_state.weekly_loss  = 0.75
if "df" not in st.session_state: st.session_state.df = load_df()

st.sidebar.header("⚙️ Réglages")
st.sidebar.number_input("Poids de départ (kg)", 30.0, 300.0, key="start_weight")
st.sidebar.date_input("Date de départ", key="start_date")
st.sidebar.number_input("Perte visée (kg)", 1.0, 100.0, key="target_loss")
st.sidebar.number_input("Vitesse (kg/sem)", 0.1, 3.0, key="weekly_loss")

st.title("🏃‍♀️ Suivi de poids — Journal quotidien")

# Formulaire rapide (date auto aujourd’hui)
c1, c2, c3, c4 = st.columns(4)
with c1:
    d = st.date_input("Date", value=date.today())
with c2:
    w = st.number_input("Poids (kg)", min_value=0.0, max_value=500.0, step=0.1, format="%.1f")
with c3:
    kcal = st.number_input("Calories (kcal)", min_value=0, max_value=20000, step=10)
with c4:
    steps = st.number_input("Pas", min_value=0, max_value=200000, step=100)

c5, c6, c7 = st.columns(3)
with c5:
    prot = st.number_input("Protéines (g)", min_value=0, max_value=400, step=1)
with c6:
    fat = st.number_input("Lipides (g)", min_value=0, max_value=400, step=1)
with c7:
    carbs = st.number_input("Glucides (g)", min_value=0, max_value=1000, step=1)

c8, c9 = st.columns(2)
with c8:
    ttype = st.selectbox("Type séance", DEFAULT_TYPES, index=0)
with c9:
    done = st.selectbox("Fait", ["", "✅", "❌"], index=0)
note = st.text_area("Notes", placeholder="Sommeil, cycle, énergie, etc.")

if st.button("Ajouter / Mettre à jour"):
    df = st.session_state.df.copy()
    new_row = {COLS[0]: d, COLS[1]: w, COLS[2]: kcal, COLS[3]: prot, COLS[4]: fat, COLS[5]: carbs,
               COLS[6]: ttype, COLS[7]: done, COLS[8]: steps, COLS[9]: note}
    if not df.empty and d in set(df["Date"]):
        df.loc[df["Date"] == d, :] = new_row
    else:
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.df = df.sort_values("Date")
    st.success("Enregistré !")

st.divider()

df = st.session_state.df.copy()
st.subheader("Dernières entrées")
st.dataframe(df.sort_values("Date", ascending=False).head(10), use_container_width=True)

# Métriques
colA, colB, colC, colD, colE = st.columns(5)
cur_w = df["Poids (kg)"].dropna().iloc[-1] if not df.dropna(subset=["Poids (kg)"]).empty else None
loss_total = (st.session_state.start_weight - cur_w) if cur_w is not None else None
target_pct = (loss_total / st.session_state.target_loss) if (loss_total and st.session_state.target_loss>0) else None
goal_w = st.session_state.start_weight - st.session_state.target_loss

colA.metric("Poids actuel", f"{cur_w:.1f}" if cur_w is not None else "—")
colB.metric("Perte totale", f"{loss_total:.1f}" if loss_total is not None else "—")
colC.metric("Avancement", f"{target_pct*100:.1f}%" if target_pct is not None else "—")
colD.metric("Poids cible", f"{goal_w:.1f}")
colE.metric("Vitesse", f"{st.session_state.weekly_loss:.2f} kg/sem")

# Prévision et graphique
forecast = forecast_series(st.session_state.start_date, st.session_state.start_weight,
                           st.session_state.weekly_loss, days=400, goal_weight=goal_w)
chart_df = pd.merge(forecast, df[["Date","Poids (kg)"]], on="Date", how="left")

st.subheader("Courbe : Fait vs Prévu")
chart = alt.Chart(chart_df).transform_fold(
    ["Poids (kg)", "Prévu (kg)"], as_=["Série", "Valeur"]
).mark_line().encode(
    x=alt.X("Date:T", title="Date"),
    y=alt.Y("Valeur:Q", title="Poids (kg)"),
    color="Série:N"
).properties(height=360)
st.altair_chart(chart, use_container_width=True)
