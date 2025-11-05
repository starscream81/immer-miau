"""
Immer Miau — Dashboard (Streamlit) — KPIs + Charts + CET + Fix B
-----------------------------------------------------------------
- Language toggle (English/Deutsch)
- KPIs across the top
- Styled roster table with green gradient and XX.XX M formatting
- CET time display (dd.mm.yyyy HHMM)
- Right-side charts (Top 5 bar, Seat Color pie)
- Admin Tools in sidebar expander
- Updates by player_name (no id)
"""

import io
import os
from typing import Dict, List
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Immer Miau — Dashboard", page_icon="🐱", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY", ""))

@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

sb = get_client()

# ------------------------------------------------------------------------------
# i18n
# ------------------------------------------------------------------------------
LANGS: Dict[str, str] = {"en": "English", "de": "Deutsch"}
UI = {
    "en": {
        "title": "Immer Miau — Dashboard",
        "filter_panel": "Filters & Sorting",
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
        "col_player_name": "player_name",
        "col_current_alliance": "Current Alliance",
        "col_total_power": "Total Hero Power",
        "col_1st_squad": "Combat Power (1st Squad)",
        "col_seat_color": "Expected Transfer Seat Color",
        "col_updated_at": "Updated At",
        # KPI titles
        "kpi_avg_power": "Avg Hero Power",
        "kpi_alliance_combat": "Alliance Combat Score",
        # misc
        "error_no_player": "No players found.",
        "error_pin_match": "PINs do not match.",
        "error_pin_range": "PIN must be 4 to 6 digits.",
        "success_reset": "PIN reset for {name}.",
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
        "col_player_name": "player_name",
        "col_current_alliance": "Aktuelle Allianz",
        "col_total_power": "Gesamte Heldenstärke",
        "col_1st_squad": "Kampfkraft (1. Trupp)",
        "col_seat_color": "Erwartete Sitzfarbe beim Transfer",
        "col_updated_at": "Zuletzt aktualisiert",
        "kpi_avg_power": "Durchschn. Heldenstärke",
        "kpi_alliance_combat": "Allianz-Kampfscore",
        "error_no_player": "Keine Spieler gefunden.",
        "error_pin_match": "PINs stimmen nicht überein.",
        "error_pin_range": "PIN muss 4 bis 6 Ziffern haben.",
        "success_reset": "PIN für {name} zurückgesetzt.",
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
        df = pd.DataFrame(res.data or [])
        if "updated_at" in df.columns:
            df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")
        return df
    except Exception as e:
        st.error("Fetch failed (likely GRANTS/RLS/columns).")
        st.exception(e)
        return pd.DataFrame()

# ------------------------------------------------------------------------------
# Header + KPIs
# ------------------------------------------------------------------------------
st.title("🐱 " + t("title", lang))

kpi1, kpi2, kpi3 = st.columns(3)
st.sidebar.header("🧭 " + t("filter_panel", lang))

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
    total_power_sum = pd.to_numeric(df.get("total_hero_power"), errors="coerce").fillna(0).sum()
    avg_power = pd.to_numeric(df.get("total_hero_power"), errors="coerce").fillna(0).mean()
    alliance_combat = pd.to_numeric(df.get("combat_power_1st_squad"), errors="coerce").fillna(0).sum()
    kpi1.metric(label=t("col_total_power", lang), value=f"{total_power_sum/1_000_000:.2f} M")
    kpi2.metric(label=t("kpi_avg_power", lang), value=f"{avg_power/1_000_000:.2f} M")
    kpi3.metric(label=t("kpi_alliance_combat", lang), value=f"{alliance_combat/1_000_000:.2f} M")

# Apply filters
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
# Main content: Table (left) and Charts (right)
# ------------------------------------------------------------------------------
left, right = st.columns([7, 5])

with left:
    st.subheader("Alliance Member Roster")
    table_df = df.copy()
    # Translate seat color for display only
    if "expected_transfer_seat_color" in table_df.columns:
        table_df["expected_transfer_seat_color"] = table_df["expected_transfer_seat_color"].map(SEAT_COLOR.get(lang, {})).fillna(table_df["expected_transfer_seat_color"])
    # Convert and format updated_at to CET
    if "updated_at" in table_df.columns:
        table_df["updated_at"] = pd.to_datetime(table_df["updated_at"], utc=True, errors="coerce")
        table_df["updated_at"] = table_df["updated_at"].dt.tz_convert("Europe/Berlin").dt.strftime("%d.%m.%Y %H%M")
    # Ensure numeric for formatting and gradient
    for col in ["total_hero_power", "combat_power_1st_squad"]:
        if col in table_df.columns:
            table_df[col] = pd.to_numeric(table_df[col], errors="coerce")

    # Column header mapping
    display_cols_map = {
        "player_name": t("col_player_name", lang),
        "current_alliance": t("col_current_alliance", lang),
        "total_hero_power": t("col_total_power", lang),
        "combat_power_1st_squad": t("col_1st_squad", lang),
        "expected_transfer_seat_color": t("col_seat_color", lang),
        "updated_at": t("col_updated_at", lang),
    }
    ordered_cols = [c for c in display_cols_map.keys() if c in table_df.columns]

    # Build styled table with gradient (requires matplotlib); fall back to st.dataframe if not available
    try:
        import matplotlib  # noqa: F401
        styled = (
            table_df[ordered_cols]
            .style
            .background_gradient(subset=["total_hero_power"], cmap="Greens")
            .format({
                "total_hero_power": lambda v: f"{float(v)/1_000_000:.2f} M" if pd.notnull(v) else "",
                "combat_power_1st_squad": lambda v: f"{float(v)/1_000_000:.2f} M" if pd.notnull(v) else "",
            })
            .hide(axis="index")
        )
        # Rename headers by rebuilding with renamed columns
        table_df_renamed = table_df.rename(columns=display_cols_map)
        styled = (
            table_df_renamed[[display_cols_map[c] for c in ordered_cols]]
            .style
            .background_gradient(subset=[display_cols_map["total_hero_power"]], cmap="Greens")
            .format({
                display_cols_map["total_hero_power"]: lambda v: f"{float(v)/1_000_000:.2f} M" if pd.notnull(v) else "",
                display_cols_map["combat_power_1st_squad"]: lambda v: f"{float(v)/1_000_000:.2f} M" if pd.notnull(v) else "",
            })
            .hide(axis="index")
        )
        st.write(styled)
    except Exception:
        # Fallback plain dataframe with formatted numbers
        tmp = table_df.copy()
        for col in ["total_hero_power", "combat_power_1st_squad"]:
            if col in tmp.columns:
                tmp[col] = tmp[col].apply(lambda v: f"{float(v)/1_000_000:.2f} M" if pd.notnull(v) else "")
        tmp = tmp.rename(columns=display_cols_map)
        st.dataframe(tmp, use_container_width=True)

    # CSV of the visible table (use renamed headers; keep formatted numbers)
    csv = table_df.rename(columns=display_cols_map).to_csv(index=False).encode("utf-8")
    st.download_button(label=t("download_csv", lang), data=csv, file_name="players_filtered.csv", mime="text/csv", key="download_csv_btn")

with right:
    import altair as alt
    st.subheader("Visuals")

    if not df.empty and {"player_name", "total_hero_power"}.issubset(df.columns):
        top5 = df[["player_name", "total_hero_power"]].copy()
        top5["total_hero_power"] = pd.to_numeric(top5["total_hero_power"], errors="coerce")
        top5 = top5.dropna().nlargest(5, "total_hero_power")
        bar = alt.Chart(top5).mark_bar().encode(
            x=alt.X("player_name:N", sort='-y', title="Player"),
            y=alt.Y("total_hero_power:Q", title="Power"),
            tooltip=["player_name", alt.Tooltip("total_hero_power:Q", format=",")]
        ).properties(title="Top 5 Players by Power", height=250)
        st.altair_chart(bar, use_container_width=True)

    if not df.empty and "expected_transfer_seat_color" in df.columns:
        seat_counts = df["expected_transfer_seat_color"].map(SEAT_COLOR.get(lang, {})).value_counts().reset_index()
        seat_counts.columns = ["seat", "count"]
        pie = alt.Chart(seat_counts).mark_arc().encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="seat", type="nominal"),
            tooltip=["seat", "count"]
        ).properties(title="Seat Color Distribution", height=250)
        st.altair_chart(pie, use_container_width=True)

# ------------------------------------------------------------------------------
# Admin Tools – Sidebar expander
# ------------------------------------------------------------------------------
with st.sidebar.expander("🔒 Admin Tools", expanded=False):
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
