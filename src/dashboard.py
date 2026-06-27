"""
src/dashboard.py
================
Renderização do dashboard COVID-19 (visualizações + onboarding).
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from db.load_data import (
    DEFAULT_COUNTRIES,
    OWID_URL,
    filter_owid_df,
    get_snowflake_session,
    ingest_csv_to_snowflake,
    validate_owid_csv,
)
from db.query_data import load_covid_data, run_custom_query

# ---------------------------------------------------------------------------
# Onboarding — tela exibida quando não há dados no Snowflake
# ---------------------------------------------------------------------------


def render_onboarding() -> None:
    """Tela de boas-vindas exibida quando a tabela COVID19 está vazia."""

    # Centraliza o conteúdo com colunas (UX/UI premium)
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown(
            """
            <div style="text-align:center; padding: 3rem 0 2rem;">
                <span style="font-size:4.5rem; display:block; margin-bottom:1rem">🗄️</span>
                <h1 style="margin-bottom:.5rem; font-size: 2.2rem; font-weight: 800;">Setup Inicial do Dashboard</h1>
                <p style="color:var(--text-color); opacity:.7; font-size:1.1rem; line-height:1.5;">
                    Parece que sua tabela <code>COVID19</code> no Snowflake está vazia. <br>
                    Vamos carregá-la em 2 passos simples.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "**Passo 1:** Baixe o arquivo de dados brutos (CSV) diretamente do repositório oficial da OWID:\n\n"
            f"[👉 Clique aqui para baixar]({OWID_URL})\n\n"
            "**Passo 2:** Faça o upload do arquivo logo abaixo para processar e gravar no Snowflake.",
            icon="ℹ️",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📤 Área de Upload", anchor=False)

        uploaded = st.file_uploader(
            "Selecione o arquivo `owid-covid-data.csv`",
            type=["csv"],
            help="Somente arquivos com a estrutura padrão OWID são aceitos.",
        )

    if uploaded is None:
        return

    with st.spinner("Validando arquivo..."):
        try:
            df_raw = pd.read_csv(uploaded, low_memory=False)
        except Exception as exc:
            st.error(f"Erro ao ler o CSV: {exc}")
            return

    ok, msg = validate_owid_csv(df_raw)
    if not ok:
        st.error(msg)
        return

    st.success("✅ Arquivo válido! Aplicando filtros...")

    # Configurações do filtro antes de gravar
    with st.expander("⚙️ Configurar filtros de ingestão", expanded=True):
        all_countries = sorted(df_raw[df_raw["continent"].notna()]["location"].unique())
        selected_countries = st.multiselect(
            "Países a incluir",
            options=all_countries,
            default=[c for c in DEFAULT_COUNTRIES if c in all_countries],
        )
        start_date = st.text_input(
            "Data inicial (AAAA-MM-DD) — deixe em branco para incluir tudo",
            value="2021-01-01",
        )

    if not selected_countries:
        st.warning("Selecione ao menos um país.")
        return

    if st.button("⬇ Gravar no Snowflake", type="primary", use_container_width=True):
        with st.spinner("Filtrando e gravando no Snowflake..."):
            try:
                df_filtered = filter_owid_df(
                    df_raw,
                    countries=selected_countries,
                    start_date=start_date or None,
                )
                session = get_snowflake_session()
                nrows = ingest_csv_to_snowflake(session, df_filtered)
                st.success(f"✅ {nrows:,} linhas gravadas com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Erro ao gravar no Snowflake: {exc}")


# ---------------------------------------------------------------------------
# Dashboard principal
# ---------------------------------------------------------------------------


def render_dashboard(df: pd.DataFrame) -> None:
    """Renderiza KPIs (st.metric), filtros na sidebar, 4 gráficos + abas extras."""

    import base64
    from pathlib import Path as _Path
    from db.load_data import _get_database, _get_schema, _get_table_name

    # ── Cabeçalho com ícone + badge Snowflake (mantido por pedido do usuário) ─
    _ico_path = _Path(__file__).resolve().parent / "assets" / "ico.png"
    _ico_b64 = base64.b64encode(_ico_path.read_bytes()).decode()

    _db_label = f"{_get_database()}.{_get_schema()}.{_get_table_name()}"
    _n_rows   = f"{len(df):,}"
    _min_dt   = df["date"].min().strftime("%d/%m/%Y") if not df.empty else "—"
    _max_dt   = df["date"].max().strftime("%d/%m/%Y") if not df.empty else "—"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:.5rem">
            <img src="data:image/png;base64,{_ico_b64}" width="52">
            <div style="flex:1">
                <h2 style="margin:0;line-height:1.1">COVID-19 Dashboard</h2>
                <span style="opacity:.55;font-size:.85rem">
                    Fonte: Our World in Data (OWID)
                </span>
            </div>
            <div style="
                background:rgba(0,104,201,.1);
                border:1px solid rgba(0,104,201,.25);
                border-radius:8px;padding:.5rem .85rem;
                font-size:.78rem;line-height:1.6;text-align:right
            ">
                <span style="opacity:.6">Snowflake</span>
                <br><code style="font-size:.72rem">{_db_label}</code>
                <br><span style="opacity:.7">{_n_rows} linhas &nbsp;·&nbsp; {_min_dt} – {_max_dt}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Filtros na sidebar  (spec 06 — st.multiselect + st.slider) ──────────
    st.sidebar.header("Filtros")

    all_countries = sorted(df["location"].unique())
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    selected = st.sidebar.multiselect(
        "Países",
        options=all_countries,
        default=all_countries,
    )

    date_range = st.sidebar.slider(
        "Período",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="DD/MM/YYYY",
    )

    st.sidebar.caption(
        "ℹ️ **Aviso:** Estes filtros afetam apenas as visualizações e dados brutos. "
        "Eles **não** se aplicam à aba *Query SQL*, que consulta os dados originais no Snowflake."
    )


    # Aplica filtros
    mask = (
        df["location"].isin(selected)
        & (df["date"].dt.date >= date_range[0])
        & (df["date"].dt.date <= date_range[1])
    )
    fdf = df[mask].copy()

    if fdf.empty:
        st.warning("Nenhum dado para os filtros selecionados.")
        return

    # ── KPIs  (spec 06 — st.metric, mínimo 3) ───────────────────────────────
    latest = fdf.sort_values("date").groupby("location").last().reset_index()
    total_cases  = int(latest["total_cases"].sum(skipna=True))
    total_deaths = int(latest["total_deaths"].sum(skipna=True))
    n_countries  = fdf["location"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Casos",  f"{total_cases:,}")
    col2.metric("Total de Óbitos", f"{total_deaths:,}")
    col3.metric("Países",          n_countries)

    st.divider()


    # ── Abas ────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Novos Casos",
        "💀 Óbitos",
        "💉 Vacinação",
        "🫧 Dispersão",
        "📋 Dados Brutos",
        "🔍 Query SQL",
    ])

    def _export_btn(df_exp: pd.DataFrame, filename: str, key: str) -> None:
        """Botão de download CSV com todos os dados brutos do filtro ativo."""
        st.download_button(
            label="⬇ Exportar dados brutos (CSV)",
            data=df_exp.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv",
            key=key,
        )


    with tab1:
        st.subheader("Evolução de Novos Casos por País")
        fig1 = px.line(
            fdf,
            x="date",
            y="new_cases",
            color="location",
            labels={"date": "Data", "new_cases": "Novos Casos", "location": "País"},
            template="plotly_white",
        )
        fig1.update_layout(
            font=dict(family="sans-serif", color="#374151"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#E5E7EB", gridwidth=1),
        )
        fig1.update_traces(line_width=3)
        st.plotly_chart(fig1, use_container_width=True)
        _export_btn(fdf, "novos_casos.csv", "dl_tab1")

    # ── Tab 2: Total de óbitos por país ─────────────────────────────────────
    with tab2:
        st.subheader("Óbitos por País (data mais recente)")
        bar_df = latest[["location", "total_deaths"]].dropna().sort_values(
            "total_deaths", ascending=False
        )
        fig2 = px.bar(
            bar_df,
            x="location",
            y="total_deaths",
            color="location",
            labels={"location": "País", "total_deaths": "Total de Óbitos"},
            template="plotly_white",
        )
        fig2.update_layout(
            showlegend=False,
            font=dict(family="sans-serif", color="#374151"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#E5E7EB"),
            barmode="group",
            bargap=0.3,
        )
        fig2.update_traces(marker_line_width=0, opacity=0.9, marker=dict(cornerradius=4))
        st.plotly_chart(fig2, use_container_width=True)
        _export_btn(
            fdf[["location", "date", "total_deaths", "new_deaths"]],
            "óbitos.csv", "dl_tab2",
        )

    # ── Tab 3: Proporção vacinados ───────────────────────────────────────────
    with tab3:
        st.subheader("Proporção de Vacinados (≥ 1 dose) por País")
        vac_df = latest[["location", "people_vaccinated", "population"]].dropna()
        vac_df = vac_df[vac_df["population"] > 0].copy()
        vac_df["pct_vacinados"] = (
            vac_df["people_vaccinated"] / vac_df["population"] * 100
        ).round(2)
        fig3 = px.pie(
            vac_df,
            names="location",
            values="pct_vacinados",
            labels={"location": "País", "pct_vacinados": "% Vacinados"},
            template="plotly_white",
            hole=0.45,
        )
        fig3.update_layout(
            font=dict(family="sans-serif", color="#374151"),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        fig3.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
        st.plotly_chart(fig3, use_container_width=True)
        vac_export = fdf[["location", "date", "people_vaccinated",
                          "people_fully_vaccinated", "population"]].copy()
        _export_btn(vac_export, "vacinacao.csv", "dl_tab3")

    # ── Tab 4: Dispersão população × total de casos ─────────────────────────
    with tab4:
        st.subheader("Relação: População × Total de Casos")
        scat_df = latest[["location", "population", "total_cases"]].dropna()
        fig4 = px.scatter(
            scat_df,
            x="population",
            y="total_cases",
            color="location",
            size="total_cases",
            text="location",
            labels={
                "population": "População",
                "total_cases": "Total de Casos",
                "location": "País",
            },
            template="plotly_white",
        )
        fig4.update_layout(
            font=dict(family="sans-serif", color="#374151"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(gridcolor="#E5E7EB"),
            yaxis=dict(gridcolor="#E5E7EB"),
        )
        fig4.update_traces(textposition="top center", marker=dict(line=dict(width=1, color='DarkSlateGrey')))
        st.plotly_chart(fig4, use_container_width=True)
        scat_export = fdf[["location", "date", "population",
                           "total_cases", "new_cases"]].copy()
        _export_btn(scat_export, "dispersao.csv", "dl_tab4")

    # ── Tab 5: Dados Brutos ──────────────────────────────────────────────────
    with tab5:
        st.subheader("Dados Brutos")
        
        # Prepara df para visualização: calcula percentual de vacinados
        df_vis = fdf.copy()
        df_vis["pct_vacinados"] = (df_vis["people_vaccinated"] / df_vis["population"]) * 100
        df_vis["pct_vacinados"] = df_vis["pct_vacinados"].fillna(0)

        # Configuração de colunas premium
        st.dataframe(
            df_vis,
            use_container_width=True,
            hide_index=True,
            column_config={
                "location": st.column_config.TextColumn("País", width="medium"),
                "date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "total_cases": st.column_config.NumberColumn("Total de Casos", format="%d"),
                "total_deaths": st.column_config.NumberColumn("Óbitos", format="%d"),
                "new_cases": st.column_config.NumberColumn("Novos Casos", format="%d"),
                "pct_vacinados": st.column_config.ProgressColumn(
                    "% Vacinados",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
            column_order=["location", "date", "total_cases", "new_cases", "total_deaths", "pct_vacinados"]
        )
        csv_bytes = fdf.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Exportar CSV",
            data=csv_bytes,
            file_name="covid19_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Tab 6: Query SQL personalizada ──────────────────────────────────────
    with tab6:
        st.subheader("🔍 Query SQL Personalizada")
        st.caption(
            "Monte a query pelos controles abaixo — o SQL é gerado automaticamente. "
            "Você também pode editar o SQL diretamente, mas qualquer alteração nos controles irá sobrescrever."
        )

        from db.load_data import _get_database, _get_schema, _get_table_name

        db = _get_database()
        schema = _get_schema()
        table = _get_table_name()
        full_table = f"{db}.{schema}.{table}"

        all_cols = [
            "location", "continent", "date",
            "total_cases", "new_cases",
            "total_deaths", "new_deaths",
            "population", "people_vaccinated", "people_fully_vaccinated",
        ]
        all_locs = sorted(df["location"].unique().tolist())

        # ── Controles do query builder ───────────────────────────────────────
        st.markdown("#### ⚙️ Construtor de Query")

        qb_col1, qb_col2 = st.columns([3, 2])

        with qb_col1:
            sel_cols = st.multiselect(
                "Colunas (SELECT)",
                options=all_cols,
                default=["location", "date", "new_cases", "total_deaths"],
                key="qb_cols",
            )

        with qb_col2:
            sel_countries = st.multiselect(
                "Países (WHERE location IN)",
                options=all_locs,
                default=["Brazil"],
                key="qb_countries",
            )

        qb_col3, qb_col4, qb_col5 = st.columns(3)

        with qb_col3:
            date_from = st.date_input(
                "Data inicial",
                value=df["date"].min().date(),
                key="qb_date_from",
            )

        with qb_col4:
            order_col = st.selectbox(
                "ORDER BY",
                options=["date", "total_cases", "total_deaths", "new_cases", "location"],
                key="qb_order",
            )
            order_dir = st.radio(
                "Direção",
                options=["DESC", "ASC"],
                horizontal=True,
                key="qb_dir",
            )

        with qb_col5:
            page_size = st.selectbox(
                "Linhas por página",
                options=[10, 25, 50, 100, 250, 500],
                index=2,  # default 50
                key="qb_page_size",
            )

        # ── Geração automática da SQL (sem LIMIT/OFFSET — aplicados na paginação) ──
        cols_str = ", ".join(sel_cols) if sel_cols else "*"

        where_parts: list[str] = []
        if sel_countries:
            locs_sql = ", ".join(f"'{c}'" for c in sel_countries)
            where_parts.append(f"location IN ({locs_sql})")
        if date_from:
            where_parts.append(f"date >= '{date_from}'")

        where_clause = f"\nWHERE {' AND '.join(where_parts)}" if where_parts else ""

        # SQL base (sem paginação) — exibido no editor
        generated_sql = (
            f"SELECT {cols_str}\n"
            f"FROM {full_table}"
            f"{where_clause}\n"
            f"ORDER BY {order_col} {order_dir};"
        )

        # ── Força update do text_area quando os controles mudam ─────────────
        if st.session_state.get("qb_last_generated") != generated_sql:
            st.session_state["qb_last_generated"] = generated_sql
            st.session_state["qb_sql"] = generated_sql
            st.session_state["qb_page"] = 1  # reset página ao mudar query

        st.divider()
        st.markdown("#### 📝 SQL gerado")
        st.caption("Edite à mão se quiser — será sobrescrito ao alterar os controles acima. LIMIT/OFFSET são aplicados automaticamente pela paginação.")

        sql_input = st.text_area(
            "SQL",
            height=160,
            key="qb_sql",
            label_visibility="collapsed",
        )

        # ── Controles de execução e paginação ───────────────────────────────
        for _k, _v in [("qb_page", 1), ("qb_result", None), ("qb_result_page", 1),
                       ("qb_is_last", False)]:
            if _k not in st.session_state:
                st.session_state[_k] = _v

        exec_col, prev_col, page_col, next_col = st.columns([2, 1, 1, 1])

        with exec_col:
            run_btn = st.button("▶ Executar Query", type="primary", use_container_width=True)
        with prev_col:
            prev_btn = st.button(
                "◀ Anterior", use_container_width=True,
                disabled=st.session_state["qb_page"] <= 1,
            )
        with page_col:
            st.markdown(
                f"<div style='text-align:center;padding-top:8px'>"
                f"Pág. <b>{st.session_state['qb_page']}</b></div>",
                unsafe_allow_html=True,
            )
        with next_col:
            next_btn = st.button(
                "Próxima ▶", use_container_width=True,
                disabled=st.session_state.get("qb_is_last", False),
            )

        # Atualiza página conforme botão
        if run_btn:
            st.session_state["qb_page"] = 1
        elif prev_btn and st.session_state["qb_page"] > 1:
            st.session_state["qb_page"] -= 1
        elif next_btn:
            st.session_state["qb_page"] += 1

        # Busca do Snowflake somente quando botão pressionado
        if run_btn or prev_btn or next_btn:
            page = st.session_state["qb_page"]
            offset = (page - 1) * int(page_size)
            base_sql = sql_input.rstrip().rstrip(";")
            paged_sql = f"{base_sql}\nLIMIT {int(page_size)} OFFSET {offset};"

            with st.spinner(f"Executando página {page}..."):
                try:
                    session = get_snowflake_session()
                    result_df = run_custom_query(session, paged_sql)
                    st.session_state["qb_result"] = result_df
                    st.session_state["qb_result_page"] = page
                    st.session_state["qb_is_last"] = len(result_df) < int(page_size)
                except Exception as exc:
                    st.error(f"Erro na query: {exc}")
                    st.session_state["qb_result"] = None

        # Exibe resultado armazenado — persiste entre re-renders
        result_df = st.session_state.get("qb_result")
        if result_df is not None:
            rpage = st.session_state["qb_result_page"]
            n = len(result_df)
            st.success(f"✅ {n} linha(s) — página {rpage}")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            if st.session_state.get("qb_is_last"):
                st.info("Última página — não há mais registros.")
            if not result_df.empty:
                st.download_button(
                    label="⬇ Exportar página CSV",
                    data=result_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"query_p{rpage}.csv",
                    mime="text/csv",
                )




