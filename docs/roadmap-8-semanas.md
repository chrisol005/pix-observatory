# Roadmap detalhado — 8 semanas

> Cada semana tem entregável verificável e PR público no GitHub.

## Semana 1 — Fundação

**Meta**: repo público vivo + primeiro dado bruto no S3.

- [ ] Criar repo `pix-observatory` no GitHub (público, MIT)
- [ ] Copiar este scaffold; primeiro push
- [ ] Setup `uv` ou `poetry`; `pre-commit install`
- [ ] CI verde (ruff, mypy, pytest com testes-stub)
- [ ] Bucket S3 criado (manual ou Terraform); credenciais via `.env`
- [ ] Cliente Bacen v1: lista endpoints, parse OData, grava 1 dia em S3
- [ ] Gerador sintético v1: 10k transações/dia em Parquet local
- [ ] PR #1: foundation + CI

**Entregável**: `aws s3 ls s3://pix-observatory-raw/bacen/` mostra dados.

## Semana 2 — Snowflake + dbt foundations

**Meta**: silver mínima passando em `dbt build`.

- [ ] Conta Snowflake trial (region us-east-1)
- [ ] Criar databases DEV/CI/PROD; warehouse XS; RBAC básico
- [ ] Snowpipe + Stage externo apontando para S3 processed
- [ ] `dbt init`; configurar `profiles.yml`
- [ ] `sources.yml` com 2-3 fontes mapeadas + freshness
- [ ] Primeiros models de staging com `not_null`, `unique`
- [ ] `dbt docs generate` rodando localmente
- [ ] PR #2: Snowflake + dbt foundations

**Entregável**: `dbt build --target dev` verde + screenshot dos docs.

## Semana 3 — Airflow + Glue

**Meta**: pipeline rodando sozinho diariamente.

- [ ] Astro CLI; primeira DAG `ingest_bacen` local
- [ ] Adicionar `generate_synthetic` e `transform_dbt`
- [ ] Sensor S3 + branching baseado em volume
- [ ] Backfill semanal funcional
- [ ] AWS Glue Job em PySpark para backfill histórico (milhões de linhas)
- [ ] Documentar comparação custo Glue vs Snowpipe
- [ ] PR #3: orquestração

**Entregável**: 3 dias seguidos de execução automática sem intervenção.

## Semana 4 — Modelagem Kimball

**Meta**: star schema completo e documentado.

- [ ] `fct_transacao_pix` (grain de transação)
- [ ] `dim_tempo` (gerada via seed dbt)
- [ ] `dim_instituicao` com snapshot SCD Type 2
- [ ] `dim_tipo_chave`, `dim_regiao`, `dim_categoria_valor`
- [ ] dbt tests + diagrama no docs
- [ ] Exposure `streamlit_dashboard` declarada
- [ ] PR #4: Kimball

**Entregável**: dbt docs com lineage + diagrama do star schema no README.

## Semana 5 — Modelagem Data Vault + OBT

**Meta**: três modelos coexistindo, benchmark inicial.

- [ ] Hubs: `hub_instituicao`, `hub_chave`
- [ ] Links: `link_transacao`
- [ ] Satellites: `sat_hub_instituicao`, `sat_hub_chave`, `sat_link_transacao`
- [ ] OBT: `obt_transacao_pix_enriquecida` (particionada por mês)
- [ ] Suite de queries de benchmark (top-10 instituições, agg mensal, etc.)
- [ ] Tabela comparativa em `modelagem-comparativa.md` preenchida
- [ ] PR #5: três modelagens

**Entregável**: documento comparativo com números reais.

## Semana 6 — Qualidade + CI/CD completo

**Meta**: pipeline auto-defendido.

- [ ] Great Expectations: suíte na bronze (schema, distribuições, freshness)
- [ ] Tests customizados dbt: continuidade temporal, conservação de massa
- [ ] CI: PR roda `dbt build --target ci` contra schema temporário
- [ ] Slim CI: `--defer --state` com manifest de PROD
- [ ] Deploy em main: upload manifest para S3
- [ ] Slack webhook para falhas
- [ ] PR #6: qualidade + CI/CD

**Entregável**: PR forçado a falhar, alerta chega no Slack.

## Semana 7 — ML + serving

**Meta**: previsão útil rodando em produção.

- [ ] Prophet: forecast diário de volume por instituição (top 10)
- [ ] MLflow tracking; experiments registrados
- [ ] Snowflake Python UDF servindo o modelo
- [ ] dbt model `fct_forecast_volume` consumindo a UDF
- [ ] Streamlit app: 4 telas (overview, ranking, forecast, qualidade)
- [ ] Deploy no Streamlit Cloud
- [ ] Metabase Docker com 3 dashboards salvos
- [ ] PR #7: ML + serving

**Entregável**: link público do Streamlit + screenshots no README.

## Semana 8 — Polimento + storytelling

**Meta**: portfólio apresentável para entrevista.

- [ ] Diagrama Excalidraw da arquitetura (`docs/img/arquitetura.png`)
- [ ] README "hero": problema, decisões, métricas, screenshots
- [ ] ADRs em `docs/decisoes-tecnicas.md`
- [ ] Vídeo Loom de 5 min apresentando
- [ ] Stretch: Terraform para S3 + IAM + Secrets Manager
- [ ] Stretch: dbt docs hospedado em GitHub Pages
- [ ] PR #8: polimento

**Entregável**: repo apresentável + candidatar a 5 vagas usando o projeto.

## Checkpoints semanais

A cada sexta-feira:
1. PR mergeado no main
2. Item "Done" no `roadmap-8-semanas.md` (este arquivo)
3. Tweet/post de progresso (opcional, mas alavanca network)
