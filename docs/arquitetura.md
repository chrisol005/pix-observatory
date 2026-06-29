# Arquitetura

## Visão geral

PIX Observatory é uma plataforma de dados batch + micro-batch sobre o
ecossistema PIX brasileiro. Funciona em três camadas lógicas — ingestão,
armazenamento/transformação e consumo — orquestradas por Airflow e
testadas continuamente por GitHub Actions.

## Diagrama lógico

```
┌─────────────────────────┐    ┌──────────────────────────┐
│ Bacen API (estatísticas)│    │ Synthetic Generator (Py) │
└────────────┬────────────┘    └────────────┬─────────────┘
             │                              │
             └──────────────┬───────────────┘
                            ▼
                  ┌───────────────────┐
                  │  S3 raw (Parquet) │  particionado por dt=YYYY-MM-DD
                  └─────────┬─────────┘
                            ▼
                  ┌───────────────────┐
                  │ AWS Glue (PySpark)│  limpeza, dedupe, padronização
                  └─────────┬─────────┘
                            ▼
                  ┌───────────────────┐
                  │  S3 processed     │
                  └─────────┬─────────┘
                            ▼
                  ┌───────────────────┐
                  │   Snowpipe        │  auto-ingest
                  └─────────┬─────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │           SNOWFLAKE                   │
        │                                       │
        │  bronze ── silver ── gold             │
        │  (raw)    (dbt)    (dbt × 3 estilos) │
        └─────────────┬─────────────────────────┘
                      ▼
        ┌─────────────────────────────┐
        │ Exposures (dbt)             │
        │  • Streamlit app            │
        │  • Metabase dashboard       │
        │  • Prophet forecast UDF     │
        └─────────────────────────────┘
```

> Versão final em alta resolução: substituir este ASCII por export do
> Excalidraw (`docs/img/arquitetura.png`) na semana 8.

## Componentes

### Ingestão

- **`ingestion/bacen/`** — cliente da API Olinda do Banco Central. Faz
  paginação OData, valida com Pydantic e grava em Parquet no S3.
- **`ingestion/synthetic_generator/`** — gera transações PIX individuais
  calibradas pelas distribuições reais do Bacen (volume diário, mix de
  tipos de chave, sazonalidade horária, distribuição de valores).
  Determinístico via seed para reproducibilidade.

### Storage (raw + processed)

- **S3 raw**: `s3://pix-observatory-raw/{source}/dt=YYYY-MM-DD/*.parquet`
- **S3 processed**: dataset limpo e padronizado, pronto para Snowpipe.
- Particionamento por data; compressão Snappy; arquivos de ~128 MB.

### Processamento distribuído

- **AWS Glue Job (PySpark)** — uma única DAG processa backfills históricos.
  Workflow normal usa Snowpipe direto; Glue só entra para reprocessamentos.
- Justificativa: para volumes diários, Snowpipe + dbt resolvem com menor
  custo. Spark fica reservado para casos onde realmente vale.

### Data Warehouse — Snowflake

```
PIX_OBSERVATORY_DEV / PROD
├── RAW.*                  ← targets do Snowpipe
├── STAGING.stg_*          ← views dbt
├── INTERMEDIATE.int_*     ← ephemeral
├── MARTS_KIMBALL.*        ← star schema
├── MARTS_DATA_VAULT.*     ← hubs / links / satellites
├── MARTS_OBT.*            ← One Big Table
└── SNAPSHOTS.*            ← dbt snapshots (SCD2)
```

RBAC:
- `DEVELOPER` — read/write em DEV
- `CI` — read/write em CI (schemas efêmeros por GITHUB_RUN_ID)
- `ANALYTICS` — read em PROD, write nas marts

### Transformação — dbt

- **staging** (views): renomeação, cast, conformação de tipos
- **intermediate** (ephemeral): joins e enriquecimentos reusáveis
- **marts**: três paradigmas paralelos (ver `modelagem-comparativa.md`)
- **snapshots**: SCD Type 2 em `dim_instituicao`

### Orquestração — Airflow

DAGs principais:
- `ingest_bacen` — diária, busca dados novos do Bacen
- `generate_synthetic` — diária, gera o lote sintético do dia
- `transform_dbt` — sensor em S3 processed → `dbt build`
- `ml_forecast` — semanal, retreina Prophet e registra no MLflow
- `quality_checks` — diária, Great Expectations + alertas Slack

### Qualidade

- **Great Expectations** valida contratos na bronze (schema, distribuições,
  freshness máximo).
- **dbt tests** genéricos (`not_null`, `unique`, `relationships`,
  `accepted_values`) em toda staging e marts.
- **Tests customizados**:
  - continuidade temporal (sem buracos de dias)
  - conservação de massa entre camadas
  - sanity em métricas financeiras (valor > 0)

### CI/CD

- PR → ruff, mypy, pytest, `dbt build` em schema CI temporário
- Merge em main → deploy do dbt em PROD; upload do manifest.json para S3
  (usado pelo slim CI dos próximos PRs).

### Serving

- **Streamlit Cloud** — app público com forecast, ranking, drill-downs
- **Metabase** (Docker) — dashboards para exploração ad-hoc
- **Snowflake Python UDF** — modelo Prophet servido in-database e
  consumido como model dbt

## Decisões importantes

Registradas em `docs/decisoes-tecnicas.md` no formato ADR.

## Custos

Orçamento mensal estimado: ~US$47, distribuído entre:

- Snowflake (pós-trial): ~US$15
- AWS Glue: ~US$10
- AWS MWAA (opcional): ~US$20
- AWS S3 + Lambda: ~US$2
- Streamlit Cloud: US$0 (tier gratuito)
