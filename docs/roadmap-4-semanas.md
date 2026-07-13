# Roadmap — 4 semanas (escopo enxuto: dbt + Snowflake)

> Escopo refocado em **dbt (prioridade 1)** e **Snowflake (prioridade 2)** — as
> duas ferramentas com maior demanda nas vagas-alvo. Airflow, Glue/PySpark,
> ML (Prophet/MLflow), Metabase, Terraform e Data Vault/OBT saíram do escopo
> central (ver `decisoes-tecnicas.md`, ADR-007). A ingestão em Python já
> construída é reaproveitada como fonte dos dados.
>
> Cada semana tem entregável verificável e PR público no GitHub.

## Ponto de partida (já construído)

- Repo `pix-observatory` com scaffold, CI stub (ruff/mypy/pytest) e docs.
- Ingestão Python: cliente Bacen (OData/Olinda) + gerador sintético.
- Dados brutos de exemplo já em `data/raw/bacen/`.

O que muda: em vez de mandar tudo para Glue/Airflow/3 modelagens, a ingestão
alimenta o **Snowflake**, e o **dbt** faz todo o trabalho de transformação até
um star schema Kimball bem testado e documentado.

---

## Semana 1 — Snowflake foundation + landing dos dados

**Meta**: dados brutos aterrissados no Snowflake, plataforma configurada.

- [ ] Conta Snowflake trial (region compatível com o bucket S3)
- [ ] Databases `PIX_OBSERVATORY_DEV` e `PIX_OBSERVATORY_PROD`
- [ ] Warehouse `WH_PIX_XS` (XS, auto-suspend 60s, auto-resume)
- [ ] RBAC básico: roles `DEVELOPER`, `CI`, `ANALYST`; grants por schema
- [ ] Resource monitor com quota mensal (proteção de custo)
- [ ] Bucket S3 `pix-observatory-raw` (bootstrap manual)
- [ ] Ingestão Python grava Parquet particionado (`dt=YYYY-MM-DD`) no S3
- [ ] **External stage** Snowflake apontando para o S3 + storage integration
- [ ] **Snowpipe** com auto-ingest → schema `RAW` (bronze)
- [ ] PR #1: Snowflake foundation + landing

**Entregável**: `SELECT count(*) FROM raw.bacen_pix` retorna linhas carregadas
via Snowpipe. Screenshot do warehouse + resource monitor.

**Foco de aprendizado (Snowflake)**: warehouses e auto-suspend, RBAC, storage
integration, external stage, Snowpipe, resource monitor de custo.

---

## Semana 2 — dbt foundation: sources → staging → intermediate

**Meta**: camadas base do dbt verdes em `dbt build`, docs navegáveis.

- [ ] `dbt init`; `profiles.yml` para `dev` e `ci` (target no Snowflake)
- [ ] `packages.yml`: `dbt_utils`, `dbt_expectations`, `codegen`
- [ ] `sources.yml`: fontes RAW mapeadas + `freshness` (warn/error)
- [ ] Staging (`stg_*`, materializado como **view**): rename, cast, tipos
- [ ] Testes genéricos em staging: `not_null`, `unique`, `accepted_values`
- [ ] Intermediate (`int_*`, **ephemeral**): joins/enriquecimentos reusáveis
- [ ] Primeiro macro reutilizável (ex.: `cents_to_brl`, `safe_divide`)
- [ ] `dbt docs generate` + `dbt docs serve` funcionando localmente
- [ ] PR #2: dbt foundation

**Entregável**: `dbt build --target dev` verde + screenshot do lineage no dbt docs.

**Foco de aprendizado (dbt)**: estrutura de projeto (best practices), sources +
freshness, materializações (view/ephemeral), testes genéricos, packages, macros.

---

## Semana 3 — Marts Kimball (star schema)

**Meta**: star schema completo, incremental e com SCD2 nativo do dbt.

- [ ] `dim_tempo` gerada via **seed** dbt (ou `dbt_utils.date_spine`)
- [ ] `dim_instituicao` com **snapshot** dbt (SCD Type 2)
- [ ] `dim_tipo_chave`, `dim_regiao`, `dim_categoria_valor`
- [ ] `fct_transacao_pix` (grain = transação) materializado como **incremental**
- [ ] Estratégia incremental (`merge`) + `is_incremental()` documentada
- [ ] Testes de `relationships` fato↔dimensões (integridade referencial)
- [ ] **Exposure** `dashboard_pix` declarada no dbt
- [ ] Diagrama do star schema no `docs/` e README
- [ ] PR #3: Kimball star schema

**Entregável**: dbt docs com lineage fato→dims + diagrama do star schema no README.

**Foco de aprendizado (dbt)**: modelagem dimensional, seeds, snapshots (SCD2),
modelos incrementais, testes de relacionamento, exposures.

---

## Semana 4 — Qualidade, CI/CD, docs e storytelling

**Meta**: pipeline auto-defendido, docs públicos, portfólio apresentável.

- [ ] Suite de testes: `dbt_expectations` (distribuições, ranges) na staging
- [ ] Testes **singulares/customizados**: continuidade temporal (sem buracos de
      dias), conservação de massa entre camadas, `valor > 0`
- [ ] CI GitHub Actions: PR roda `dbt build --target ci` em ambiente isolado via
      **zero-copy clone** (ou schema temporário por `GITHUB_RUN_ID`)
- [ ] **Slim CI**: `dbt build --defer --state` usando o `manifest.json` de PROD
- [ ] Deploy em `main`: `dbt build --target prod` + upload do manifest para S3
- [ ] **dbt docs no GitHub Pages** (link público)
- [ ] Dashboard leve de serving: Streamlit simples OU consumo direto dos marts
- [ ] README "hero": problema, arquitetura, decisões, screenshots, métricas
- [ ] PR #4: qualidade + CI/CD + docs
- [ ] Candidatar a 5 vagas usando o projeto

**Entregável**: CI barra um PR quebrado; dbt docs público no GitHub Pages;
link do dashboard no README.

**Foco de aprendizado**: testes avançados dbt, CI/CD com dbt, zero-copy clone
(Snowflake), slim CI com defer/state, hospedagem de docs.

---

## Stretch (opcional, pós-MVP)

Itens que ficaram fora do núcleo mas viram bons projetos-satélite ou upgrades:

- **Snowflake Streams + Tasks** para CDC/incremental nativo no warehouse.
- **Snowflake Python UDF** (ex.: uma função analítica in-database).
- One Big Table (OBT) como segunda modelagem para comparar com Kimball.
- Orquestração (Airflow/Dagster) substituindo o cron/CI trigger.
- Terraform para S3 + storage integration + roles.

## Checkpoints semanais

A cada sexta-feira:
1. PR mergeado no `main`.
2. Item "Done" marcado neste roadmap.
3. Post curto de progresso (opcional, alavanca network).
