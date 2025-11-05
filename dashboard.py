# dashboard.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

st.set_page_config(page_title="Immer Miau — Dashboard", page_icon="😼", layout="wide")

# IMPORTANT: use SERVICE ROLE key here (server-only, private app)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

SEAT_OPTIONS = ["White", "Blue", "Pink"]

def fmt_m(n):
    try:
        n = float(n)
        return f"{n/1_000_000:.1f}M"
    except:
        return "—"

# Language toggle
if "lang" not in st.session_state:
    st.session_state.lang = "en"
lang = st.sidebar.selectbox(
    t("language", st.session_state.lang),
    options=list(LANGS.keys()),
    format_func=lambda k: {"en": "English", "de": "Deutsch"}.get(k, k),
    index=list(LANGS.keys()).index(st.session_state.lang),
)
st.session_state.lang = lang

st.title(t("app_title_private", lang))
st.caption(t("private_caption", lang))

@st.cache_data(ttl=30)
def load_df():
    data = sb.table("players").select("*").order("player_name").execute().data or []
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=[
            "player_name","current_alliance","total_hero_power","combat_power_1st_squad",
            "expected_transfer_seat_color","created_at","updated_at","submitted_ip"
        ])
    return df

def upsert(row: dict):
    row["updated_at"] = datetime.utcnow().isoformat()
    sb.table("players").upsert(row, on_conflict="player_name").execute()

def delete(name: str):
    sb.table("players").delete().eq("player_name", name).execute()

df = load_df()

# Summary
c1, c2, c3 = st.columns(3)
with c1:
    st.metric(t("players", lang), len(df))
with c2:
    try:
        st.metric(t("avg_hero_power", lang), round(pd.to_numeric(df["total_hero_power"], errors="coerce").mean()))
    except:
        st.metric(t("avg_hero_power", lang), "N/A")
with c3:
    st.metric(t("last_updated", lang), df["updated_at"].max() if not df.empty else "N/A")

# Display table with pretty M columns
df_display = df.copy()
if not df_display.empty:
    df_display["total_hero_power (M)"] = df_display["total_hero_power"].apply(fmt_m)
    df_display["combat_power_1st_squad (M)"] = df_display["combat_power_1st_squad"].apply(fmt_m)

st.subheader(t("roster", lang))
show_cols = ["player_name","current_alliance","total_hero_power (M)","combat_power_1st_squad (M)","expected_transfer_seat_color","updated_at"] \
            if not df_display.empty else df_display.columns
st.dataframe(df_display[show_cols] if not df_display.empty else df_display, use_container_width=True, hide_index=True)

# Add or Edit
st.subheader(t("add_or_edit", lang))
with st.form("edit_form", clear_on_submit=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        player_name = st.text_input(t("player_name", lang), placeholder="unique key")
        current_alliance = st.text_input(t("current_alliance", lang))
        seat_color = st.selectbox(t("seat_color", lang), options=SEAT_OPTIONS)
    with c2:
        total_hero_power = st.number_input(
            t("total_hero_power", lang),
            min_value=0.0, step=1.0, format="%.0f",
            help=t("enter_full_number", lang)
        )
        st.caption(f"Preview: {fmt_m(total_hero_power)}")
    with c3:
        combat_power = st.number_input(
            t("combat_power_1st", lang),
            min_value=0.0, step=1.0, format="%.0f",
            help=t("enter_full_number", lang)
        )
        st.caption(f"Preview: {fmt_m(combat_power)}")
        mode = st.radio(t("mode", lang), [t("add_update", lang), t("delete", lang)], horizontal=True)

    submit = st.form_submit_button(t("apply", lang))

if submit:
    if not player_name.strip():
        st.error(t("required_name", lang))
    else:
        if mode == t("delete", lang):
            delete(player_name.strip())
            st.success(f"{t('deleted', lang)} {player_name}")
        else:
            upsert({
                "player_name": player_name.strip(),
                "current_alliance": current_alliance.strip() or None,
                "total_hero_power": float(total_hero_power) if total_hero_power else None,
                "combat_power_1st_squad": float(combat_power) if combat_power else None,
                "expected_transfer_seat_color": seat_color,
            })
            st.success(f"{t('saved', lang)} {player_name}")
        st.cache_data.clear()
        st.experimental_rerun()

# Export
st.subheader(t("export", lang))
st.download_button(
    t("download_csv", lang),
    data=df.to_csv(index=False),
    file_name="immer_miau_roster.csv",
    mime="text/csv",
)
