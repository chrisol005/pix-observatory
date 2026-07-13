# Arquitetura (escopo enxuto: dbt + Snowflake)

## Visão geral

PIX Observatory é uma plataforma de dados batch sobre o ecossistema PIX
brasileiro. O escopo foi deliberadamente enxugado para concentrar profundidade
em **duas ferramentas**: **dbt** (transformação, prioridade 1) e **Snowflake**
(data warehouse, prioridade 2). A ingestão em Python já existente alimenta o
Snowflake; o dbt faz todo o trabalho analítico até um star schema Kimball
testado e documentado.

Três camadas lógicas: **ingestão → warehouse/transformação → consumo**.

## Diagrama lógico

```
┌─────────────────────────┐    ┌──────────────────────────┐
│ Bacen API (estatísticas)│    │ Synthetic Generator (Py) │   ◄── já construído
└────────────┬────────────┘    └────────────┬─────────────┘
             └──────────────┬───────────────┘
                            ▼
                  ┌───────────────────┐
                  │  S3 raw (Parquet) │  particionado por dt=YYYY-MM-DD
                  └─────────┬─────────┘
                            ▼
                  ┌───────────────────┐
                  │ External Stage    │  ◄── SNOWFLAKE
                  │   + Snowpipe      │      (storage integration, auto-ingest)
                  └─────────┬─────────┘
                            ▼
        ┌───────────────────────────────────────┐
        │              SNOWFLAKE                 │
        │                                        │
        │  RAW ──► STAGING ──► INTERMEDIATE ──► MARTS_KIMBALL
        │ (bronze)  (dbt view) (dbt ephemeral)  (dbt table/incremental)
        │                                        │
        │  + SNAPSHOTS (SCD2)  + SEEDS (dim_tempo)
        └─────────────────┬──────────────────────┘
                          │  ◄── DBT: staging → intermediate → marts,
                          │       snapshots, seeds, tests, macros, exposures
                          ▼
        ┌─────────────────────────────┐
        │ Consumo                     │
        │  • dbt docs (lineage) — GH Pages
        │  • Dashboard leve (Streamlit)
        └─────────────────────────────┘
```

> Versão final em alta resolução: substituir este ASCII por export do
> Excalidraw (`docs/img/arquitetura.png`) na semana 4.

## Componentes

### Ingestão (reaproveitada — Python)

- **`ingestion/bacen/`** — cliente da API Olinda do Banco Central. Paginação
  OData, validação com Pydantic, grava Parquet no S3.
- **`ingestion/synthetic_generator/`** — gera transações PIX individuais
  calibradas pelas distribuições reais do Bacen (volume diário, mix de tipos de
  chave, sazonalidade horária, distribuição de valores). Determinístico via seed.

Nada muda aqui: é a fonte dos dados. O foco do projeto está a jusante.

### Storage (raw) — S3

- **S3 raw**: `s3://pix-observatory-raw/{source}/dt=YYYY-MM-DD/*.parquet`
- Particionamento por data; compressão Snappy.
- Único componente AWS mantido — mínimo necessário para alimentar o Snowpipe.

### Data Warehouse — Snowflake (prioridade 2)

Ingestão para o Snowflake via **storage integration + external stage +
Snowpipe** (auto-ingest do S3). Nada de Glue/PySpark: para o volume do projeto,
Snowpipe + dbt resolvem com menor custo e mais foco.

```
PIX_OBSERVATORY_DEV / PROD
├── RAW.*                 ← targets do Snowpipe (bronze)
├── STAGING.stg_*         ← views dbt
├── INTERMEDIATE.int_*    ← ephemeral dbt
├── MARTS_KIMBALL.*       ← star schema (fato + dims)
└── SNAPSHOTS.*           ← dbt snapshots (SCD2)
```

RBAC:
- `DEVELOPER` — read/write em DEV
- `CI` — ambiente isolado (zero-copy clone ou schema por `GITHUB_RUN_ID`)
- `ANALYST` — read em PROD

Recursos Snowflake exercitados: warehouses (XS, auto-suspend/resume), RBAC,
storage integration, external stage, Snowpipe, resource monitor (custo),
zero-copy clone (CI), Time Travel. *Stretch*: Streams + Tasks, Python UDF.

### Transformação — dbt (prioridade 1)

Coração do projeto. Segue as [best practices de estrutura do dbt](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview):

- **staging** (`stg_*`, view): renomeação, cast, conformação de tipos.
- **intermediate** (`int_*`, ephemeral): joins e enriquecimentos reusáveis.
- **marts** (`MARTS_KIMBALL`, table/incremental): star schema Kimball.
- **snapshots**: SCD Type 2 em `dim_instituicao`.
- **seeds**: `dim_tempo` e tabelas de referência pequenas.

Recursos dbt exercitados: sources + freshness, materializações (view / ephemeral
/ table / incremental), testes genéricos (`not_null`, `unique`, `relationships`,
`accepted_values`), testes singulares/customizados, macros, packages
(`dbt_utils`, `dbt_expectations`, `codegen`), snapshots, seeds, exposures, e
`dbt docs` (lineage) hospedado no GitHub Pages.

### Qualidade

- **dbt tests genéricos** em toda staging e marts.
- **dbt_expectations** para distribuições e ranges na staging.
- **Testes customizados**: continuidade temporal (sem buracos de dias),
  conservação de massa entre camadas, sanity financeiro (`valor > 0`).

### CI/CD

- PR → ruff, mypy, pytest, `dbt build --target ci` em **ambiente isolado**
  (zero-copy clone ou schema temporário).
- **Slim CI**: `--defer --state` contra o `manifest.json` de PROD.
- Merge em `main` → `dbt build --target prod` + upload do manifest para S3.

### Serving

- **dbt docs** — lineage e catálogo público via GitHub Pages.
- **Dashboard leve** — Streamlit simples consumindo os marts Kimball (ou
  consumo direto por SQL). Sem Metabase.

## O que saiu do escopo (e por quê)

Ver `decisoes-tecnicas.md`, ADR-007. Em resumo: Glue/PySpark, Airflow,
ML (Prophet/MLflow), Metabase, Terraform e as modelagens Data Vault/OBT foram
removidos do núcleo para maximizar profundidade em dbt + Snowflake — as duas
ferramentas mais demandadas nas vagas-alvo. Vários viram itens *stretch* ou
projetos-satélite.

## Custos

Orçamento mensal estimado: **~US$15–17** (bem abaixo do teto de US$50):

- Snowflake (pós-trial): ~US$15 (warehouse XS com auto-suspend agressivo)
- AWS S3: ~US$1–2
- GitHub Actions / GitHub Pages / Streamlit Cloud: US$0 (tiers gratuitos)
