"""
Mandala Stakeholder Dialogue Dashboard
--------------------------------------
An interactive Streamlit dashboard that visualises stakeholder commentary on a
central research topic as a bubble / network diagram.

  * Upload the data compiled by Bec (CSV or Excel).
  * Bubbles are one per stakeholder group, arranged around the central topic.
  * Bubble size = the amount of dialogue (number of commentaries) from that group.
  * Click a bubble to read what that group is saying: the quote, who said it,
    and a link to the source.

Run locally:   streamlit run app.py
Data schema:   see data/sample_data.csv and README.md
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Mandala branding
# --------------------------------------------------------------------------- #
# Palette extracted from mandalapartners.com/reports (navy + coral house style),
# extended with in-family tints/complements so up to ~8 groups stay distinct.
NAVY = "#0A2A5E"          # deep navy (spokes + central ring)
NAVY_INK = "#0A1F45"      # near-black navy (text)
TEAL = "#2E6E8E"          # teal accent (source links)
AZURE = "#2E86C1"         # bright azure blue
GREEN = "#2E8B67"         # green accent
STEEL = "#33567A"         # deep steel blue
GREY = "#5F5F5F"          # body grey
LIGHT = "#EDEFF3"         # light background

# Ordered categorical palette for stakeholder bubbles (from Mandala theme swatches).
# Blues, teals and greens only.
MANDALA_PALETTE = [
    "#0A2A5E",  # deep navy
    "#2A47A8",  # royal blue
    "#2E6E8E",  # teal
    "#2E86C1",  # azure blue
    "#2E8B67",  # green
    "#5A7196",  # slate blue
    "#7E93AD",  # muted slate
    "#35798F",  # deep teal
]

# Stable colour per known group so the palette doesn't shuffle between loads.
FIXED_GROUP_COLOURS = {
    "Government": "#0A2A5E",                 # deep navy
    "Academia": "#2A47A8",                   # royal blue
    "Media": "#2E6E8E",                      # teal
    "Business and peak bodies": "#2E86C1",   # azure blue
    "Public": "#2E8B67",                     # green
    "Unions": "#5A7196",                     # slate blue
}

SENTIMENT_COLOURS = {
    "positive": GREEN,
    "neutral": GREY,
    "negative": STEEL,
}

REQUIRED_COLUMNS = ["stakeholder_group", "quote"]
OPTIONAL_COLUMNS = ["topic", "stakeholder_name", "source_link", "date", "sentiment"]

APP_DIR = Path(__file__).parent
SAMPLE_PATH = APP_DIR / "data" / "sample_data.csv"


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_dataframe(uploaded_file) -> pd.DataFrame:
    """Read an uploaded CSV/Excel file into a normalised DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
    return normalise(df)


def load_sample() -> pd.DataFrame:
    return normalise(pd.read_csv(SAMPLE_PATH))


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Lower/strip column names, ensure expected columns exist, tidy types."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Drop rows without a group or a quote.
    df["stakeholder_group"] = df["stakeholder_group"].astype(str).str.strip()
    df["quote"] = df["quote"].astype(str).str.strip()
    df = df[(df["stakeholder_group"] != "") & (df["stakeholder_group"].str.lower() != "nan")]
    df = df[(df["quote"] != "") & (df["quote"].str.lower() != "nan")]

    for col in ["stakeholder_name", "source_link", "sentiment", "topic"]:
        df[col] = df[col].astype(str).str.strip().replace({"nan": ""})
    df["sentiment"] = df["sentiment"].str.lower()

    return df.reset_index(drop=True)


def validate(df: pd.DataFrame) -> list[str]:
    """Return a list of problems; empty list means the data is usable."""
    problems = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            problems.append(f"Missing required column: `{col}`")
    if df.empty:
        problems.append("No usable rows found (need at least a stakeholder group and a quote).")
    return problems


def colour_for(group: str, index: int) -> str:
    return FIXED_GROUP_COLOURS.get(group, MANDALA_PALETTE[index % len(MANDALA_PALETTE)])


# --------------------------------------------------------------------------- #
# Network / bubble figure
# --------------------------------------------------------------------------- #
def build_figure(counts: pd.DataFrame, topic_label: str) -> go.Figure:
    """
    Build the hub-and-spoke bubble diagram.

    `counts` has columns: stakeholder_group, n (number of commentaries), colour.
    Returns a Plotly figure; each group bubble carries its group name in
    customdata so clicks can be mapped back to a group.
    """
    n_groups = len(counts)
    radius = 1.0
    # Marker area ~ number of commentaries -> diameter ~ sqrt(n).
    max_n = max(int(counts["n"].max()), 1)
    min_px, max_px = 46, 130

    def size_px(n: int) -> float:
        return min_px + (max_px - min_px) * math.sqrt(n / max_n)

    fig = go.Figure()

    # Position groups evenly around the centre. Start at the top, go clockwise.
    positions = []
    for i in range(n_groups):
        angle = math.pi / 2 - (2 * math.pi * i / max(n_groups, 1))
        positions.append((radius * math.cos(angle), radius * math.sin(angle)))

    # 1) Edges (spokes) from centre to each group.
    for (x, y) in positions:
        fig.add_trace(
            go.Scatter(
                x=[0, x], y=[0, y],
                mode="lines",
                line=dict(color=NAVY, width=2),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # 2) Group bubbles (single trace so click index maps to the group list).
    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in positions],
            y=[p[1] for p in positions],
            mode="markers+text",
            marker=dict(
                size=[size_px(int(n)) for n in counts["n"]],
                color=list(counts["colour"]),
                line=dict(color="white", width=2),
                opacity=0.92,
            ),
            text=[f"<b>{g}</b><br>{int(n)}" for g, n in zip(counts["stakeholder_group"], counts["n"])],
            textposition="middle center",
            textfont=dict(color="white", size=12, family="Arial"),
            customdata=list(counts["stakeholder_group"]),
            hovertemplate="<b>%{customdata}</b><br>%{marker.size:.0f}px · click to read<extra></extra>",
            showlegend=False,
        )
    )

    # 3) Central topic node (white with navy ring, like the reference diagram).
    fig.add_trace(
        go.Scatter(
            x=[0], y=[0],
            mode="markers+text",
            marker=dict(size=150, color="white", line=dict(color=NAVY, width=3)),
            text=[f"<b>{topic_label}</b>"],
            textposition="middle center",
            textfont=dict(color=NAVY_INK, size=13, family="Arial"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.7, 1.7]),
        yaxis=dict(visible=False, range=[-1.5, 1.5], scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=10, b=10),
        height=620,
        plot_bgcolor="white",
        paper_bgcolor="white",
        clickmode="event+select",
        dragmode=False,
    )
    return fig


# --------------------------------------------------------------------------- #
# Detail panel
# --------------------------------------------------------------------------- #
def render_group_detail(df: pd.DataFrame, group: str) -> None:
    rows = df[df["stakeholder_group"] == group]
    st.markdown(f"### 💬 What **{group}** are saying  ·  {len(rows)} commentaries")

    for _, r in rows.iterrows():
        speaker = r.get("stakeholder_name", "") or "Unattributed"
        sentiment = (r.get("sentiment", "") or "").lower()
        badge = ""
        if sentiment in SENTIMENT_COLOURS:
            colour = SENTIMENT_COLOURS[sentiment]
            badge = (
                f"<span style='background:{colour};color:white;padding:2px 8px;"
                f"border-radius:10px;font-size:11px;margin-left:8px;'>{sentiment}</span>"
            )
        date = r.get("date", "")
        date_txt = f" · <span style='color:{GREY};font-size:12px;'>{date}</span>" if date else ""

        st.markdown(
            f"<div style='border-left:4px solid {NAVY};padding:6px 14px;margin:10px 0;'>"
            f"<div style='font-weight:600;color:{NAVY_INK};'>{speaker}{badge}{date_txt}</div>"
            f"<div style='color:{GREY};font-style:italic;margin:6px 0;'>“{r['quote']}”</div>"
            + (
                f"<a href='{r['source_link']}' target='_blank' style='color:{TEAL};"
                f"font-size:13px;text-decoration:none;'>↗ Source</a>"
                if r.get("source_link")
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Mandala Stakeholder Dashboard", layout="wide", page_icon="🟦")

    st.markdown(
        f"<h1 style='color:{NAVY};margin-bottom:0;'>Stakeholder Dialogue Dashboard</h1>"
        f"<p style='color:{GREY};margin-top:4px;'>Who is saying what about the research topic — "
        f"sized by volume of commentary, click a bubble to read the detail.</p>",
        unsafe_allow_html=True,
    )

    # --- Sidebar: data source ------------------------------------------------
    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader("Upload Bec's data (CSV or Excel)", type=["csv", "xlsx", "xls"])
        st.caption("Columns: topic, stakeholder_group, stakeholder_name, quote, source_link, date, sentiment")
        with open(SAMPLE_PATH, "rb") as fh:
            st.download_button("⬇ Download data template", fh, "stakeholder_template.csv", "text/csv")

    if uploaded is not None:
        try:
            df = load_dataframe(uploaded)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read that file: {exc}")
            st.stop()
        st.sidebar.success(f"Loaded {len(df)} rows from {uploaded.name}")
    else:
        df = load_sample()
        st.sidebar.info("Showing sample data. Upload a file to replace it.")

    problems = validate(df)
    if problems:
        for p in problems:
            st.error(p)
        st.stop()

    # --- Topic selector ------------------------------------------------------
    topics = sorted([t for t in df["topic"].unique() if t])
    if len(topics) > 1:
        topic = st.selectbox("Research topic", topics)
        df = df[df["topic"] == topic]
    elif len(topics) == 1:
        topic = topics[0]
    else:
        topic = "Research topic"

    # --- Aggregate counts per group -----------------------------------------
    counts = (
        df.groupby("stakeholder_group")
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
        .reset_index(drop=True)
    )
    counts["colour"] = [colour_for(g, i) for i, g in enumerate(counts["stakeholder_group"])]

    # Wrap a long topic label so it fits inside the central node.
    topic_label = topic if len(topic) <= 22 else topic[:22].rsplit(" ", 1)[0] + "…"

    # --- Summary metrics -----------------------------------------------------
    m1, m2, m3 = st.columns(3)
    m1.metric("Total commentaries", int(counts["n"].sum()))
    m2.metric("Stakeholder groups", len(counts))
    m3.metric("Most vocal", counts.iloc[0]["stakeholder_group"] if len(counts) else "—")

    left, right = st.columns([3, 2], gap="large")

    # --- Bubble diagram + click handling ------------------------------------
    with left:
        fig = build_figure(counts, topic_label)
        event = st.plotly_chart(
            fig,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="network",
        )

        selected_group = None
        try:
            pts = event["selection"]["points"]
            for pt in pts:
                cd = pt.get("customdata")
                if isinstance(cd, list):
                    cd = cd[0] if cd else None
                if cd:
                    selected_group = cd
                    break
        except (KeyError, TypeError):
            selected_group = None

    # --- Detail panel --------------------------------------------------------
    with right:
        # Selectbox mirrors/serves as a fallback for clicking.
        group_options = ["— select a group —"] + list(counts["stakeholder_group"])
        default_idx = group_options.index(selected_group) if selected_group in group_options else 0
        chosen = st.selectbox("Or pick a stakeholder group", group_options, index=default_idx)
        active = selected_group or (chosen if chosen != "— select a group —" else None)

        if active:
            render_group_detail(df, active)
        else:
            st.info("Click a bubble (or choose a group above) to see the quotes and sources.")


if __name__ == "__main__":
    main()
