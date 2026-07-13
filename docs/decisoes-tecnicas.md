# ADRs — Decisões técnicas

Arquivo de Architecture Decision Records. Formato leve: contexto,
decisão, alternativas, consequências.

---

## ADR-001 — Cloud: AWS + Snowflake

**Contexto**: a ingestão e o processamento se beneficiam do ecossistema
AWS (Glue, S3, Athena), e o projeto precisa de um data warehouse cloud
robusto e amplamente adotado para a camada analítica.

**Decisão**: AWS para ingestão e processamento; Snowflake como DW.

**Alternativas consideradas**:
- *GCP + BigQuery*: stack cloud adicional, custo de ramp-up alto.
- *Multi-cloud (AWS + Snowflake + GCP serving)*: cobre mais ferramentas,
  mas aumenta muito a complexidade operacional.

**Consequências**:
- ✓ Aproveita o ferramental maduro da AWS para ingestão
- ✓ Snowflake é um DW cloud consolidado e bem documentado
- ✗ Não cobre GCP/BigQuery (pode virar projeto-satélite depois)

---

## ADR-002 — Streaming: simulado via micro-batch

**Contexto**: implementar streaming real com Kafka + Flink + processamento
exactly-once adiciona complexidade operacional significativa, desproporcional
ao escopo atual do projeto.

**Decisão**: simular streaming via micro-batch (Airflow DAG a cada 15 min).
Documentar abertamente no README como simulação, não streaming real.

**Alternativas**:
- *Kafka real*: alto custo de operação e manutenção.
- *AWS Kinesis*: custo mais alto, sem ganho proporcional para o escopo.

**Consequências**:
- ✓ Mantém o escopo gerenciável
- ✓ Honestidade técnica: descrito como simulação, sem exageros
- ✗ Não exercita Kafka — projeto-satélite futuro recomendado

---

## ADR-003 — Synthetic data generator

**Contexto**: dados públicos do Bacen são agregados (não há transações
individuais públicas). Para demonstrar engenharia de dados em escala,
precisa de granularidade transacional.

**Decisão**: gerar dados sintéticos calibrados pelas distribuições reais
do Bacen (Faker + numpy, determinístico via seed).

**Alternativas**:
- *Só dados agregados*: limita drasticamente o que dá pra modelar.
- *Buscar leak/scrape de dados reais*: legalmente arriscado, eticamente
  errado.

**Consequências**:
- ✓ Permite modelagem em todos os 3 paradigmas
- ✓ Reproducible para qualquer pessoa que clone o repo
- ✗ Análises não refletem fenômenos reais — declarar explicitamente no
  README e em todos os dashboards.

---

## ADR-004 — Três modelagens em paralelo — REVISADO (ver ADR-007)

**Contexto original**: a escolha do modelo dimensional é uma decisão de
arquitetura de alto impacto. Implementar uma só não permite comparação;
implementar três sobre o mesmo dado torna os trade-offs explícitos.

**Decisão original**: materializar gold em 3 schemas paralelos (Kimball, DV, OBT).

**Revisão (2026-07-13)**: substituída pela ADR-007. Escopo reduzido a **uma**
modelagem — Kimball (star schema) — feita com profundidade (SCD2 via snapshot,
fato incremental). OBT vira *stretch* opcional; Data Vault, projeto-satélite.

**Consequências**:
- ✓ Profundidade > amplitude: uma modelagem bem testada demonstra mais domínio
- ✓ Cabe no prazo de 4 semanas com foco em dbt
- ✗ Perde-se o benchmark comparativo — compensado por saber narrar os trade-offs

---

## ADR-005 — Terraform como stretch

**Contexto**: IaC agrega valor à reprodutibilidade da infra, mas não é
parte central do pipeline de dados em si.

**Decisão**: incluir Terraform apenas como item opcional, ao final.
Bootstrap manual da infra é aceitável nesta fase.

**Consequências**:
- ✓ Foco primeiro nas camadas centrais do pipeline
- ✗ Pode ficar de fora — adicionar a um próximo projeto se necessário

---

## ADR-006 — Astro CLI local em vez de MWAA

**Contexto**: MWAA custa ~US$20-30/mês. Astro CLI roda Airflow em Docker
localmente sem custo.

**Decisão**: desenvolvimento em Astro CLI. MWAA opcional ao final, como
exercício de deploy gerenciado.

**Consequências**:
- ✓ Reduz custo
- ✓ Aprende Airflow puro
- ✗ "Production-like" apenas na fase com MWAA — declarar no README

> ⚠️ **Superado pela ADR-007**: Airflow saiu do escopo central. Orquestração
> fica como *stretch*; o disparo do dbt no MVP é via CI / cron simples.

---

## ADR-007 — Refoco de escopo: dbt + Snowflake (2026-07-13)

**Contexto**: o projeto original cobria muitas ferramentas em amplitude
(Glue/PySpark, Airflow, ML com Prophet/MLflow, Metabase, Terraform, três
modelagens dimensionais). As vagas-alvo de Data Engineer / Analytics Engineer
pedem, com frequência muito maior, **dbt** e **Snowflake**. Amplitude excessiva
diluía a profundidade justamente nas ferramentas de maior retorno.

**Decisão**: refocar o projeto em duas ferramentas — **dbt (prioridade 1)** e
**Snowflake (prioridade 2)** — e comprimir o prazo para ~4 semanas. A ingestão
Python já construída é reaproveitada como fonte.

**Sai do núcleo** (vira *stretch* ou projeto-satélite):
- AWS Glue / PySpark — Snowpipe + dbt cobrem o volume do projeto.
- Airflow — disparo via CI/cron no MVP (ADR-006 superado).
- ML (Prophet/MLflow) — fora do foco das duas ferramentas.
- Metabase — serving via dbt docs + Streamlit leve.
- Terraform — bootstrap manual aceitável (ADR-005 reforçado).
- Data Vault 2.0 e OBT — só Kimball no núcleo (ADR-004 revisado).

**Entra com profundidade**:
- dbt: sources+freshness, staging/intermediate/marts, snapshots (SCD2), seeds,
  incremental, testes genéricos + customizados, macros, packages, exposures,
  docs no GitHub Pages, CI com slim CI (defer/state).
- Snowflake: warehouses + auto-suspend, RBAC, storage integration, external
  stage, Snowpipe, resource monitor, zero-copy clone para CI, Time Travel.

**Consequências**:
- ✓ Profundidade demonstrável nas duas ferramentas mais pedidas
- ✓ Menor custo (~US$15/mês) e prazo mais curto (4 semanas)
- ✓ Aproveita 100% da ingestão já codada
- ✗ Menos "amplitude" visível — mitigado listando os *stretch* como roadmap futuro
- ✗ Não exercita orquestração/ML/Spark neste projeto — declarar no README
