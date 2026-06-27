"""
src/db/query_data.py
====================
Camada de leitura: consultas ao Snowflake para o dashboard.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session

from db.load_data import _get_database, _get_schema, _get_table_name


# ---------------------------------------------------------------------------
# Leitura principal
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False, ttl=600)
def load_covid_data(_session: Session) -> pd.DataFrame:
    """
    Lê toda a tabela COVID19 do Snowflake e retorna um DataFrame.

    O argumento é prefixado com _ para que o cache do Streamlit
    não tente fazer hash do objeto Session.
    """
    df = (
        _session.table(f"{_get_database()}.{_get_schema()}.{_get_table_name()}")
        .to_pandas()
    )
    # Normaliza nomes de colunas para lowercase
    df.columns = [c.lower() for c in df.columns]

    # Garante tipagem correta
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    num_cols = [
        "total_cases", "new_cases", "total_deaths",
        "new_deaths", "population",
        "people_vaccinated", "people_fully_vaccinated",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Query SQL personalizada (bônus)
# ---------------------------------------------------------------------------


def run_custom_query(_session: Session, sql: str) -> pd.DataFrame:
    """
    Executa SQL arbitrário no Snowflake e retorna um DataFrame.
    Não usa cache — cada execução é ao vivo.
    """
    df = _session.sql(sql).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df
