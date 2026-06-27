"""
src/main.py
===========
Ponto de entrada do app Streamlit.
Segue estritamente a estrutura da spec 05-script-carga-dashboard.md.
"""

import sys
from pathlib import Path

import streamlit as st

# Garante que src/ está no path para imports relativos funcionarem
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard import render_dashboard, render_onboarding
from db.load_data import get_snowflake_session, table_has_data
from db.query_data import load_covid_data

# ---------------------------------------------------------------------------
# Configuração da página  (spec 05 — 4.1)
# ---------------------------------------------------------------------------

_ICON_PATH = Path(__file__).resolve().parent / "assets" / "ico.png"

st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon=str(_ICON_PATH),
    layout="wide",
)

# ---------------------------------------------------------------------------
# Conexão Snowflake
# ---------------------------------------------------------------------------

try:
    session = get_snowflake_session()
except Exception as exc:
    st.error(
        f"❌ Não foi possível conectar ao Snowflake.\n\n"
        f"Verifique as credenciais em `.streamlit/secrets.toml`.\n\n`{exc}`"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar  (spec 05 — botões obrigatórios)
# ---------------------------------------------------------------------------

with st.sidebar:
    _ico = Path(__file__).resolve().parent / "assets" / "ico.png"
    st.image(str(_ico), width=64)
    st.markdown("### COVID-19 Dashboard")
    st.caption("Dados: [Our World in Data](https://ourworldindata.org/coronavirus)")
    st.divider()

    # Botão 1 — spec 05: "⬇ Carregar Dados no Snowflake"
    # Adaptado: upload via file_uploader em vez de download automático
    btn_upload = st.button(
        "⬇ Carregar Dados no Snowflake",
        use_container_width=True,
        help="Faz upload do CSV OWID e grava no Snowflake.",
    )

    # Botão 2 — spec 05: "📊 Carregar Dashboard"
    btn_load = st.button(
        "📊 Carregar Dashboard",
        use_container_width=True,
        help="Lê a tabela do Snowflake e exibe o dashboard.",
    )

    st.divider()

    # Informação de status após dados carregados
    _status_placeholder = st.empty()

# ---------------------------------------------------------------------------
# Fluxo principal  (spec 05 — 4.3)
# ---------------------------------------------------------------------------

# Botão 1 → mostra tela de upload
if btn_upload:
    st.session_state["show_upload"] = True
    st.session_state.pop("df", None)  # limpa df para forçar re-load após upload

# Botão 2 → lê tabela do Snowflake e salva em session_state
if btn_load:
    with st.spinner("Carregando dados do Snowflake..."):
        st.session_state["df"] = load_covid_data(session)
    st.session_state["show_upload"] = False

# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------

show_upload = st.session_state.get("show_upload", False)
df = st.session_state.get("df")

if show_upload or (df is None and not table_has_data(session)):
    # Tela de onboarding / upload
    render_onboarding()

elif df is not None:
    # Dashboard com dados já carregados em session_state
    _status_placeholder.success(f"Snowflake — **{len(df):,} registros**")
    render_dashboard(df)

else:
    # Tabela existe mas nenhum botão foi clicado ainda — orienta o usuário
    st.info(
        "A tabela COVID19 já possui dados gravados. Carregue o dashboard para visualizar.",
        icon="📊",
    )
    if st.button("📊 Carregar Dashboard", use_container_width=True, type="primary"):
        with st.spinner("Carregando dados do Snowflake..."):
            st.session_state["df"] = load_covid_data(session)
        st.session_state["show_upload"] = False
        st.rerun()
