# dashboard.py
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client
from i18n import t, LANGS

st.set_page_config(page_title="Immer Miau — Private Dashboard", page_icon="😼", layout="wide")

# ---- Supabase (read from env or Streamlit Secrets; no keys in code) ----
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    st.error("Missing Supabase configuration. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Settings → Secrets.")
    st.stop()
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ---- Constants ----
SEAT_OPTIONS = ["White", "Blue", "Pink"]
TABLE = "players"

def fmt_m(n):
    try:
        n = float(n)
        return f"{n/1_000_000:.1f}M"
    except:
        return "—"

# ---- Language selector (matches i18n.py) ----
if "lang" not in st.session_state:
    st.session_state.lang = "en"
lang = st.sidebar.selectbox(
    "🌐 Language",
    options=list(LANGS.keys()),
    index=list(LANGS.keys()).index(st.session_state.lang) if st.session_state.lang in LANGS else 0
)
st.session_state.lang = lang
t.set_lang(lang)

st.title(t("title"))  # reuse the title key from i18n

# ---- Data helpers ----
@st.cache_data(ttl=30)
def load_df() -> pd.DataFrame:
    data = sb.table(TABLE).select("*").order("player_name").execute().data or []
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=[
            "player_name",
            "current_alliance",
            "total_hero_power",
            "combat_power_1st_squad",
            "expected_transfer_seat_color",
            "created_at",
            "updated_at",
            "submitted_ip",
        ])
    return df

def upsert_row(row: dict):
    row["updated_at"] = datetime.utcnow().isoformat()
    sb.table(TABLE).upsert(row, on_conflict="player_name").execute()

def delete_row(name: str):
    sb.table(TABLE).delete().eq("player_name", name).execute()

df = load_df()

# ---- FILTERS + SORT (in sidebar) ----
st.sidebar.header("Filters & Sort")

alliance_query = st.sidebar.text_input("Filter by Current Alliance (contains)")
seat_filter = st.sidebar.multiselect("Seat Color", SEAT_OPTIONS, default=SEAT_OPTIONS)

# Programmatic sort (table also supports click-to-sort)
SORT_FIELDS = {
    "Player Name": "player_name",
    "Current Alliance": "current_alliance",
    "Total Hero Power": "total_hero_power",
    "Combat Power 1st Squad": "combat_power_1st_squad",
    "Seat Color": "expected_transfer_seat_color",
    "Last Updated": "updated_at",
}
sort_field_label = st.sidebar.selectbox("Sort by", list(SORT_FIELDS.keys()), index=0)
sort_field = SORT_FIELDS[sort_field_label]
sort_ascending = st.sidebar.checkbox("Sort ascending", value=True)

# Apply filters
df_filtered = df.copy()
if alliance_query:
    df_filtered = df_filtered[df_filtered["current_alliance"].fillna("").str.contains(alliance_query, case=False, na=False)]
if seat_filter:
    df_filtered = df_filtered[df_filtered["expected_transfer_seat_color"].isin(seat_filter)]

# Ensure numeric types for proper sorting and metrics
for col in ["total_hero_power", "combat_power_1st_squad"]:
    df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce")

# Apply programmatic sort
df_filtered = df_filtered.sort_values(by=sort_field, ascending=sort_ascending, na_position="last")

# ---- Summary ----
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Players", len(df_filtered))
with c2:
    try:
        st.metric(t("total_power"), round(pd.to_numeric(df_filtered["total_hero_power"], errors="coerce").mean()))
    except:
        st.metric(t("total_power"), "—")
with c3:
    st.metric("Last Updated", (df_filtered["updated_at"].max() if not df_filtered.empty else "—"))

# ---- Table (pretty M columns) ----
if not df_filtered.empty:
    df_display = df_filtered.copy()
    df_display["Total Hero Power (M)"] = df_display["total_hero_power"].apply(fmt_m)
    df_display["Combat Power 1st Squad (M)"] = df_display["combat_power_1st_squad"].apply(fmt_m)
    show_cols = [
        "player_name",
        "current_alliance",
        "Total Hero Power (M)",
        "Combat Power 1st Squad (M)",
        "expected_transfer_seat_color",
        "updated_at",
    ]
    st.subheader("Roster")
    st.dataframe(df_display[show_cols], use_container_width=True, hide_index=True)
else:
    st.info("No matching rows. Try clearing filters.")

# ---- Add / Update / Delete ----
st.subheader(t("add_or_edit") if "add_or_edit" in LANGS.get(lang, {}) else "Add or Edit")

with st.form("edit_form", clear_on_submit=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        player_name = st.text_input(t("player_name"))
        current_alliance = st.text_input(t("current_alliance"))
        seat_color = st.selectbox("Expected Transfer Seat Color", SEAT_OPTIONS)
    with c2:
        total_power = st.number_input(t("total_power"), min_value=0, step=1, help=t("total_power"))
        st.caption(f"Preview: {fmt_m(total_power)}")
    with c3:
        combat_power = st.number_input(t("combat_power"), min_value=0, step=1, help=t("combat_power"))
        st.caption(f"Preview: {fmt_m(combat_power)}")
        mode = st.radio("Mode", ["Add/Update", "Delete"], horizontal=True)

    apply_btn = st.form_submit_button("Apply")

if apply_btn:
    if not player_name.strip():
        st.warning(t("warning"))
    else:
        if mode == "Delete":
            delete_row(player_name.strip())
            st.success(f"Deleted {player_name}")
        else:
            upsert_row({
                "player_name": player_name.strip(),
                "current_alliance": (current_alliance or "").strip() or None,
                "total_hero_power": int(total_power) if total_power is not None else None,
                "combat_power_1st_squad": int(combat_power) if combat_power is not None else None,
                "expected_transfer_seat_color": seat_color,
            })
            st.success(f"Saved {player_name}")
        st.cache_data.clear()
        st.experimental_rerun()

# ---- Export ----
st.subheader("Export")
st.download_button(
    "Download CSV (filtered)",
    data=df_filtered.to_csv(index=False),
    file_name="immer_miau_roster_filtered.csv",
    mime="text/csv",
)
