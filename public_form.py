# public_form.py
import os
from datetime import datetime
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

# Page config
st.set_page_config(
    page_title="Immer Miau – Submit",
    page_icon="🐾",
    layout="centered"
)

# Load Supabase credentials from environment
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Seat color dropdown
SEAT_OPTIONS = ["White", "Blue", "Pink"]

# Language selector
lang = st.selectbox("🌍 Choose your language / Wählen Sie Ihre Sprache", options=list(LANGS.keys()))
st.set_lang(lang)

st.title(t("title"))

# Player input form
with st.form("player_form"):
    player_name = st.text_input(t("player_name"))
    alliance = st.text_input(t("current_alliance"))
    total_power = st.number_input(f"{t('total_power')} (Enter whole number)", min_value=0, step=1)
    combat_power = st.number_input(f"{t('combat_power')} (Enter whole number)", min_value=0, step=1)
    seat_color = st.selectbox(t("seat_color"), SEAT_OPTIONS)
    submit_button = st.form_submit_button(t("submit"))

    if submit_button:
        if not player_name or not alliance:
            st.warning(t("warning"))
        else:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "player_name": player_name.strip(),
                "current_alliance": alliance.strip(),
                "total_hero_power": total_power,
                "combat_power_first_squad": combat_power,
                "expected_seat_color": seat_color
            }

            try:
                sb.table("players").insert(data).execute()
                st.success(t("success"))
            except Exception as e:
                st.error(f"{t('error')}: {e}")
