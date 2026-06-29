"""
================================================================================
 bacen/ingest.py — A "receita completa" da ingestão Bacen
================================================================================

ESTE ARQUIVO ORQUESTRA: cliente Bacen + escrita em Parquet.

Pense neste arquivo como um "roteiro" no Excel:
    1. Abrir conexão
    2. Trazer os dados
    3. Salvar no formato certo, na pasta certa

Não tem lógica de negócio nova — só costura as outras peças.

Por que essa separação? Porque amanhã, em vez do CLI, quem vai chamar
essa função é o Airflow. E em vez do Airflow, daqui a um ano talvez
seja um botão de UI ou uma Lambda na AWS. A função `ingest_endpoint`
fica reutilizável por qualquer "disparador".

--------------------------------------------------------------------------------
 CONCEITOS QUE APARECEM AQUI
--------------------------------------------------------------------------------

1) `from __future__ import annotations`
   Isso é mágica do Python para permitir usar tipos em anotações sem ter
   problemas com versões antigas. Pode ignorar por enquanto — é boilerplate.

2) `from datetime import date`
   `date` é só a data (sem hora). `datetime` seria data+hora.
   Usamos `date` porque nossa partição é por DIA.

3) Tipos com `|` (union) — `date | None`
   Significa: "esse parâmetro pode ser um `date` OU `None`".
   `None` é o equivalente Python de NULL em SQL. Usamos como default
   pra dizer "se não passou, eu decido o que fazer".

4) Parâmetros com `*` na frente
   `def funcao(a, *, b, c)` — força `b` e `c` a serem passados pelo nome:
       funcao(a=1, b=2, c=3)   ← OK
       funcao(1, 2, 3)         ← Erro
   Boa prática quando há vários parâmetros opcionais.

5) `log.info("evento", chave=valor)` — estruturado, não texto livre
   Logs estruturados deixam fácil filtrar depois: "me mostre todas as
   ingestões do endpoint X que demoraram >30s". Com prints só dá pra
   fazer grep, o que é frágil.

================================================================================
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import structlog

from pix_observatory.bacen.client import BacenOlindaClient
from pix_observatory.config import settings
from pix_observatory.io_utils import write_records_parquet

log = structlog.get_logger(__name__)


def ingest_endpoint(
    endpoint: str,
    *,
    run_date: date | None = None,
    filter_query: str | None = None,
    order_by: str | None = None,
    max_records: int | None = None,
    output_root: Path | None = None,
    extra_params: dict[str, str] | None = None,
) -> Path:
    """Busca um endpoint do Bacen Olinda e grava o resultado como Parquet.

    Parâmetros
    ----------
    endpoint : str
        Nome do endpoint OData. Ex.: "EstoqueDeChavesPix".
    run_date : date, opcional
        Data da partição (vira a pasta dt=YYYY-MM-DD). Default: hoje.
    filter_query : str, opcional
        Expressão OData $filter. Ex.: "AnoMes ge 202401".
    order_by : str, opcional
        Expressão OData $orderby. Recomendado para paginação estável.
    max_records : int, opcional
        Para depois de N registros. Útil para smoke tests.
    output_root : Path, opcional
        Sobrescreve a pasta raiz dos arquivos brutos. Default: settings.raw_root.

    Retorno
    -------
    Path
        Caminho do arquivo Parquet gerado.
    """
    # Defaults sensatos. "or" em Python: se o primeiro for None/0/"", usa o
    # segundo. Truque conveniente para preencher faltantes.
    run_date = run_date or date.today()
    output_root = output_root or settings.raw_root

    # Log de início. Em produção, este log é o que aparece no painel quando
    # o pipeline começa. Inclua todo o contexto útil para diagnosticar.
    log.info(
        "ingest_endpoint.start",
        endpoint=endpoint,
        run_date=run_date.isoformat(),
        filter_query=filter_query,
        max_records=max_records,
    )

    # ------------------------------------------------------------------
    # PASSO 1 — Abrir cliente, baixar tudo de uma vez para a memória.
    # ------------------------------------------------------------------
    # Note o `with`: garante que `client.close()` é chamado mesmo se
    # algo der errado lá dentro. Vimos esse padrão em client.py.
    #
    # `list(...)` ao redor de `client.iter_records(...)` materializa o
    # gerador numa lista em memória. Para volumes pequenos (até alguns
    # milhões de registros pequenos) isso é OK. Para volumes maiores,
    # trocamos esse list() por escrita incremental (futuramente, via AWS Glue).
    with BacenOlindaClient() as client:
        records = list(
            client.iter_records(
                endpoint,
                filter_query=filter_query,
                order_by=order_by,
                max_records=max_records,
                extra_params=extra_params,
            )
        )

    # ------------------------------------------------------------------
    # PASSO 2 — Salvar a lista de registros em Parquet, particionado.
    # ------------------------------------------------------------------
    # `source=f"bacen/{endpoint}"` cria a pasta organizadora dentro do
    # data lake. Ex.: data/raw/bacen/EstoqueDeChavesPix/dt=2026-06-08/
    # Para a partição em disco usamos só o nome do recurso, sem a sintaxe
    # de função do Olinda. Ex.: "ChavesPix(Data=@Data)" → "ChavesPix".
    endpoint_dirname = endpoint.split("(")[0]

    output_file = write_records_parquet(
        records,
        root=output_root,
        source=f"bacen/{endpoint_dirname}",
        dt=run_date,
    )

    log.info(
        "ingest_endpoint.done",
        endpoint=endpoint,
        rows=len(records),
        path=str(output_file),
    )

    # Retorna o caminho do arquivo para quem chamou poder usar (ex: testar,
    # passar adiante na DAG do Airflow, etc.).
    return output_file
