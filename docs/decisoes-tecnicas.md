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

## ADR-004 — Três modelagens em paralelo

**Contexto**: a escolha do modelo dimensional é uma decisão de arquitetura
de alto impacto. Implementar uma só não permite comparação; implementar
três sobre o mesmo dado torna os trade-offs explícitos e mensuráveis.

**Decisão**: materializar gold em 3 schemas paralelos (Kimball, DV 2.0, OBT).

**Consequências**:
- ✓ Trade-offs comparáveis com números reais
- ✓ Exercita decisão arquitetural com dados concretos
- ✗ Mais código pra manter — mitigado por reuso da camada intermediate

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
