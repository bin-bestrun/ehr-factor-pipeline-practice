from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
FACTOR_FILE = PROJECT_DIR / "data" / "processed" / "ehr_factor_values.parquet"
INDEX_FILE = PROJECT_DIR / "ehr_factor_skills" / "factor_index.json"

st.set_page_config(
    page_title="EHR Factor Explorer",
    page_icon=":material/monitoring:",
    layout="wide",
)


@st.cache_data(ttl="15m", max_entries=2, show_spinner="Loading encounter factor values…")
def load_factor_values(path: str, modified_time: float) -> pd.DataFrame:
    """Read the generated factor table; modified time refreshes replaced files."""
    del modified_time
    return pd.read_parquet(path)


@st.cache_data(ttl="15m", max_entries=2)
def load_factor_index(path: str, modified_time: float) -> list[dict[str, Any]]:
    del modified_time
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("factor_index.json should contain a list of factor entries.")
    return [item for item in data if isinstance(item, dict)]


def format_number(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"{value:,.3f}"


def make_histogram(values: pd.Series) -> pd.DataFrame:
    """Build a small aggregate histogram without showing encounter rows."""
    low = float(values.min())
    high = float(values.max())
    if low == high:
        return pd.DataFrame(
            {"Value interval": [format_number(low)], "Encounter count": [len(values)]}
        )

    bin_count = min(20, max(5, int(len(values) ** 0.5)))
    buckets = pd.cut(values, bins=bin_count, include_lowest=True)
    counts = buckets.value_counts(sort=False)
    histogram = counts.rename_axis("Value interval").reset_index(name="Encounter count")
    histogram["Value interval"] = histogram["Value interval"].astype(str)
    return histogram


def make_factor_summary(
    frame: pd.DataFrame, entries: list[dict[str, Any]]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        column = str(entry.get("column", ""))
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        valid = values.dropna()
        rows.append(
            {
                "ID": entry.get("factor_id", ""),
                "Factor": entry.get("name_en", column),
                "Available encounters": int(valid.size),
                "Missing values": int(values.isna().sum()),
                "Mean": valid.mean() if not valid.empty else pd.NA,
                "Median": valid.median() if not valid.empty else pd.NA,
                "Unit": entry.get("unit", ""),
            }
        )
    return pd.DataFrame(rows)


st.title("EHR factor explorer")
st.caption("A local learning dashboard for descriptive encounter-level features.")
st.warning(
    "Educational use only. These factors are not validated clinical scores and must not be used to guide patient care.",
    icon=":material/info:",
)

missing_files = [path for path in (FACTOR_FILE, INDEX_FILE) if not path.exists()]
if missing_files:
    st.error("The dashboard needs its generated factor data and package index.")
    st.markdown("Run these commands from `S:\\AI_Projects\\pipeline_practice`:")
    st.code(
        "python .\\ehr_factor_pipeline.py\n"
        "python .\\build_ehr_factor_package.py",
        language="powershell",
    )
    st.caption("Missing: " + ", ".join(str(path) for path in missing_files))
    st.stop()

try:
    factor_stat = FACTOR_FILE.stat()
    index_stat = INDEX_FILE.stat()
    values_frame = load_factor_values(str(FACTOR_FILE), factor_stat.st_mtime)
    factor_entries = load_factor_index(str(INDEX_FILE), index_stat.st_mtime)
except Exception as exc:
    st.error("Could not load the factor data or catalog.")
    st.exception(exc)
    st.stop()

available_entries = [
    entry for entry in factor_entries if str(entry.get("column", "")) in values_frame.columns
]
if not available_entries:
    st.error("No factor columns in the Parquet file match the package index.")
    st.stop()

with st.sidebar:
    st.header("Explore a factor")
    selected = st.selectbox(
        "Factor",
        available_entries,
        format_func=lambda entry: f"{entry.get('factor_id', '')} — {entry.get('name_en', entry.get('column', ''))}",
    )
    st.caption("The dashboard shows aggregate distributions and does not display encounter IDs.")

column = str(selected["column"])
series = pd.to_numeric(values_frame[column], errors="coerce")
valid_values = series.dropna()

with st.container(horizontal=True):
    st.metric("Encounter rows", f"{len(series):,}", border=True)
    st.metric("Available values", f"{len(valid_values):,}", border=True)
    st.metric("Missing values", f"{int(series.isna().sum()):,}", border=True)
    st.metric("Median", format_number(valid_values.median()) if not valid_values.empty else "—", border=True)

left, right = st.columns([3, 2])
with left:
    with st.container(border=True):
        st.subheader("Factor value distribution")
        if valid_values.empty:
            st.info("This factor has no usable values to chart.")
        else:
            histogram = make_histogram(valid_values)
            st.bar_chart(
                histogram,
                x="Value interval",
                y="Encounter count",
                alt=f"Aggregate distribution of {selected.get('name_en', column)} across encounters",
            )
with right:
    with st.container(border=True):
        st.subheader("Summary statistics")
        if valid_values.empty:
            st.info("No non-missing values are available.")
        else:
            stats = pd.DataFrame(
                {
                    "Statistic": ["Mean", "Standard deviation", "Minimum", "25th percentile", "75th percentile", "Maximum"],
                    "Value": [
                        valid_values.mean(),
                        valid_values.std(),
                        valid_values.min(),
                        valid_values.quantile(0.25),
                        valid_values.quantile(0.75),
                        valid_values.max(),
                    ],
                }
            )
            stats["Value"] = stats["Value"].map(format_number)
            st.dataframe(stats, hide_index=True, alt="Summary statistics for the selected factor")

with st.container(border=True):
    st.subheader("Factor definition")
    st.markdown(f"**{selected.get('factor_id', '')} — {selected.get('name_en', column)}**")
    st.write(selected.get("rationale_en", "No description is listed."))
    st.code(selected.get("formula_en", "Formula not listed"), language="text")
    st.caption(
        f"Output column: `{column}` · Unit: {selected.get('unit', 'unspecified')} · "
        "Encounter-level descriptive feature"
    )

with st.expander("Compare all factors"):
    summary = make_factor_summary(values_frame, available_entries)
    if summary.empty:
        st.info("No factor summary is available.")
    else:
        st.dataframe(
            summary,
            hide_index=True,
            alt="Aggregate availability and summary statistics for all packaged factors",
            column_config={
                "Mean": st.column_config.NumberColumn(format="%.3f"),
                "Median": st.column_config.NumberColumn(format="%.3f"),
            },
        )

st.caption(
    "The source dataset has no encounter date field. This dashboard does not create dates "
    "or display patient-level records. Keep this practice dashboard local."
)
