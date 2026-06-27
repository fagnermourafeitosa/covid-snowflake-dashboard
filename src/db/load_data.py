"""
src/db/load_data.py
===================
Camada de ingestão: sessão Snowflake e gravação da tabela COVID-19.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OWID_URL = (
    "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/"
    "owid-covid-data.csv"
)

def _sf_secret(key: str, default: str = "") -> str:
    """Lê uma chave de st.secrets["snowflake"] com fallback seguro."""
    try:
        return st.secrets["snowflake"][key]
    except Exception:
        return default


def _get_table_name() -> str:
    return _sf_secret("table", "COVID19")


def _get_database() -> str:
    return _sf_secret("database", "CLASS1")


def _get_schema() -> str:
    return _sf_secret("schema", "PUBLIC")


# Colunas mínimas que identificam o arquivo OWID genuíno
REQUIRED_COLUMNS: list[str] = [
    "location",
    "continent",
    "date",
    "total_cases",
    "new_cases",
    "total_deaths",
    "new_deaths",
    "population",
    "people_vaccinated",
    "people_fully_vaccinated",
]

# Colunas efetivamente gravadas no Snowflake (apenas as usadas nas visualizações)
KEEP_COLUMNS: list[str] = REQUIRED_COLUMNS  # mesmo conjunto, alias semântico

# Países padrão para filtragem ao gravar no Snowflake
DEFAULT_COUNTRIES: list[str] = [
    "Brazil",
    "Spain",
    "Portugal",
    "United States",
    "South Africa",
    "China",
]


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def get_snowflake_session() -> Session:
    """Cria (e cacheia) uma Session Snowpark a partir de st.secrets."""
    params = {
        "user": st.secrets["snowflake"]["user"],
        "password": st.secrets["snowflake"]["password"],
        "account": st.secrets["snowflake"]["account"],
        "warehouse": st.secrets["snowflake"]["warehouse"],
        "database": _get_database(),
        "schema": _get_schema(),
        "role": st.secrets["snowflake"]["role"],
    }
    return Session.builder.configs(params).create()


# ---------------------------------------------------------------------------
# Verificação de tabela
# ---------------------------------------------------------------------------


def table_has_data(session: Session) -> bool:
    """Retorna True se a tabela COVID19 existe e contém ao menos 1 linha."""
    try:
        db, schema, table = _get_database(), _get_schema(), _get_table_name()
        count = (
            session.sql(
                f"SELECT COUNT(*) AS n FROM {db}.{schema}.{table}"
            )
            .collect()[0]["N"]
        )
        return int(count) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Validação do CSV
# ---------------------------------------------------------------------------


def validate_owid_csv(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Verifica se o DataFrame possui as colunas mínimas do OWID.

    Returns
    -------
    (ok, message)
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, (
            f"Arquivo inválido. Colunas ausentes: {', '.join(missing)}.\n"
            f"Certifique-se de que está usando o CSV oficial disponível em:\n"
            f"{OWID_URL}"
        )
    return True, "OK"


# ---------------------------------------------------------------------------
# Filtragem
# ---------------------------------------------------------------------------


def filter_owid_df(
    df: pd.DataFrame,
    countries: list[str] | None = None,
    start_date: str | None = None,
) -> pd.DataFrame:
    """
    Aplica filtros de países e data inicial e mantém só as colunas principais.
    Remove linhas de continentes/agregados (continent == NaN).
    """
    # Remove agregados (mundo, continentes): continent é NaN nesses casos
    df = df[df["continent"].notna()].copy()

    if countries:
        df = df[df["location"].isin(countries)]

    if start_date:
        df = df[df["date"] >= start_date]

    # Mantém apenas as colunas principais — descarta as 57 colunas extras do OWID
    df = df[[c for c in KEEP_COLUMNS if c in df.columns]]

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Ingestão no Snowflake
# ---------------------------------------------------------------------------


def ingest_csv_to_snowflake(
    session: Session,
    df: pd.DataFrame,
    overwrite: bool = True,
) -> int:
    """
    Grava o DataFrame na tabela COVID19 via write_pandas.

    Parameters
    ----------
    session  : Session Snowpark ativa
    df       : DataFrame já validado e filtrado
    overwrite: Se True, substitui a tabela existente

    Returns
    -------
    Número de linhas gravadas.
    """
    from snowflake.connector.pandas_tools import write_pandas

    # Normaliza nomes de colunas para uppercase (exigência Snowflake)
    df_snow = df.copy()
    df_snow.columns = [c.upper() for c in df_snow.columns]

    # Converte tipos problemáticos
    for col in df_snow.select_dtypes(include="object").columns:
        df_snow[col] = df_snow[col].astype(str).where(df_snow[col].notna(), None)

    conn = session.connection
    success, nchunks, nrows, _ = write_pandas(
        conn=conn,
        df=df_snow,
        table_name=_get_table_name(),
        database=_get_database(),
        schema=_get_schema(),
        overwrite=overwrite,
        auto_create_table=True,
        quote_identifiers=False,
    )

    if not success:
        raise RuntimeError(f"write_pandas falhou após {nchunks} chunks.")

    return nrows
