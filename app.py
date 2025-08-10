# app.py — Трекер веса для iPhone (Streamlit, RU)
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import altair as alt

st.set_page_config(page_title="Трекер веса", page_icon="🏃‍♀️", layout="wide")

DATE_FMT = "%d.%m.%Y"
COLS = ["Дата", "Вес (кг)", "Калории (ккал)", "Белки (г)", "Жиры (г)", "Углеводы (г)",
        "Тип тренировки", "Выполнено (✅/❌)", "Шаги", "Заметки"]

DEFAULT_TYPES = ["Силовые + Аквафитнес", "Ходьба 10 км", "Отдых"]

@st.cache_data
def load_df():
    return pd.DataFrame(columns=COLS)

def forecast_series(start_date, start_weight, weekly_loss, days=400, goal_weight=None):
    if goal_weight is None:
        goal_weight = max(30.0, start_weight - 100)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    weights = [max(start_weight - weekly_loss*(i/7.0), goal_weight) for i in range(days)]
    return pd.DataFrame({"Дата": dates, "План (кг)": weights})

# Настройки (в боковой панели)
if "start_weight" not in st.session_state: st.session_state.start_weight = 83.0
if "start_date"   not in st.session_state: st.session_state.start_date   = date(2025, 7, 27)
if "target_loss"  not in st.session_state: st.session_state.target_loss  = 30.0
if "weekly_loss"  not in st.session_state: st.session_state.weekly_loss  = 0.75
if "df" not in st.session_state: st.session_state.df = load_df()

st.sidebar.header("⚙️ Настройки")
st.sidebar.number_input("Стартовый вес (кг)", 30.0, 300.0, key="start_weight")
st.sidebar.date_input("Дата старта", key="start_date")
st.sidebar.number_input("Цель снижения (кг)", 1.0, 100.0, key="target_loss")
st.sidebar.number_input("Скорость (кг/нед)", 0.1, 3.0, key="weekly_loss")

st.title("🏃‍♀️ Трекер веса — ежедневный журнал")

# Быстрый ввод (дата = сегодня по умолчанию)
c1, c2, c3, c4 = st.columns(4)
with c1:
    d = st.date_input("Дата", value=date.today())
with c2:
    w = st.number_input("Вес (кг)", min_value=0.0, max_value=500.0, step=0.1, format="%.1f")
with c3:
    kcal = st.number_input("Калории (ккал)", min_value=0, max_value=20000, step=10)
with c4:
    steps = st.number_input("Шаги", min_value=0, max_value=200000, step=100)

c5, c6, c7 = st.columns(3)
with c5:
    prot = st.number_input("Белки (г)", min_value=0, max_value=400, step=1)
with c6:
    fat = st.number_input("Жиры (г)", min_value=0, max_value=400, step=1)
with c7:
    carbs = st.number_input("Углеводы (г)", min_value=0, max_value=1000, step=1)

c8, c9 = st.columns(2)
with c8:
    ttype = st.selectbox("Тип тренировки", DEFAULT_TYPES, index=0)
with c9:
    done = st.selectbox("Выполнено", ["", "✅", "❌"], index=0)

note = st.text_area("Заметки", placeholder="Самочувствие, сон, цикл, что помогло/мешало…")

if st.button("Добавить / Обновить"):
    df = st.session_state.df.copy()
    new_row = {COLS[0]: d, COLS[1]: w, COLS[2]: kcal, COLS[3]: prot, COLS[4]: fat, COLS[5]: carbs,
               COLS[6]: ttype, COLS[7]: done, COLS[8]: steps, COLS[9]: note}
    if not df.empty and d in set(df["Дата"]):
        df.loc[df["Дата"] == d, :] = new_row
    else:
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.df = df.sort_values("Дата")
    st.success("Сохранено!")

st.divider()

df = st.session_state.df.copy()
st.subheader("Последние записи")
st.dataframe(df.sort_values("Дата", ascending=False).head(10), use_container_width=True)

# Метрики
colA, colB, colC, colD, colE = st.columns(5)
cur_w = df["Вес (кг)"].dropna().iloc[-1] if not df.dropna(subset=["Вес (кг)"]).empty else None
loss_total = (st.session_state.start_weight - cur_w) if cur_w is not None else None
target_pct = (loss_total / st.session_state.target_loss) if (loss_total and st.session_state.target_loss>0) else None
goal_w = st.session_state.start_weight - st.session_state.target_loss

colA.metric("Текущий вес", f"{cur_w:.1f}" if cur_w is not None else "—")
colB.metric("Сброшено всего", f"{loss_total:.1f}" if loss_total is not None else "—")
colC.metric("Прогресс к цели", f"{target_pct*100:.1f}%" if target_pct is not None else "—")
colD.metric("Целевой вес", f"{goal_w:.1f}")
colE.metric("Скорость", f"{st.session_state.weekly_loss:.2f} кг/нед")

# Прогноз и график
forecast = forecast_series(st.session_state.start_date, st.session_state.start_weight,
                           st.session_state.weekly_loss, days=400, goal_weight=goal_w)
chart_df = pd.merge(forecast, df[["Дата","Вес (кг)"]], on="Дата", how="left")

st.subheader("График: Факт vs План")
chart = alt.Chart(chart_df).transform_fold(
    ["Вес (кг)", "План (кг)"], as_=["Серия", "Значение"]
).mark_line().encode(
    x=alt.X("Дата:T", title="Дата"),
    y=alt.Y("Значение:Q", title="Вес (кг)"),
    color="Серия:N"
).properties(height=360)
st.altair_chart(chart, use_container_width=True)
