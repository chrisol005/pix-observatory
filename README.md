# PIX Observatory

> End-to-end data platform on the Brazilian PIX instant payments ecosystem.
> Combines public Banco Central statistics with synthetic transaction data,
> built on AWS + Snowflake with dbt, Airflow, and modern data engineering practices.

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
            ├─► S3 raw ──► AWS Glue (PySpark) ──► S3 processed ──► Snowpipe
Synthetic ──┘                                                          │
generator                                                              ▼
                                                                  Snowflake
                                                                  bronze
                                                                     │
                                                                  dbt│
                                                                     ▼
                                                              silver / gold
                                                          (Kimball, Data Vault, OBT)
                                                                     │
                                                                     ▼
                                                       Streamlit · Metabase · Prophet UDF
```

Orchestrated by Airflow. CI/CD on GitHub Actions. Quality enforced by Great
Expectations + dbt tests. See [`docs/arquitetura.md`](docs/arquitetura.md) for
the full diagram and decisions.

## Stack

| Layer | Tool |
|---|---|
| Ingestion | Python (httpx, pydantic), Faker, AWS Lambda |
| Storage (raw) | Amazon S3 (Parquet, partitioned) |
| Processing | AWS Glue (PySpark) |
| Warehouse | Snowflake (Snowpipe, Streams, Tasks, Python UDFs) |
| Transformation | dbt Core |
| Orchestration | Apache Airflow (Astro CLI local / MWAA) |
| Quality | Great Expectations, dbt tests |
| ML | Prophet, MLflow |
| Serving | Streamlit, Metabase |
| CI/CD | GitHub Actions |
| IaC (stretch) | Terraform |

## Three modeling approaches, one source of truth

The same transactional data is materialized into three parallel mart schemas:

- `marts.kimball.*` — classic star schema with fact + conformed dimensions and SCD2 snapshots
- `marts.data_vault.*` — hubs / links / satellites following Data Vault 2.0
- `marts.obt.*` — one big table, denormalized for ML feature stores and ad-hoc exploration

Each is benchmarked on query latency, storage cost, schema-evolution friction,
and auditability. See [`docs/modelagem-comparativa.md`](docs/modelagem-comparativa.md).

## Quick start

```bash
# Clone and install
git clone https://github.com/REPLACE_ME/pix-observatory.git
cd pix-observatory
uv sync                              # or: pip install -e ".[dev]"
pre-commit install

# Spin up local stack
docker-compose up -d                 # Airflow + Metabase

# Configure credentials (see .env.example)
cp .env.example .env
# fill in SNOWFLAKE_*, AWS_*, etc.

# Run dbt against your dev schema
cd dbt && dbt build --target dev
```

## Repository layout

```
pix-observatory/
├── ingestion/          # Bacen client + synthetic generator
├── glue/               # PySpark jobs for AWS Glue
├── airflow/dags/       # orchestration
├── dbt/                # models (staging, intermediate, marts × 3)
├── great_expectations/ # bronze contracts
├── ml/                 # Prophet forecast + MLflow
├── streamlit_app/      # public dashboard
├── infra/terraform/    # IaC (stretch)
└── docs/               # architecture, ADRs, modeling comparison
```

## Data sources

- **Banco Central — Olinda API** ([docs](https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/))
  — public aggregated PIX statistics (volumes, transactions by type, institution
  rankings).
- **Synthetic transaction generator** — Python module under `ingestion/synthetic_generator/`
  that produces individual transactions calibrated to match the real Bacen
  distributions (volume curves, key types, value buckets, hourly seasonality).
  No proprietary data anywhere in this repo.

## Project status

Actively under development. Component checklist:

- [ ] Ingestion — Bacen client + synthetic generator
- [ ] Snowflake + dbt foundations
- [ ] Airflow + Glue orchestration
- [ ] Kimball modeling
- [ ] Data Vault + OBT modeling
- [ ] Data quality + CI/CD
- [ ] ML forecast + serving
- [ ] Documentation polish

## License

MIT — see [LICENSE](LICENSE).
