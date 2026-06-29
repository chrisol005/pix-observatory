# Modelagem comparativa: Kimball vs Data Vault 2.0 vs OBT

> Os mesmos dados de transações PIX são materializados em três paradigmas
> paralelos. Este documento registra o desenho de cada um, a motivação,
> e — ao fim do projeto — os benchmarks medidos.

## Por que três modelagens?

A escolha do modelo dimensional é uma das decisões de arquitetura mais
importantes — e mais debatidas — em engenharia de dados. Implementar e
comparar três abordagens sobre o mesmo dado torna o trade-off explícito e
mensurável, em vez de uma escolha tomada por hábito.

## A fonte

Tabela de fato lógica: `transacao_pix`

Grain: uma transação individual.

Atributos relevantes:
- Identificador da transação
- Timestamp
- Instituição pagadora / recebedora
- Tipo de chave PIX (CPF, CNPJ, email, telefone, aleatória)
- Valor
- Estado da instituição pagadora / recebedora
- Categoria de valor (faixa)

## Modelo 1 — Kimball (Star Schema)

Schema: `marts.kimball.*`

```
                ┌──────────────┐
                │  dim_tempo   │
                └──────┬───────┘
                       │
┌────────────┐         │         ┌────────────────┐
│dim_         │         ▼         │dim_instituicao │
│instituicao  ├──► fct_transacao  │  (SCD2)         │
│  (SCD2)     │   _pix            └────────────────┘
└────────────┘         ▲
                       │
                ┌──────┴────────┐
                │dim_tipo_chave │
                └───────────────┘

           ... dim_regiao, dim_categoria_valor
```

- **Fato**: `fct_transacao_pix` (grain de transação individual)
- **Dimensões**: tempo, instituição (SCD2), tipo_chave, região, categoria_valor
- **Materialização**: `table`
- **Atualização**: incremental por dia

**Quando é bom**: BI corporativo, queries previsíveis, baixa curva de
aprendizado para analistas.

**Quando dói**: evolução de schema (precisa rebuildar dims), múltiplas
fontes com diferentes granularidades.

## Modelo 2 — Data Vault 2.0

Schema: `marts.data_vault.*`

```
hub_instituicao ──┐
                  ├─► link_transacao ──► sat_link_transacao
hub_chave ────────┘                       (valor, ts, atributos)

sat_hub_instituicao  ← atributos descritivos da instituição, SCD2 nativo
sat_hub_chave        ← atributos descritivos da chave
```

- **Hubs**: chaves de negócio + hash key + load date + record source
- **Links**: relacionamentos (transação = link entre instituições + chave)
- **Satellites**: atributos descritivos versionados (auditoria nativa)
- **Materialização**: `incremental` com `append_new_columns`

**Quando é bom**: ambientes regulatórios (auditoria nativa), múltiplas
fontes voláteis, necessidade de rastreabilidade total.

**Quando dói**: queries de BI lentas (muitos joins), curva de aprendizado
alta, storage mais caro.

## Modelo 3 — One Big Table (OBT)

Schema: `marts.obt.*`

Tabela única `obt_transacao_pix_enriquecida` com todos os atributos
denormalizados (instituição expandida, tempo expandido, geo expandida).

- **Materialização**: `table` particionada por mês
- **Atualização**: full refresh semanal + append diário

**Quando é bom**: ML feature stores, exploração ad-hoc, ferramentas que
não fazem join bem (alguns no-code BI).

**Quando dói**: storage (muito redundante), atualizações em campos
descritivos (precisa reescrever histórico).

## Comparação (a preencher com medições reais)

| Critério | Kimball | Data Vault | OBT |
|---|---|---|---|
| Tempo médio: query top-10 ranking instituições | _TBD_ | _TBD_ | _TBD_ |
| Tempo médio: agregação por mês × região | _TBD_ | _TBD_ | _TBD_ |
| Storage total (GB) | _TBD_ | _TBD_ | _TBD_ |
| Custo Snowflake compute em 1 build completo | _TBD_ | _TBD_ | _TBD_ |
| Linhas de SQL dbt | _TBD_ | _TBD_ | _TBD_ |
| Tempo para adicionar nova fonte (estimado) | _TBD_ | _TBD_ | _TBD_ |
| Tempo para mudar SCD em instituição | _TBD_ | _TBD_ | _TBD_ |
| Facilidade para analista escrever SQL | Alta | Baixa | Muito alta |

## Recomendação

Será documentada ao final, com base nos números reais. Hipótese inicial:
**Kimball + OBT em paralelo** atende 80% dos casos (BI + ML) sem o custo
operacional do Data Vault. DV se justifica quando há requisito explícito
de auditoria ou ambiente com múltiplas fontes evoluindo independentemente.

## Referências

- Kimball, *The Data Warehouse Toolkit* (3ª ed.)
- Linstedt & Olschimke, *Building a Scalable Data Warehouse with Data Vault 2.0*
- AWS Well-Architected — Analytics Lens
- dbt: [How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
