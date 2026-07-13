# PIX Observatory

> End-to-end analytics engineering project on the Brazilian PIX instant
> payments ecosystem. Combines public Banco Central statistics with synthetic
> transaction data, landed in **Snowflake** and transformed with **dbt** into a
> tested, documented Kimball star schema.
>
> Deliberately focused on two tools — **dbt** and **Snowflake** — to go deep
> instead of wide.

[![CI](https://github.com/REPLACE_ME/pix-observatory/actions/workflows/ci.yml/badge.svg)](https://github.com/REPLACE_ME/pix-observatory/actions)
[![dbt docs](https://img.shields.io/badge/dbt-docs-orange)](https://REPLACE_ME.github.io/pix-observatory/)
[![Streamlit](https://img.shields.io/badge/Streamlit-live-FF4B4B)](https://pix-observatory.streamlit.app/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Why this project

The Brazilian PIX system processes billions of transactions per month and is one
of the most successful instant-payment platforms in the world — yet there are
no public data products exploring it end-to-end.

This repo builds one, using real public data from Banco Central combined with a
calibrated synthetic transaction generator. It exists as both a useful analytical
artifact and a demonstration of a modern data-engineering stack.

## Architecture

```
Bacen API ──┐
            ├─► S3 raw ──► External Stage + Snowpipe ──► Snowflake RAW (bronze)
Synthetic ──┘   (Parquet)      (auto-ingest)                     │
generator                                                        │ dbt
                                                                 ▼
                                            STAGING ─► INTERMEDIATE ─► MARTS_KIMBALL
                                            (views)    (ephemeral)    (star schema,
                                                                       incremental,
                                                                       SCD2 snapshots)
                                                                 │
                                                                 ▼
                                                    dbt docs (GH Pages) · Streamlit
```

CI/CD on GitHub Actions (dbt build in an isolated Snowflake env via zero-copy
clone, slim CI with `--defer --state`). Quality enforced by dbt tests +
dbt_expectations. See [`docs/arquitetura.md`](docs/arquitetura.md) for the full
diagram and decisions.

## Stack

**Focus tools in bold.**

| Layer | Tool |
|---|---|
| Ingestion (reused) | Python (httpx, pydantic), Faker |
| Storage (raw) | Amazon S3 (Parquet, partitioned) |
| Warehouse | **Snowflake** (storage integration, external stage, Snowpipe, RBAC, warehouses, resource monitor, zero-copy clone, Time Travel) |
| Transformation | **dbt Core** (sources+freshness, staging/intermediate/marts, snapshots SCD2, seeds, incremental, tests, macros, packages, exposures, docs) |
| Quality | dbt tests, dbt_expectations |
| Serving | dbt docs (GitHub Pages), Streamlit |
| CI/CD | GitHub Actions (slim CI, defer/state) |

Out of scope (see [ADR-007](docs/decisoes-tecnicas.md)): AWS Glue/PySpark,
Airflow, ML (Prophet/MLflow), Metabase, Terraform, Data Vault/OBT — kept as
future *stretch* / satellite projects.

## Modeling — Kimball star schema

A single dimensional model, done with depth: `fct_transacao_pix` (transaction
grain, incremental) surrounded by conformed dimensions, with `dim_instituicao`
versioned as SCD Type 2 via a dbt snapshot and `dim_tempo` built from a seed.
See [`docs/modelagem-kimball.md`](docs/modelagem-kimball.md).

## Quick start

```bash
# Clone and install
git clone https://github.com/REPLACE_ME/pix-observatory.git
cd pix-observatory
uv sync                              # or: pip install -e ".[dev]"
pre-commit install

# Configure credentials (see .env.example)
cp .env.example .env
# fill in SNOWFLAKE_*, AWS_* (S3 raw bucket)

# Land data into Snowflake RAW (S3 + Snowpipe already configured), then:
cd dbt
dbt deps
dbt build --target dev               # staging → intermediate → marts + tests
dbt docs generate && dbt docs serve  # lineage + catalog
```

## Repository layout

```
pix-observatory/
├── ingestion/          # Bacen client + synthetic generator (reused)
├── snowflake/          # DDL: warehouses, RBAC, stage, Snowpipe, resource monitor
├── dbt/                # models (staging, intermediate, marts_kimball), snapshots, seeds, macros, tests
├── streamlit_app/      # light dashboard
└── docs/               # architecture, ADRs, Kimball modeling, 4-week roadmap
```

> Legacy dirs (`glue/`, `airflow/`, `ml/`, `infra/terraform/`,
> `great_expectations/`) belong to the earlier wide-scope plan and are kept only
> for reference / future stretch work.

## Data sources

- **Banco Central — Olinda API** ([docs](https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/))
  — public aggregated PIX statistics (volumes, transactions by type, institution
  rankings).
- **Synthetic transaction generator** — Python module under `ingestion/synthetic_generator/`
  that produces individual transactions calibrated to match the real Bacen
  distributions (volume curves, key types, value buckets, hourly seasonality).
  No proprietary data anywhere in this repo.

## Project status

Actively under development — 4-week focused plan (see
[`docs/roadmap-4-semanas.md`](docs/roadmap-4-semanas.md)):

- [x] Ingestion — Bacen client + synthetic generator (reused)
- [ ] Week 1 — Snowflake foundation + Snowpipe landing
- [ ] Week 2 — dbt foundation (sources, staging, intermediate)
- [ ] Week 3 — Kimball star schema (fact, dims, SCD2 snapshot, incremental)
- [ ] Week 4 — Quality, CI/CD, dbt docs on GitHub Pages, dashboard

## License

MIT — see [LICENSE](LICENSE).
