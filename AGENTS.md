# AGENTS.md — COVID Snowflake Dashboard

Regras de comportamento para agentes que trabalham neste projeto.

---

## Fluxo obrigatório de trabalho

### 1. Leia as specs antes de qualquer implementação

- Todo trabalho de código parte das specs em `/specs/`.
- Leia o `specs/README.md` para entender o índice e o status de cada etapa.
- Leia o arquivo de spec da etapa antes de escrever qualquer linha de código.
- Não implemente nada que não esteja descrito nas specs.

### 2. Marque tarefas ao avançar

Use o `task.md` (em `brain/<conversation-id>/`) para rastrear progresso:

| Símbolo | Significado |
|---------|-------------|
| `[ ]`   | Pendente |
| `[/]`   | Em andamento |
| `[x]`   | Concluída |

- Marque `[/]` ao **iniciar** uma tarefa.
- Marque `[x]` ao **finalizar** — só depois de verificar que funciona.
- Atualize `task.md` a cada mudança de estado, não em lote no final.

### 3. Informe o usuário ao concluir etapas

Ao concluir uma etapa relevante:

- Resuma o que foi feito (sem repetir o código inteiro).
- Aponte o próximo passo.
- Se houver bloqueio ou decisão necessária, pergunte — não assuma.

---

## Regras de código

- **Modularização**: lógica de dados fica em `src/db/`, renderização em `src/dashboard.py`, orquestração em `src/main.py`.
- **Sem hardcode de credenciais**: `database`, `schema`, `table` e credenciais Snowflake sempre via `st.secrets["snowflake"]`.
- **Sem download automático**: o CSV OWID nunca é baixado pelo app. O usuário faz upload via `st.file_uploader`.
- **Sem leitura local**: sem fallback para arquivo em disco.
- **Filtro de colunas**: ao ingerir no Snowflake, manter apenas `KEEP_COLUMNS` (as 10 colunas principais usadas nas visualizações).
- **Filtro de países**: usar `DEFAULT_COUNTRIES` como padrão (`Brazil`, `Spain`, `Portugal`, `United States`, `South Africa`, `China`).
- **Design/UI**: É estritamente proibido o uso de paletas de cores "IAish" (tons de índigo, violeta, roxo neon) ou elementos que remetam a design típico de LLMs. Usar sempre cores corporativas clássicas ou paletas de dados neutras.

---

## Specs e status

| # | Arquivo | Etapa | Status |
|---|---------|-------|--------|
| 00 | `specs/00-objetivo.md` | Objetivo e competências | em andamento |
| 01 | `specs/01-dataset.md` | Dataset OWID | concluída |
| 02 | `specs/02-snowflake-conta.md` | Conta Snowflake | concluída |
| 03 | `specs/03-ambiente-local.md` | Ambiente local | concluída |
| 04 | `specs/04-credenciais.md` | Credenciais | concluída |
| 05 | `specs/05-script-carga-dashboard.md` | Script de carga e dashboard | **em andamento** |
| 06 | `specs/06-visualizacoes.md` | Visualizações obrigatórias | **em andamento** |
| 07 | `specs/07-teste-local.md` | Teste local | pendente |
| 08 | `specs/08-github.md` | GitHub | pendente |
| 09 | `specs/09-deploy.md` | Deploy Streamlit Cloud | pendente |
| 10 | `specs/10-entrega-e-avaliacao.md` | Entrega e avaliação | pendente |
