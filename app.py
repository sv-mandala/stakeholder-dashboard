"""
Mandala Stakeholder Dialogue Dashboard
--------------------------------------
An interactive Streamlit dashboard that visualises stakeholder commentary on a
central research topic as a bubble / network diagram, coloured by argument.

  * Upload the data compiled by Bec (CSV or Excel).
  * Each major ARGUMENT in the topic has its own colour.
  * Each stakeholder-group bubble is coloured by the argument the MOST
    commentators in that group align with (its dominant theme).
  * Bubble size = the amount of dialogue (number of commentaries) from that group.
  * Click a bubble to see every commentator in a table, grouped by the argument
    their comment aligns with, with the quote and a link to the source.

Run locally:   streamlit run app.py
Data schema:   see data/sample_data.csv and README.md
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Mandala branding
# --------------------------------------------------------------------------- #
# Blues / teals / greens only (from the Mandala theme swatches). No coral, no gold.
NAVY = "#0A2A5E"          # deep navy (spokes + central ring)
NAVY_INK = "#0A1F45"      # near-black navy (text)
TEAL = "#2E6E8E"          # teal accent (source links)
GREEN = "#2E8B67"         # green accent
STEEL = "#33567A"         # deep steel blue
GREY = "#5F5F5F"          # body grey
LIGHT = "#EDEFF3"         # light background

# Palette used to colour ARGUMENTS (assigned in stable, sorted order).
ARGUMENT_PALETTE = [
    "#0A2A5E",  # deep navy
    "#2E86C1",  # azure blue
    "#2E8B67",  # green
    "#2E6E8E",  # teal
    "#2A47A8",  # royal blue
    "#5A7196",  # slate blue
    "#35798F",  # deep teal
    "#7E93AD",  # muted slate
    "#1F9E89",  # emerald
    "#264F73",  # steel navy
]
UNCLASSIFIED = "Unclassified"
UNCLASSIFIED_COLOUR = "#9AA6B2"  # neutral grey-blue for uncoded comments

SENTIMENT_COLOURS = {
    "positive": GREEN,
    "neutral": GREY,
    "negative": STEEL,
}

REQUIRED_COLUMNS = ["stakeholder_group", "quote"]
OPTIONAL_COLUMNS = ["topic", "stakeholder_name", "argument", "source_link", "date", "sentiment"]

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

    df["stakeholder_group"] = df["stakeholder_group"].astype(str).str.strip()
    df["quote"] = df["quote"].astype(str).str.strip()
    df = df[(df["stakeholder_group"] != "") & (df["stakeholder_group"].str.lower() != "nan")]
    df = df[(df["quote"] != "") & (df["quote"].str.lower() != "nan")]

    for col in ["stakeholder_name", "argument", "source_link", "sentiment", "topic"]:
        df[col] = df[col].astype(str).str.strip().replace({"nan": ""})
    df["sentiment"] = df["sentiment"].str.lower()

    # Uncoded comments still appear, grouped under "Unclassified".
    df["argument"] = df["argument"].replace({"": UNCLASSIFIED})

    return df.reset_index(drop=True)


def validate(df: pd.DataFrame) -> list[str]:
    problems = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            problems.append(f"Missing required column: `{col}`")
    if df.empty:
        problems.append("No usable rows found (need at least a stakeholder group and a quote).")
    return problems


def argument_colours(arguments: list[str]) -> dict[str, str]:
    """Assign a stable colour to each argument (sorted, so it never shuffles)."""
    ordered = sorted(a for a in arguments if a != UNCLASSIFIED)
    mapping = {a: ARGUMENT_PALETTE[i % len(ARGUMENT_PALETTE)] for i, a in enumerate(ordered)}
    mapping[UNCLASSIFIED] = UNCLASSIFIED_COLOUR
    return mapping


def dominant_argument(group_df: pd.DataFrame) -> str:
    """The argument with the most commentators in a group.

    Ties break deterministically: higher count first, then alphabetical.
    """
    tally = group_df["argument"].value_counts()
    # Sort by (-count, name) for a stable winner.
    ordered = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
    return ordered[0][0] if ordered else UNCLASSIFIED


# --------------------------------------------------------------------------- #
# Network / bubble figure
# --------------------------------------------------------------------------- #
def build_figure(counts: pd.DataFrame, arg_colours: dict[str, str], topic_label: str) -> go.Figure:
    """
    Hub-and-spoke bubble diagram.

    `counts` columns: stakeholder_group, n, dominant_arg, colour.
    Bubble colour encodes the group's dominant argument; a legend maps
    each colour to its argument. Group names carried in customdata for clicks.
    """
    n_groups = len(counts)
    radius = 1.0
    max_n = max(int(counts["n"].max()), 1)
    min_px, max_px = 46, 132

    def size_px(n: int) -> float:
        return min_px + (max_px - min_px) * math.sqrt(n / max_n)

    positions = []
    for i in range(n_groups):
        angle = math.pi / 2 - (2 * math.pi * i / max(n_groups, 1))
        positions.append((radius * math.cos(angle), radius * math.sin(angle)))

    fig = go.Figure()

    # 1) Spokes from centre to each group.
    for (x, y) in positions:
        fig.add_trace(
            go.Scatter(
                x=[0, x], y=[0, y], mode="lines",
                line=dict(color=NAVY, width=2), hoverinfo="skip", showlegend=False,
            )
        )

    # 2) Group bubbles (single trace -> click index maps to group list).
    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in positions],
            y=[p[1] for p in positions],
            mode="markers+text",
            marker=dict(
                size=[size_px(int(n)) for n in counts["n"]],
                color=list(counts["colour"]),
                line=dict(color="white", width=2),
                opacity=0.95,
            ),
            text=[f"<b>{g}</b><br>{int(n)}" for g, n in zip(counts["stakeholder_group"], counts["n"])],
            textposition="middle center",
            textfont=dict(color="white", size=12, family="Arial"),
            customdata=list(counts["stakeholder_group"]),
            hovertemplate="<b>%{customdata}</b><br>%{marker.size:.0f}px · click to read<extra></extra>",
            showlegend=False,
        )
    )

    # 3) Central topic node.
    fig.add_trace(
        go.Scatter(
            x=[0], y=[0], mode="markers+text",
            marker=dict(size=180, color="white", line=dict(color=NAVY, width=3)),
            text=[f"<b>{topic_label}</b>"], textposition="middle center",
            textfont=dict(color=NAVY_INK, size=11, family="Arial"),
            hoverinfo="skip", showlegend=False,
        )
    )

    # 4) Legend: one dummy trace per argument that actually colours a bubble.
    shown_args = list(dict.fromkeys(counts["dominant_arg"]))  # preserve order, unique
    for arg in shown_args:
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=13, color=arg_colours.get(arg, UNCLASSIFIED_COLOUR)),
                name=arg, showlegend=True, hoverinfo="skip",
            )
        )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-1.7, 1.7]),
        yaxis=dict(visible=False, range=[-1.5, 1.6], scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=48, b=10),
        height=640,
        plot_bgcolor="white",
        paper_bgcolor="white",
        clickmode="event+select",
        dragmode=False,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5,
            title=dict(text="Dominant argument  ", side="left"),
            font=dict(size=11, color=NAVY_INK),
        ),
    )
    return fig


# --------------------------------------------------------------------------- #
# Detail panel: table of commentators grouped by argument
# --------------------------------------------------------------------------- #
def render_group_detail(df: pd.DataFrame, group: str, arg_colours: dict[str, str]) -> None:
    rows = df[df["stakeholder_group"] == group]
    dom = dominant_argument(rows)

    st.markdown(f"### 💬 {group} — {len(rows)} commentators")
    st.markdown(
        f"<span style='color:{GREY};'>Bubble colour reflects the dominant argument: </span>"
        f"<span style='background:{arg_colours.get(dom, UNCLASSIFIED_COLOUR)};color:white;"
        f"padding:2px 10px;border-radius:10px;font-size:13px;'>{dom}</span>",
        unsafe_allow_html=True,
    )

    # Order arguments within the group: dominant first, then by count desc.
    tally = rows["argument"].value_counts()
    ordered_args = sorted(tally.items(), key=lambda kv: (kv[0] != dom, -kv[1], kv[0]))

    for arg, n in ordered_args:
        colour = arg_colours.get(arg, UNCLASSIFIED_COLOUR)
        crown = "  ⭐ dominant" if arg == dom else ""
        st.markdown(
            f"<div style='margin-top:14px;'>"
            f"<span style='display:inline-block;width:12px;height:12px;border-radius:3px;"
            f"background:{colour};margin-right:8px;'></span>"
            f"<span style='font-weight:700;color:{NAVY_INK};'>{arg}</span>"
            f"<span style='color:{GREY};'> · {n} commentator{'s' if n != 1 else ''}{crown}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        sub = rows[rows["argument"] == arg].copy()
        table = pd.DataFrame(
            {
                "Commentator": sub["stakeholder_name"].replace({"": "Unattributed"}),
                "Quote": sub["quote"],
                "Sentiment": sub["sentiment"].replace({"": "—"}),
                "Date": sub["date"].replace({"": "—"}),
                "Source": sub["source_link"].replace({"": None}),
            }
        )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Commentator": st.column_config.TextColumn(width="medium"),
                "Quote": st.column_config.TextColumn(width="large"),
                "Sentiment": st.column_config.TextColumn(width="small"),
                "Date": st.column_config.TextColumn(width="small"),
                "Source": st.column_config.LinkColumn("Source", display_text="↗ open"),
            },
        )


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
def main() -> None:
    st.set_page_config(page_title="Mandala Stakeholder Dashboard", layout="wide", page_icon="🟦")

    st.markdown(
        f"<h1 style='color:{NAVY};margin-bottom:0;'>Stakeholder Dialogue Dashboard</h1>"
        f"<p style='color:{GREY};margin-top:4px;'>What are opinion-formers saying about fixed, "
        f"four-year federal terms in Australia? Each bubble is a stakeholder group, coloured by the "
        f"argument most of its commentators align with. Click a bubble to see who is saying what.</p>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Data")
        uploaded = st.file_uploader("Upload Bec's data (CSV or Excel)", type=["csv", "xlsx", "xls"])
        st.caption("Columns: topic, stakeholder_group, stakeholder_name, argument, quote, source_link, date, sentiment")
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

    # Topic selector.
    topics = sorted([t for t in df["topic"].unique() if t])
    if len(topics) > 1:
        topic = st.selectbox("Research topic", topics)
        df = df[df["topic"] == topic]
    elif len(topics) == 1:
        topic = topics[0]
    else:
        topic = "Research topic"

    # Argument colour map (stable across the whole topic).
    arg_colours = argument_colours(list(df["argument"].unique()))

    # Per-group counts + dominant argument + bubble colour.
    rows = []
    for group, gdf in df.groupby("stakeholder_group"):
        dom = dominant_argument(gdf)
        rows.append(
            {
                "stakeholder_group": group,
                "n": len(gdf),
                "dominant_arg": dom,
                "colour": arg_colours.get(dom, UNCLASSIFIED_COLOUR),
            }
        )
    counts = pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)

    central_question = "What are opinion-formers saying about fixed, four-year federal terms in Australia?"
    topic_label = "<br>".join(textwrap.wrap(central_question, width=16))

    # Summary metrics.
    arg_overall = df["argument"].value_counts()
    top_arg = arg_overall.index[0] if len(arg_overall) else "—"
    m1, m2, m3 = st.columns(3)
    m1.metric("Total commentators", int(counts["n"].sum()))
    m2.metric("Arguments in play", df["argument"].nunique())
    m3.metric("Most-cited argument", top_arg)

    left, right = st.columns([3, 2], gap="large")

    with left:
        fig = build_figure(counts, arg_colours, topic_label)
        event = st.plotly_chart(
            fig, width="stretch",
            on_select="rerun", selection_mode="points", key="network",
        )

        selected_group = None
        try:
            for pt in event["selection"]["points"]:
                cd = pt.get("customdata")
                if isinstance(cd, list):
                    cd = cd[0] if cd else None
                if cd:
                    selected_group = cd
                    break
        except (KeyError, TypeError):
            selected_group = None

    with right:
        group_options = ["— select a group —"] + list(counts["stakeholder_group"])
        default_idx = group_options.index(selected_group) if selected_group in group_options else 0
        chosen = st.selectbox("Or pick a stakeholder group", group_options, index=default_idx)
        active = selected_group or (chosen if chosen != "— select a group —" else None)

        if active:
            render_group_detail(df, active, arg_colours)
        else:
            st.info("Click a bubble (or choose a group above) to see its commentators grouped by argument.")


if __name__ == "__main__":
    main()
