# public_form.py
import os
from datetime import datetime
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

st.set_page_config(page_title="Immer Miau — Submit", page_icon="🐾", layout="centered")

# Supabase (public anon key only for this app)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

SEAT_OPTIONS = ["White", "Blue", "Pink"]

def fmt_millions_preview(n):
    try:
        n = float(n)
        return f"≈ {n/1_000_000:.1f}M"
    except:
        return ""

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

st.title(t("app_title_public", lang))
st.caption(t("note_public", lang))

with st.form("submit_form"):
    player_name = st.text_input(t("player_name", lang), max_chars=80)
    current_alliance = st.text_input(t("current_alliance", lang), max_chars=80)

    col1, col2 = st.columns(2)
    with col1:
        total_hero_power = st.number_input(
            t("total_hero_power", lang),
            min_value=0.0, step=1.0, format="%.0f",
            help=t("enter_full_number", lang)
        )
        st.caption(fmt_millions_preview(total_hero_power))
    with col2:
        combat_power_1st = st.number_input(
            t("combat_power_1st", lang),
            min_value=0.0, step=1.0, format="%.0f",
            help=t("enter_full_number", lang)
        )
        st.caption(fmt_millions_preview(combat_power_1st))

    seat_color = st.selectbox(
        t("seat_color", lang),
        options=SEAT_OPTIONS,
        help=t("seat_color_hint", lang)
    )

    submitted = st.form_submit_button(t("submit", lang))

if submitted:
    if not player_name.strip():
        st.error(t("required_name", lang))
        st.stop()

    row = {
        "player_name": player_name.strip(),
        "current_alliance": current_alliance.strip() or None,
        "total_hero_power": float(total_hero_power) if total_hero_power else None,
        "combat_power_1st_squad": float(combat_power_1st) if combat_power_1st else None,
        "expected_transfer_seat_color": seat_color,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "submitted_ip": None,  # can be filled by a proxy later if you add one
    }

    try:
        # upsert so users can correct their own entry by Player Name
        sb.table("players").upsert(row, on_conflict="player_name").execute()
        st.success(t("thanks", lang))
    except Exception as e:
        st.error(f"{t('submit_failed', lang)} ({e})")
