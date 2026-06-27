from collections import deque
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

OWID_URL = (
    "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/"
    "owid-covid-data.csv"
)
LOCAL_CSV = Path(__file__).resolve().parent.parent / "data" / "owid-covid-data.csv"
PREVIEW_COLUMNS = [
    "location",
    "date",
    "total_cases",
    "new_cases",
    "total_deaths",
    "new_deaths",
]

st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon="🦠",
    layout="wide",
)

st.title("Dashboard COVID-19")
st.caption(
    "Preview dummy — 5 linhas do dataset "
    "[Our World in Data (OWID)](https://ourworldindata.org/coronavirus)"
)


def _read_local_tail(path: Path, n: int = 5) -> pd.DataFrame:
    with path.open(encoding="utf-8") as handle:
        header = handle.readline()
        tail_lines = deque(handle, maxlen=n)
    return pd.read_csv(StringIO(header + "".join(tail_lines)))


@st.cache_data
def load_preview() -> tuple[pd.DataFrame, str]:
    if LOCAL_CSV.exists():
        df = _read_local_tail(LOCAL_CSV)
        source = f"arquivo local (`{LOCAL_CSV.name}`)"
    else:
        df = pd.read_csv(OWID_URL, nrows=5)
        source = "URL remota OWID"
    return df, source


with st.spinner("Carregando dados..."):
    df, source = load_preview()

display = df[[c for c in PREVIEW_COLUMNS if c in df.columns]]

st.info(f"Fonte: {source}")
st.dataframe(display, use_container_width=True, hide_index=True)

st.metric("Linhas exibidas", len(display))
