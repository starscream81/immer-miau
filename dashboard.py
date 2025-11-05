"""
Immer Miau — Dashboard (Streamlit) — Fix B (use player_name instead of id)
--------------------------------------------------------------------------
Features:
- Language toggle (English, Deutsch) for all UI text and column headers
- Keeps player_name values EXACTLY as stored (never translated)
- Filters: alliance contains, seat color chips, sort by column, ascending toggle
- CSV download for the filtered view
- Admin tool: reset a player's PIN (by player_name) with validation
- Supabase read/write (players table assumed)
"""

import io
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Immer Miau — Dashboard", page_icon="🛠️", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", ""))

@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

sb = get_client()

# ------------------------------------------------------------------------------
# i18n (translations)
# ------------------------------------------------------------------------------
LANGS: Dict[str, str] = {"en": "English", "de": "Deutsch"}

UI = {
    "en": {
        "title": "Immer Miau — Dashboard",
        "filter_panel": "Filter & Sorting",
        "filter_alliance": "Filter by current alliance (contains)",
        "seat_color": "Seat color",
        "sort_by": "Sort by",
        "ascending": "Sort ascending",
        "download_csv": "Download CSV (filtered)",
        "showing": "Showing {n} of {total} records",
        "admin_tools": "Admin tools: Reset Player PIN",
        "select_player": "Select Player",
        "new_pin": "New PIN (4–6 digits)",
        "confirm_pin": "Confirm New PIN",
        "reset_pin": "Reset PIN",
        "pin_note": "PINs are not displayed here for security; resetting will overwrite the previous PIN immediately.",
        # column headers
        "col_player_name": "player_name",  # never translate
        "col_current_alliance": "Current Alliance",
        "col_total_power": "Total Hero Power",
        "col_1st_squad": "Combat Power (1st Squad)",
        "col_seat_color": "Expected Transfer Seat Color",
        "col_updated_at": "Updated At",
        # misc
        "success_reset": "PIN reset for {name}.",
        "error_pin_match": "PINs do not match.",
        "error_pin_range": "PIN must be 4 to 6 digits.",
        "error_no_player": "No players found.",
    },
    "de": {
        "title": "Immer Miau – Dashboard",
        "filter_panel": "Filter & Sortierung",
        "filter_alliance": "Nach aktueller Allianz filtern (enthält)",
        "seat_color": "Sitzfarbe",
        "sort_by": "Sortieren nach",
        "ascending": "Aufsteigend sortieren",
        "download_csv": "CSV herunterladen (gefiltert)",
        "showing": "Es werden {n} von {total} Einträgen angezeigt",
        "admin_tools": "Admin-Tools: Spieler-PIN zurücksetzen",
        "select_player": "Spieler auswählen",
        "new_pin": "Neue PIN (4–6 Ziffern)",
        "confirm_pin": "Neue PIN bestätigen",
        "reset_pin": "PIN zurücksetzen",
        "pin_note": "PINs werden hier aus Sicherheitsgründen nicht angezeigt; das Zurücksetzen überschreibt die vorherige PIN sofort.",
        # column headers
        "col_player_name": "player_name",  # do not translate
        "col_current_alliance": "Aktuelle Allianz",
        "col_total_power": "Gesamte Heldenstärke",
        "col_1st_squad": "Kampfkraft (1. Trupp)",
        "col_seat_color": "Erwartete Sitzfarbe beim Transfer",
        "col_updated_at": "Zuletzt aktualisiert",
        # misc
        "success_reset": "PIN für {name} zurückgesetzt.",
        "error_pin_match": "PINs stimmen nicht überein.",
        "error_pin_range": "PIN muss 4 bis 6 Ziffern haben.",
        "error_no_player": "Keine Spieler gefunden.",
    },
}

SEAT_COLOR = {
    "en": {"White": "White", "Blue": "Blue", "Pink": "Pink"},
    "de": {"White": "Weiß", "Blue": "Blau", "Pink": "Pink"},
}

SORT_CHOICES = [
    ("updated_at", {"en": "Last Updated", "de": "Zuletzt aktualisiert"}),
    ("total_hero_power", {"en": "Total Hero Power", "de": "Gesamte Heldenstärke"}),
    ("combat_power_1st_squad", {"en": "Combat Power (1st Squad)", "de": "Kampfkraft (1. Trupp)"}),
]

def t(key: str, lang: str) -> str:
    return UI.get(lang, UI["en"]).get(key, key)

# ------------------------------------------------------------------------------
# Language selector
# ------------------------------------------------------------------------------
def lang_selector() -> str:
    default = st.session_state.get("lang", "de")
    lang = st.sidebar.selectbox(
        "Language",
        list(LANGS.keys()),
        index=list(LANGS.keys()).index(default),
        format_func=lambda k: LANGS[k],
    )
    st.session_state.lang = lang
    return lang

lang = lang_selector()

# ------------------------------------------------------------------------------
# Data access
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=30)
def fetch_players() -> pd.DataFrame:
    try:
        res = (
            sb.table("players")
            .select("player_name, current_alliance, total_hero_power, combat_power_1st_squad, expected_transfer_seat_color, updated_at")
            .order("updated_at", desc=True)
            .limit(1000)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error("Fetch failed (likely GRANTS/RLS/columns).")
        st.exception(e)
        return pd.DataFrame()

# ------------------------------------------------------------------------------
# UI – main
# ------------------------------------------------------------------------------
st.title(t("title", lang))
st.sidebar.header(t("filter_panel", lang))

# Filters
alliance_like = st.sidebar.text_input(t("filter_alliance", lang))
seat_opts = ["White", "Blue", "Pink"]
seat_mult = st.sidebar.multiselect(t("seat_color", lang), options=seat_opts, default=seat_opts)
sort_key_labels = {k: v[lang] for k, v in SORT_CHOICES}
sort_key = st.sidebar.selectbox(t("sort_by", lang), options=[k for k, _ in SORT_CHOICES], format_func=lambda k: sort_key_labels[k])
ascending = st.sidebar.checkbox(t("ascending", lang), value=False)

df = fetch_players()
total_records = len(df)

if not df.empty:
    if alliance_like.strip():
        df = df[df["current_alliance"].str.contains(alliance_like, case=False, na=False)]
    if seat_mult:
        df = df[df["expected_transfer_seat_color"].isin(seat_mult)]
    if sort_key in df.columns:
        df = df.sort_values(by=sort_key, ascending=ascending, kind="mergesort")
else:
    st.info(t("error_no_player", lang))

# ------------------------------------------------------------------------------
# Table display
# ------------------------------------------------------------------------------
_df = df.copy()
if "expected_transfer_seat_color" in _df.columns:
    _df["expected_transfer_seat_color"] = _df["expected_transfer_seat_color"].map(SEAT_COLOR.get(lang, {})).fillna(_df["expected_transfer_seat_color"])

cols_map = {
    "player_name": t("col_player_name", lang),
    "current_alliance": t("col_current_alliance", lang),
    "total_hero_power": t("col_total_power", lang),
    "combat_power_1st_squad": t("col_1st_squad", lang),
    "expected_transfer_seat_color": t("col_seat_color", lang),
    "updated_at": t("col_updated_at", lang),
}

_df = _df.rename(columns=cols_map)
st.caption(t("showing", lang).format(n=len(_df), total=total_records))
st.dataframe(_df[[c for c in cols_map.values() if c in _df.columns]], use_container_width=True)

# CSV download
csv = _df.to_csv(index=False).encode("utf-8")
st.download_button(label=t("download_csv", lang), data=csv, file_name="players_filtered.csv", mime="text/csv")

# ------------------------------------------------------------------------------
# Admin Tools – Reset PIN
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader(t("admin_tools", lang))

players_for_select: List[Dict] = df[["player_name"]].to_dict("records") if not df.empty else []

if players_for_select:
    players_for_select = sorted(players_for_select, key=lambda r: (r["player_name"] or "").lower())
    names = [r["player_name"] for r in players_for_select]
    idx = st.selectbox(t("select_player", lang), options=range(len(names)), format_func=lambda i: names[i])

    pin1 = st.text_input(t("new_pin", lang))
    pin2 = st.text_input(t("confirm_pin", lang))

    if st.button(t("reset_pin", lang)):
        if pin1 != pin2:
            st.error(t("error_pin_match", lang))
        elif not pin1.isdigit() or not (4 <= len(pin1) <= 6):
            st.error(t("error_pin_range", lang))
        else:
            player_name = players_for_select[idx]["player_name"]
            try:
                sb.table("players").update({"edit_pin": pin1}).eq("player_name", player_name).execute()
                st.success(t("success_reset", lang).format(name=player_name))
            except Exception as e:
                st.error("PIN update failed. Check RLS or column name.")
                st.exception(e)
else:
    st.info(t("error_no_player", lang))

st.caption(t("pin_note", lang))
