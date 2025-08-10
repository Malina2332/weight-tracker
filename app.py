# app.py — Трекер веса (Streamlit, RU) с автосохранением в Google Sheets
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import altair as alt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Трекер веса", page_icon="🏃‍♀️", layout="wide")

# ---------- Настройка доступа к Google Sheets ----------
SHEET_ID = st.secrets["sheets"]["sheet_id"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
gc = gspread.authorize(CREDS)
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Data")

HEADERS = ["Дата","Вес (кг)","Калории (ккал)","Белки (г)","Жиры (г)","Углеводы (г)","Тип тренировки","Выполнено","Шаги","Заметки"]
DATE_FMT = "%d.%m.%Y"

def _ensure_headers():
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(HEADERS)
    else:
        hdr = rows[0]
        if hdr != HEADERS:
            ws.update("A1:J1", [HEADERS])

def read_df():
    _ensure_headers()
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return pd.DataFrame(columns=HEADERS)

    df = pd.DataFrame(rows[1:], columns=rows[0])
    for c in HEADERS:
        if c not in df.columns:
            df[c] = ""

    def to_date(x):
        if not x:
            return None
        for fmt in [DATE_FMT, "%Y-%m-%d"]:
            try:
                return datetime.strptime(x, fmt).date()
            except:
                pass
        try:
            return pd.to_datetime(x).date()
        except:
            return None

    df["Дата"] = df["Дата"].apply(to_date)
    num_cols = ["Вес (кг)","Калории (ккал)","Белки (г)","Жиры (г)","Углеводы (г)","Шаги"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna(subset=["Дата"]).sort_values("Дата")

def upsert_row(entry: dict):
    _ensure_headers()
    target_str = entry["Дата"].strftime(DATE_FMT)
    col_dates = ws.col_values(1)[1:]
    row_idx = None
    for i, d in enumerate(col_dates, start=2):
        if d == target_str:
            row_idx = i
            break

    values = [
        target_str,
        entry.get("Вес (кг)", ""),
        entry.get("Калории (ккал)", ""),
        entry.get("Белки (г)", ""),
        entry.get("Жиры (г)", ""),
        entry.get("Углеводы (г)", ""),
        entry.get("Тип тренировки", ""),
        entry.get("Выполнено", ""),
        entry.get("Шаги", ""),
        entry.get("Заметки", ""),
    ]

    if row_idx:
        ws.update(f"A{row_idx}:J{row_idx}", [values])
    else:
        ws.append_row(values, value_input_option="USER_ENTERED")

def forecast_df(start_date: date, start_weight: float, weekly_loss: float, days=400, goal_weight=None):
    if goal_weight is None:
        goal_weight = max(30.0, start_weight - 100.0)
    dates = pd.date_range(start_date, periods=days, freq="D")
    planned = [max(start_weight - weekly_loss*(i/7.0), goal_weight) for i in range(days)]
    return pd.DataFrame({"Дата": dates, "План (кг)": planned})

if "start_weight" not in st.session_state: st.session_state.start_weight = 83.0
if "start_date"   not in st.session_state: st.session_state.start_date   = date(2025, 7, 27)
if "target_loss"  not in st.session_state: st.session_state.target_loss  = 30.0
if "weekly_loss"  not in st.session_state: st.session_state.weekly_loss  = 0.75

with st.sidebar:
    st.header("⚙️ Настройки")
    st.session_state.start_weight = st.number_input("Стартовый вес (кг)", 30.0, 300.0, value=st.session_state.start_weight, step=0.5)
    st.session_state.start_date   = st.date_input("Дата старта", value=st.session_state.start_date)
    st.session_state.target_loss  = st.number_input("Цель снижения (кг)", 1.0, 100.0, value=st.session_state.target_loss, step=0.5)
    st.session_state.weekly_loss  = st.number_input("Скорость (кг/нед)", 0.1, 3.0, value=st.session_state.weekly_loss, step=0.05)

st.title("🏃‍♀️ Трекер веса — мобильная версия")

c1, c2, c3 = st.columns([1,1,1])
with c1:
    d = st.date_input("📅 Дата", value=date.today())
with c2:
    w = st.number_input("⚖️ Вес (кг)", min_value=0.0, max_value=500.0, step=0.1, format="%.1f")
with c3:
    kcal = st.number_input("🔥 Калории (ккал)", min_value=0, max_value=20000, step=10)

c4, c5, c6 = st.columns([1,1,1])
with c4:
    prot = st.number_input("🍗 Белки (г)", min_value=0, max_value=400, step=1)
with c5:
    fat  = st.number_input("🥑 Жиры (г)", min_value=0, max_value=400, step=1)
with c6:
    carb = st.number_input("🍚 Углеводы (г)", min_value=0, max_value=1000, step=1)

c7, c8, c9 = st.columns([1,1,2])
with c7:
    ttype = st.selectbox("🏋️ Тип тренировки", ["Силовые + Аквафитнес","Ходьба 10 км","Отдых"], index=0)
with c8:
    done = st.selectbox("✅ Выполнено", ["", "✅", "❌"], index=0)
with c9:
    steps = st.number_input("🚶 Шаги", min_value=0, max_value=200000, step=100)

note = st.text_area("📝 Заметки", placeholder="Самочувствие, цикл, сон...")

col_btn1, col_btn2 = st.columns(2)
save_clicked = col_btn1.button("💾 Сохранить", use_container_width=True)
quick_done   = col_btn2.button("✔️ Отметить день (✅)", use_container_width=True)

if quick_done:
    done = "✅"

if save_clicked or quick_done:
    entry = {
        "Дата": d,
        "Вес (кг)": w,
        "Калории (ккал)": kcal,
        "Белки (г)": prot,
        "Жиры (г)": fat,
        "Углеводы (г)": carb,
        "Тип тренировки": ttype,
        "Выполнено": done,
        "Шаги": steps,
        "Заметки": note
    }
    try:
        upsert_row(entry)
        st.success("Данные сохранены в Google Sheets ✅")
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")

st.divider()

df = read_df()
st.subheader("Последние записи")
if df.empty:
    st.info("Пока нет записей.")
else:
    st.dataframe(df.sort_values("Дата", ascending=False).head(10), use_container_width=True)

cur_w = df["Вес (кг)"].dropna().iloc[-1] if not df.dropna(subset=["Вес (кг)"]).empty else None
goal_w = st.session_state.start_weight - st.session_state.target_loss
loss_total = (st.session_state.start_weight - cur_w) if cur_w is not None else None
target_pct = (loss_total / st.session_state.target_loss) if (loss_total is not None and st.session_state.target_loss > 0) else None

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Текущий вес", f"{cur_w:.1f}" if cur_w is not None else "—")
m2.metric("Сброшено всего", f"{loss_total:.1f}" if loss_total is not None else "—")
m3.metric("Прогресс к цели", f"{target_pct*100:.1f}%" if target_pct is not None else "—")
m4.metric("Целевой вес", f"{goal_w:.1f}")
m5.metric("Скорость", f"{st.session_state.weekly_loss:.2f} кг/нед")

plan = forecast_df(st.session_state.start_date, st.session_state.start_weight, st.session_state.weekly_loss, days=400, goal_weight=goal_w)
dfc = df.copy()
if not dfc.empty:
    dfc["Дата"] = pd.to_datetime(dfc["Дата"])
chart_df = pd.merge(plan, dfc[["Дата","Вес (кг)"]], on="Дата", how="left")

st.subheader("📈 Вес: Факт vs План")
chart = alt.Chart(chart_df).transform_fold(
    ["Вес (кг)", "План (кг)"], as_=["Серия", "Значение"]
).mark_line().encode(
    x=alt.X("Дата:T", title="Дата"),
    y=alt.Y("Значение:Q", title="Вес (кг)"),
    color="Серия:N"
).properties(height=360)
st.altair_chart(chart, use_container_width=True)

