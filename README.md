# Mandala Stakeholder Dialogue Dashboard

An interactive Python (Streamlit) dashboard that visualises stakeholder commentary
on a central research topic as a **hub-and-spoke bubble diagram**, in Mandala branding.

- One bubble per **stakeholder group** (Academia, Public, Media, Government, Unions,
  Business and peak bodies, …), arranged around the central research topic.
- Each major **argument** in the topic has its own colour, and each bubble is
  **coloured by the argument that the most commentators in that group align with**
  (its dominant theme). A legend maps colours to arguments.
- **Bubble size = amount of dialogue** — the number of commentaries from that group.
- **Click a bubble** to open a **table of every commentator, grouped by the argument
  their comment aligns with**, with the quote, sentiment, date and a link to the source.
- **Upload** the data Bec compiles (CSV or Excel) to refresh the whole dashboard.

---

## 1. The data (what Bec compiles)

The dashboard reads one row per commentary. Save it as **CSV or Excel** with these columns:

| Column              | Required | Description                                                        |
|---------------------|----------|--------------------------------------------------------------------|
| `topic`             | optional | The central research topic. Multiple topics → a topic dropdown.    |
| `stakeholder_group` | **yes**  | The bubble this belongs to, e.g. `Government`, `Media`, `Academia`. |
| `stakeholder_name`  | optional | The commentator — who said it (person or organisation).           |
| `argument`          | **key**  | The argument/theme this comment aligns with, e.g. `Lower direct election cost`. Drives the bubble colour and the grouped tables. Blank rows are grouped under `Unclassified`. |
| `quote`             | **yes**  | The commentary / quote text.                                      |
| `source_link`       | optional | URL to the source (rendered as a clickable “↗ open” link).        |
| `date`              | optional | Date of the commentary (any readable format).                     |
| `sentiment`         | optional | `positive`, `neutral`, or `negative`.                             |

> **Tip:** keep `argument` values consistent (same spelling every time) so comments
> group cleanly and colours stay stable. Each distinct argument gets its own colour,
> assigned in alphabetical order from the Mandala palette.

A ready-to-fill template lives at [`data/sample_data.csv`](data/sample_data.csv), and can
also be downloaded from inside the app (sidebar → **Download data template**).

Column names are case-insensitive and spaces are ignored, so `Stakeholder Group`
also works.

---

## 2. Run it locally

```bash
cd "C:\Team folder\stakeholder_dashboard"
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell   (or: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at http://localhost:8501. Upload a file from the sidebar, or
explore the bundled sample data.

---

## 3. Put it online (free)

**Streamlit Community Cloud** is the simplest host:

1. Push this `stakeholder_dashboard/` folder to a GitHub repo.
2. Go to https://share.streamlit.io → **New app** → point it at `app.py`.
3. It installs `requirements.txt` automatically and gives you a shareable URL.

Any Python host works too (Render, Azure App Service, an internal server): install
`requirements.txt` and run `streamlit run app.py --server.port $PORT`.

---

## 4. Branding

Bubbles use the Mandala theme palette — blues, teals and green only (deep navy
`#0A2A5E`, royal blue `#2A47A8`, teal `#2E6E8E`, azure `#2E86C1`, green `#2E8B67`,
slate blue `#5A7196`). To adjust, edit `MANDALA_PALETTE` and `FIXED_GROUP_COLOURS`
near the top of [`app.py`](app.py), and the theme in
[`.streamlit/config.toml`](.streamlit/config.toml).

---

## 5. Notes / roadmap

- Bubble size already scales with commentary volume (area ∝ number of rows).
- Clicking is handled two ways: click the bubble, **or** use the group dropdown
  in the detail panel (a reliable fallback across Streamlit versions).
- Possible next steps: sentiment filtering, date-range slider, keyword search
  across quotes, and per-group export.
