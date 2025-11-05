# public_form.py
import os
from datetime import datetime
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

st.set_page_config(
    page_title="Immer Miau – Submit",
    page_icon="🐾",
    layout="centered"
)

# Supabase (values come from Streamlit Secrets / env)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

SEAT_OPTIONS = ["White", "Blue", "Pink"]

# Language selector
lang = st.selectbox(
    "🌍 Choose your language / Wählen Sie Ihre Sprache",
    options=list(LANGS.keys())
)
t.set_lang(lang)

st.title(t("title"))

def _is_valid_pin(pin: str) -> bool:
    return pin.isdigit() and 4 <= len(pin) <= 6

with st.form("player_form"):
    player_name = st.text_input(t("player_name"))
    alliance = st.text_input(t("current_alliance"))
    total_power = st.number_input(f"{t('total_power')} (Enter whole number)", min_value=0, step=1)
    combat_power = st.number_input(f"{t('combat_power')} (Enter whole number)", min_value=0, step=1)
    seat_color = st.selectbox(t("seat_color"), SEAT_OPTIONS)

    st.markdown("")

    # Update mode using a PIN (edit_code)
    update_mode = st.checkbox("Update an existing entry?")
    create_pin = ""
    edit_pin = ""
    if update_mode:
        edit_pin = st.text_input("Enter your PIN (4–6 digits)", type="password", max_chars=6)
    else:
        create_pin = st.text_input("Choose a PIN (4–6 digits) — you’ll use this to edit later", type="password", max_chars=6)

    submit_button = st.form_submit_button(t("submit"))

    if submit_button:
        if not player_name or not alliance:
            st.warning(t("warning"))
        else:
            try:
                if update_mode:
                    if not _is_valid_pin(edit_pin):
                        st.warning("Please enter a valid 4–6 digit PIN to update.")
                    else:
                        payload = {
                            "player_name": player_name.strip(),
                            "current_alliance": alliance.strip(),
                            "total_hero_power": int(total_power),
                            "combat_power_1st_squad": int(combat_power),
                            "expected_transfer_seat_color": seat_color,
                            "updated_at": datetime.utcnow().isoformat(),
                            "edit_code": edit_pin.strip(),
                        }
                        # RLS will only allow this if the PIN matches the row for this player_name
                        sb.table("players").update(payload).eq("player_name", payload["player_name"]).execute()
                        st.success("✅ Updated successfully.")
                else:
                    if not _is_valid_pin(create_pin):
                        st.warning("Please choose a valid 4–6 digit PIN (numbers only).")
                    else:
                        payload = {
                            "player_name": player_name.strip(),
                            "current_alliance": alliance.strip(),
                            "total_hero_power": int(total_power),
                            "combat_power_1st_squad": int(combat_power),
                            "expected_transfer_seat_color": seat_color,
                            "created_at": datetime.utcnow().isoformat(),
                            "updated_at": datetime.utcnow().isoformat(),
                            "edit_code": create_pin.strip(),
                        }
                        sb.table("players").insert(payload).execute()
                        st.success("✅ Submission successful! Keep your PIN — you’ll need it to edit.")
                        st.info("🔐 Your PIN is the number you just chose. If you forget it, ask an editor to reset it.")
            except Exception as e:
                msg = str(e)
                # Friendly duplicate-name message (unique constraint violation)
                if "duplicate key value" in msg or "23505" in msg:
                    st.warning("That player name already exists — please use Update mode and enter your PIN.")
                # PIN mismatch during update typically surfaces as an RLS violation
                elif "violates row-level security" in msg or "42501" in msg:
                    st.warning("Update blocked. The PIN is incorrect or the player name was not found.")
                else:
                    st.error(f"{t('error')}: {msg}")
