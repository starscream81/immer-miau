# dashboard.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

# ──────────────────────────────────────────────────────────────────────────────
# App config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Immer Miau – Dashboard", page_icon="📊", layout="wide")

# Supabase (service role key so editors can update safely)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

SEAT_OPTIONS = ["White", "Blue", "Pink"]

# Language
lang = st.sidebar.selectbox("🌍 Language", options=list(LANGS.keys()), index=list(LANGS.keys()).index("en"))
t.set_lang(lang)

st.title("Immer Miau – Admin Dashboard")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def fetch_players() -> pd.DataFrame:
    """Pull all rows from players into a DataFrame."""
    try:
        res = sb.table("players").select("*").execute()
        rows = res.data or []
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        rows = []
    if not rows:
        return pd.DataFrame(columns=[
            "player_name", "current_alliance", "total_hero_power",
            "combat_power_1st_squad", "expected_transfer_seat_color",
            "edit_code", "created_at", "updated_at"
        ])
    df = pd.DataFrame(rows)
    # Ensure expected columns exist
    for col in ["player_name", "current_alliance", "total_hero_power",
                "combat_power_1st_squad", "expected_transfer_seat_color",
                "edit_code", "created_at", "updated_at"]:
        if col not in df.columns:
            df[col] = None
    # Nice types
    for col in ["total_hero_power", "combat_power_1st_squad"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Sort newest first by updated_at if present
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")
        df = df.sort_values("updated_at", ascending=False)
    return df

def numeric(n):
    try:
        return int(n)
    except Exception:
        return n

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar: Filters & Sort
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.subheader(t("filters"))

alliance_query = st.sidebar.text_input(t("filter_alliance"))
seat_filter = st.sidebar.multiselect(t("filter_seat"), SEAT_OPTIONS, default=SEAT_OPTIONS)

SORT_FIELDS = {
    "Player Name": "player_name",
    "Alliance": "current_alliance",
    "Total Hero Power": "total_hero_power",
    "Combat Power 1st Squad": "combat_power_1st_squad",
    "Seat Color": "expected_transfer_seat_color",
    "Last Updated": "updated_at",
}
sort_field_label = st.sidebar.selectbox(t("sort_by"), list(SORT_FIELDS.keys()), index=5 if "Last Updated" in SORT_FIELDS else 0)
sort_col = SORT_FIELDS[sort_field_label]
sort_ascending = st.sidebar.checkbox(t("sort_asc"), value=False)

# ──────────────────────────────────────────────────────────────────────────────
# Data view
# ──────────────────────────────────────────────────────────────────────────────
df = fetch_players()

# Apply filters
df_view = df.copy()
if alliance_query:
    df_view = df_view[df_view["current_alliance"].fillna("").str.contains(alliance_query, case=False, na=False)]
if seat_filter:
    df_view = df_view[df_view["expected_transfer_seat_color"].isin(seat_filter)]

# Sort
if sort_col in df_view.columns:
    df_view = df_view.sort_values(sort_col, ascending=sort_ascending, kind="mergesort")

st.caption(f"Showing {len(df_view)} of {len(df)} records")

# Hide sensitive PIN from the main grid
columns_to_show = [
    "player_name", "current_alliance", "total_hero_power",
    "combat_power_1st_squad", "expected_transfer_seat_color", "updated_at"
]
present_cols = [c for c in columns_to_show if c in df_view.columns]

st.dataframe(df_view[present_cols], use_container_width=True)

# Export filtered CSV
csv = df_view[present_cols].to_csv(index=False).encode("utf-8")
st.download_button(label=t("download_csv"), data=csv, file_name="immer-miau-filtered.csv", mime="text/csv")

st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Admin tools: Reset a player's PIN (edit_code)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Admin tools: Reset Player PIN")

def _valid_pin(pin: str) -> bool:
    return pin.isdigit() and 4 <= len(pin) <= 6

with st.form("reset_pin_form", clear_on_submit=False):
    # Choose player
    name_options = sorted(df["player_name"].dropna().unique().tolist())
    player_to_reset = st.selectbox("Select Player", options=name_options)
    new_pin = st.text_input("New PIN (4–6 digits)", type="password", max_chars=6, help="Digits only. Example: 1234")
    confirm_pin = st.text_input("Confirm New PIN", type="password", max_chars=6)

    submitted = st.form_submit_button("Reset PIN")
    if submitted:
        if not player_to_reset:
            st.warning("Please select a player.")
        elif not new_pin or not confirm_pin:
            st.warning("Please enter and confirm the new PIN.")
        elif new_pin != confirm_pin:
            st.warning("PINs do not match.")
        elif not _valid_pin(new_pin):
            st.warning("PIN must be 4–6 digits (numbers only).")
        else:
            try:
                # Service role key bypasses RLS; we can update directly
                sb.table("players").update({
                    "edit_code": new_pin,
                    "updated_at": datetime.utcnow().isoformat(),
                }).eq("player_name", player_to_reset).execute()
                st.success(f"✅ PIN reset for **{player_to_reset}**.")
            except Exception as e:
                st.error(f"Failed to reset PIN: {e}")

st.markdown("PINs are not displayed here for security; resetting will overwrite the previous PIN immediately.")
