# public_form.py
import os
from datetime import datetime
import streamlit as st
from supabase import create_client
from i18n import t, LANGS  # your i18n.py

# ---------------------------------------------------------------------
# Page config (collapsed sidebar is nicer on phones)
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Immer Miau – Submit",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", ""))
sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Canonical DB values for seat color
SEAT_OPTIONS = ["White", "Blue", "Pink"]

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def valid_pin(pin: str) -> bool:
    return bool(pin) and pin.isdigit() and 4 <= len(pin) <= 6

def now_iso() -> str:
    return datetime.utcnow().isoformat()

def try_update_with_pin(table_payload: dict, player_name: str, pin_value: str):
    """
    Prefer new column 'edit_pin'. If it doesn't exist, fall back to legacy 'edit_code'.
    """
    try:
        sb.table("players").update(table_payload).eq("player_name", player_name).eq("edit_pin", pin_value).execute()
        return True
    except Exception as e1:
        msg = str(e1)
        if ("edit_pin" in msg and "does not exist" in msg) or ("column edit_pin" in msg):
            sb.table("players").update(table_payload).eq("player_name", player_name).eq("edit_code", pin_value).execute()
            return True
        raise

def try_insert_with_pin(table_payload: dict, pin_value: str):
    """
    Prefer new column 'edit_pin'. Fall back to legacy 'edit_code' if needed.
    """
    payload = dict(table_payload)
    payload["edit_pin"] = pin_value
    try:
        sb.table("players").insert(payload).execute()
        return True
    except Exception as e1:
        msg = str(e1)
        if ("edit_pin" in msg and "does not exist" in msg) or ("column edit_pin" in msg):
            payload = dict(table_payload)
            payload["edit_code"] = pin_value
            sb.table("players").insert(payload).execute()
            return True
        raise

# ---------------------------------------------------------------------
# Language picker + title + note
# ---------------------------------------------------------------------
lang = st.selectbox(
    "🌍 Choose your language / Wählen Sie Ihre Sprache",
    options=list(LANGS.keys()),
    index=list(LANGS.keys()).index("en") if "en" in LANGS else 0,
    format_func=lambda k: k
)
t.set_lang(lang)

st.title(t("title"))
st.info(t("seat_note"))  # localized note under the title

# Optional: Mobile layout toggle (compact styles, full-width button)
mobile = st.toggle("Mobile layout", value=False, help="Optimized layout for phones")
if mobile:
    st.markdown("""
    <style>
      .stTextInput input, .stNumberInput input, .stSelectbox select { font-size: 0.95rem; }
      .stButton > button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------
with st.form("player_form", clear_on_submit=False):
    player_name = st.text_input(t("player_name"))
    alliance = st.text_input(t("current_alliance"))

    # Number inputs + localized hint
    total_power = st.number_input(f"{t('total_power')} ({t('whole_hint')})", min_value=0, step=1)
    combat_power = st.number_input(f"{t('combat_power')} ({t('whole_hint')})", min_value=0, step=1)

    # Seat color: blank by default, optional
    seat_options_with_blank = [""] + SEAT_OPTIONS
    seat_color = st.selectbox(
        t("seat_color"),
        options=seat_options_with_blank,
        index=0,
        format_func=lambda v: "" if v == "" else v,
        help=t("seat_note"),
    )

    st.markdown("---")

    # Update vs new
    update_mode = st.checkbox("Update an existing entry?")
    if update_mode:
        pin_update = st.text_input("Enter your PIN (4–6 digits)", type="password", max_chars=6)
        pin_create = ""
    else:
        pin_create = st.text_input("Choose a PIN (4–6 digits)", type="password", max_chars=6)
        pin_update = ""

    submitted = st.form_submit_button(t("submit"), use_container_width=mobile)

# ---------------------------------------------------------------------
# Handle submit
# ---------------------------------------------------------------------
if submitted:
    if not player_name or not alliance:
        st.warning(t("warning"))
    else:
        try:
            if update_mode:
                if not valid_pin(pin_update):
                    st.warning("Please enter a valid 4–6 digit PIN to update.")
                else:
                    payload = {
                        "player_name": player_name.strip(),
                        "current_alliance": alliance.strip(),
                        "total_hero_power": int(total_power),
                        "combat_power_1st_squad": int(combat_power),
                        "updated_at": now_iso(),
                    }
                    if seat_color:
                        payload["expected_transfer_seat_color"] = seat_color

                    try_update_with_pin(payload, player_name.strip(), pin_update.strip())
                    st.success(t("success"))

            else:
                if not valid_pin(pin_create):
                    st.warning("Please choose a valid 4–6 digit PIN (numbers only).")
                else:
                    payload = {
                        "player_name": player_name.strip(),
                        "current_alliance": alliance.strip(),
                        "total_hero_power": int(total_power),
                        "combat_power_1st_squad": int(combat_power),
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    }
                    if seat_color:
                        payload["expected_transfer_seat_color"] = seat_color

                    try_insert_with_pin(payload, pin_create.strip())
                    st.success(t("success"))

        except Exception as e:
            msg = str(e)
            if "duplicate key value" in msg or "23505" in msg:
                st.warning("That player name already exists — switch to Update mode and enter your PIN.")
            elif "violates row-level security" in msg or "permission denied" in msg or "42501" in msg:
                st.warning("Update blocked. Wrong PIN or player not found.")
            else:
                st.error(f"{t('error')} {msg}")

# ---------------------------------------------------------------------
# Buy Me a Beer button
# ---------------------------------------------------------------------
st.markdown(
    """
    ---
    <style>
      .beer-button {
        background-color: #f5c518;
        color: black;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.3s ease;
        text-decoration: none;
      }
      .beer-button:hover {
        background-color: #ffd84d;
      }
    </style>
    <div style='text-align: center; margin-top: 1.5em;'>
      <a class='beer-button' href='https://paypal.me/KMahana' target='_blank'>
        🍺 Buy Me a Beer
      </a>
    </div>
    """,
    unsafe_allow_html=True
)