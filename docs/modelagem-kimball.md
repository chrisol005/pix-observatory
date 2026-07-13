# Modelagem dimensional — Kimball (Star Schema)

> Escopo enxuto: **uma** modelagem, feita com profundidade. O star schema
> Kimball é o padrão dominante em BI corporativo e o que aparece com mais
> frequência nas descrições de vaga de Data Engineer / Analytics Engineer.
> Data Vault 2.0 e OBT saíram do escopo central (ver ADR-004 revisado e ADR-007
> em `decisoes-tecnicas.md`); OBT fica como *stretch* opcional para comparação.

## A fonte

Tabela de fato lógica: `transacao_pix`. Grain: **uma transação individual**.

Atributos relevantes:
- Identificador da transação
- Timestamp
- Instituição pagadora / recebedora
- Tipo de chave PIX (CPF, CNPJ, email, telefone, aleatória)
- Valor
- Estado (UF) da instituição pagadora / recebedora
- Categoria de valor (faixa)

## Star schema

```
                ┌──────────────┐
                │  dim_tempo   │  (seed dbt / date_spine)
                └──────┬───────┘
                       │
┌────────────────┐     │      ┌────────────────┐
│ dim_instituicao│     ▼      │ dim_tipo_chave │
│    (SCD2 via   ├──► fct_ ◄──┤                │
│    snapshot)   │  transacao └────────────────┘
└────────────────┘   _pix
                       ▲
              ┌────────┴─────────┐
              │                  │
      ┌───────────────┐  ┌──────────────────┐
      │  dim_regiao   │  │dim_categoria_valor│
      └───────────────┘  └──────────────────┘
```

### Fato — `fct_transacao_pix`

- **Grain**: transação individual.
- **Materialização**: `incremental` (estratégia `merge`, com `is_incremental()`).
- **Chaves estrangeiras**: para todas as dimensões, testadas com `relationships`.
- **Medidas**: valor da transação, contadores.

### Dimensões

| Dimensão | Como é construída | Observação |
|---|---|---|
| `dim_tempo` | **seed** dbt (ou `dbt_utils.date_spine`) | calendário completo, dia/mês/trimestre/ano, flags de fim de semana |
| `dim_instituicao` | **snapshot** dbt (SCD Type 2) | versiona mudanças de atributos da instituição no tempo |
| `dim_tipo_chave` | seed / staging | CPF, CNPJ, email, telefone, aleatória |
| `dim_regiao` | staging + enriquecimento | UF → região |
| `dim_categoria_valor` | seed / lógica no intermediate | faixas de valor (banding) |

## Por que Kimball (e não Data Vault / OBT) no núcleo

- **Demanda de mercado**: star schema é o vocabulário comum de BI/analytics
  engineering — melhor retorno por hora de estudo para as vagas-alvo.
- **Profundidade > amplitude**: uma modelagem bem testada, com SCD2 real via
  snapshot e fato incremental, demonstra mais competência do que três modelagens
  superficiais.
- **Menos código para manter** dentro de um prazo de 4 semanas.

**Quando Kimball é bom**: BI corporativo, queries previsíveis, baixa curva para
analistas. **Quando dói**: evolução de schema (rebuild de dims), múltiplas fontes
com granularidades diferentes — cenários onde Data Vault brilharia (documentado
abaixo como conhecimento, não como implementação).

## Contexto: as alternativas (só para narrativa em entrevista)

Vale saber explicar os trade-offs mesmo sem implementar:

- **Data Vault 2.0** (hubs/links/satellites): auditoria e rastreabilidade
  nativas, ótimo para ambientes regulatórios e muitas fontes voláteis; custo:
  queries de BI lentas (muitos joins) e curva alta. Bom candidato a
  projeto-satélite dado o histórico em serviços financeiros.
- **One Big Table (OBT)**: tabela única denormalizada; excelente para feature
  stores de ML e ferramentas que não fazem join bem; custo: storage redundante
  e reescrita de histórico em mudanças descritivas. É o *stretch* natural aqui —
  materializar `obt_transacao_pix` a partir do mesmo intermediate e comparar
  com o star schema.

## Testes de modelagem (dbt)

- `unique` + `not_null` nas surrogate keys das dimensões.
- `relationships` de cada FK do fato para a respectiva dimensão.
- `accepted_values` em `dim_tipo_chave`, `dim_regiao`.
- Customizados: continuidade temporal (sem dias faltando em `dim_tempo` vs fato),
  conservação de massa (soma de valores bronze = soma no fato), `valor > 0`.

## Referências

- Kimball, *The Data Warehouse Toolkit* (3ª ed.)
- dbt: [How we structure our dbt projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- dbt: [Snapshots (SCD2)](https://docs.getdbt.com/docs/build/snapshots)
- dbt: [Incremental models](https://docs.getdbt.com/docs/build/incremental-models)
