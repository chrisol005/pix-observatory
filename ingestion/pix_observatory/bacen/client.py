"""
================================================================================
 bacen/client.py — O "garçom" que vai ao balcão do Bacen
================================================================================

ESTE ARQUIVO ENCAPSULA TUDO QUE SABE SOBRE A API DO BACEN.

A ideia: o resto do projeto não precisa saber se é OData, se tem paginação,
quais headers HTTP, etc. Basta ele instanciar este "cliente" e pedir
"me dá os registros do endpoint X". É como pedir um cafezinho no balcão:
você não precisa saber como funciona a máquina, só pede o café.

--------------------------------------------------------------------------------
 CONCEITOS DE PYTHON QUE APARECEM AQUI E PODEM ESTRANHAR
--------------------------------------------------------------------------------

1) CLASSE (`class BacenOlindaClient:`)
   Uma classe é um "molde" para criar objetos que carregam ESTADO (dados
   internos) + COMPORTAMENTO (funções).
   Você provavelmente nunca criou classes em scripts de pandas, mas usa
   elas o tempo todo: `df.head()` — o `df` é um objeto da classe DataFrame,
   e `.head()` é um método dela.

   Quando faz `client = BacenOlindaClient()`, você instancia um objeto.
   Esse objeto tem dentro dele: a URL do Bacen, a sessão HTTP aberta, etc.
   E tem métodos: `client.iter_records(...)`, `client.close()`.

2) `__init__` (o "construtor")
   É o método chamado AUTOMATICAMENTE quando você cria o objeto.
   `BacenOlindaClient(base_url=..., timeout=...)` → `__init__` recebe esses
   parâmetros e arruma o objeto para uso.

3) `self`
   Toda função dentro de uma classe tem `self` como primeiro parâmetro.
   `self` é o próprio objeto. `self.base_url = base_url` significa "guarde
   este valor dentro do objeto, para usar depois em outras funções".
   Em outras linguagens chama-se `this`.

4) `__enter__` e `__exit__` (CONTEXT MANAGER)
   Esses dois métodos especiais transformam a classe em algo que pode ser
   usado com `with`:

       with BacenOlindaClient() as cliente:
           ...

   Quando você entra no `with`, Python chama `__enter__()`.
   Quando você sai (mesmo se der erro!), Python chama `__exit__()`.
   Isso garante que a conexão HTTP sempre seja fechada, evitando vazamento
   de recursos. É o mesmo padrão de `with open(...) as f:` para arquivos.

5) `Iterator[dict]` e `yield` (GENERATOR)
   Veja a função `iter_records`. Ela não dá `return` no fim — ela usa `yield`
   no meio. Isso transforma a função num GERADOR.

   Diferença prática:
     `return lista` — devolve a lista inteira de uma vez (consome memória).
     `yield item`   — entrega item por item; o chamador "puxa" um de cada vez.

   Por que isso importa? Se o Bacen tiver 50 milhões de registros, NÃO
   queremos carregar tudo na memória. Com yield, processamos um por um.
   É exatamente o conceito de "cursor" do SQL.

6) `httpx.Client`
   `httpx` é uma biblioteca para fazer requisições HTTP (como o `requests`,
   mas mais moderna). `httpx.Client()` mantém uma conexão TCP aberta
   reaproveitada entre as requisições — bem mais rápido que abrir e fechar
   a cada chamada.

================================================================================
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import structlog

from pix_observatory.config import settings

# Logger estruturado. Em vez de `print("baixou X")`, fazemos `log.info("baixou", x=X)`.
# Isso permite, no futuro, mandar os logs para CloudWatch/Datadog em formato JSON,
# filtrar por campo, etc. Para o dia a dia, comporta-se como print().
log = structlog.get_logger(__name__)


class BacenOlindaClient:
    """Cliente paginado para o serviço OData do Bacen Olinda (PIX).

    Como usar (forma recomendada, com `with`):
        with BacenOlindaClient() as cliente:
            for registro in cliente.iter_records("EstoqueDeChavesPix"):
                print(registro)

    O `with` garante que a conexão é fechada mesmo se der erro.
    """

    # Constante de classe — tamanho padrão de cada página de paginação OData.
    # 1000 é um meio-termo: grande o suficiente pra ter poucas requisições;
    # pequeno o suficiente pra não estourar memória ou timeout.
    DEFAULT_PAGE_SIZE = 1000

    # ------------------------------------------------------------------
    # Construtor: prepara o cliente para uso.
    # Note os "*" entre `base_url` e os outros parâmetros — isso força
    # quem chama a usar nome explícito para timeout e page_size:
    #     BacenOlindaClient("https://...", timeout=60)  ← OK
    #     BacenOlindaClient("https://...", 60)          ← Erro!
    # Boa prática para parâmetros opcionais não-óbvios.
    # ------------------------------------------------------------------
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 30.0,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        # Se quem chamou não passou base_url, usamos a do config.py.
        # O `.rstrip("/")` remove uma barra final, se houver, pra evitar
        # URLs com "//" no meio.
        self.base_url = (base_url or settings.bacen_api_base).rstrip("/")
        self.page_size = page_size

        # Cria a sessão HTTP. `httpx.Client` reaproveita a conexão entre
        # múltiplas chamadas, o que é bem mais rápido.
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            # Headers padrão:
            # - Accept: queremos JSON (Olinda também serve XML/CSV/HTML)
            # - User-Agent: alguns servidores rejeitam requisições sem isso
            headers={
                "Accept": "application/json",
                "User-Agent": "pix-observatory/0.1 (https://github.com/.../pix-observatory)",
            },
        )

    # ------------------------------------------------------------------
    # Métodos especiais que habilitam o uso com `with`.
    # ------------------------------------------------------------------
    def __enter__(self) -> BacenOlindaClient:
        """Chamado ao entrar no bloco `with`."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Chamado ao sair do bloco `with`, mesmo se houve exceção."""
        self.close()

    def close(self) -> None:
        """Fecha a sessão HTTP. Boa cidadania de rede."""
        self._client.close()

    # ------------------------------------------------------------------
    # O método público principal: itera registros do endpoint, paginando.
    # ------------------------------------------------------------------
    def iter_records(
        self,
        endpoint: str,
        *,
        filter_query: str | None = None,
        select: str | None = None,
        order_by: str | None = None,
        max_records: int | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Entrega registros de um endpoint OData, um a um.

        O tipo de retorno `Iterator[dict[str, Any]]` significa:
        "uma sequência preguiçosa onde cada item é um dicionário Python
        com chaves string e valores de qualquer tipo".

        Use em loop:
            for registro in cliente.iter_records("ChavesPix(Data=@Data)",
                                                 extra_params={"@Data": "'2026-05-31'"}):
                processar(registro)

        Alguns endpoints Olinda exigem parâmetros nomeados (sintaxe
        `Recurso(Param=@Param)?@Param='valor'`). Use `extra_params` para
        passar esses pares.
        """
        # Garante que o endpoint começa com "/" (compatível com httpx.base_url).
        path = f"/{endpoint.lstrip('/')}"

        # Olinda quirk #1: o servidor não decodifica corretamente $, @ e ' quando
        # vêm percent-encoded. Por isso montamos a query string manualmente
        # com os caracteres literais, em vez de passar dict para o httpx
        # (que codificaria tudo).
        def _build_query(p: dict[str, str | int]) -> str:
            return "&".join(f"{k}={v}" for k, v in p.items())

        # Olinda quirk #2: a ordem dos parâmetros importa. Os "@" (function args
        # que bindam a resource) devem vir antes dos "$" (OData query options).
        # Olinda quirk #3: incluir "$skip=0" na primeira página causa erro 500.
        # Só incluímos $skip quando > 0 (a partir da segunda página).
        # Construímos um dict base (sem $skip) e adicionamos $skip por página.
        base_params: dict[str, str | int] = {}

        # 1. Olinda function args (@) primeiro
        if extra_params:
            for k, v in extra_params.items():
                if k.startswith("@"):
                    base_params[k] = v

        # 2. OData query options ($)
        base_params["$top"] = self.page_size
        base_params["$format"] = "json"
        if filter_query:
            base_params["$filter"] = filter_query
        if select:
            base_params["$select"] = select
        if order_by:
            base_params["$orderby"] = order_by

        # 3. Outros extras (raros)
        if extra_params:
            for k, v in extra_params.items():
                if not k.startswith("@"):
                    base_params[k] = v

        # Contador para respeitar o limite max_records.
        yielded = 0
        skip = 0

        # LAÇO DE PAGINAÇÃO.
        # Quebra quando:
        #   1) A página voltou vazia (acabaram os dados)
        #   2) A página voltou com menos que page_size registros (última página)
        #   3) Atingimos max_records (se foi passado)
        while True:
            # Monta os params desta página: base + $skip se já não for o primeiro.
            current_params = dict(base_params)
            if skip > 0:
                current_params["$skip"] = skip

            # Loga o que estamos fazendo — útil para debugar timeout/lentidão.
            log.info(
                "bacen.fetch_page",
                endpoint=endpoint,
                skip=skip,
                top=self.page_size,
            )

            # FAZ A REQUISIÇÃO HTTP.
            # Em vez de passar `params=dict`, anexamos a query string já pronta
            # ao path. Isso preserva $, @, ' literais como o Olinda exige.
            full_path = f"{path}?{_build_query(current_params)}"
            response = self._client.get(full_path)

            # raise_for_status() levanta exceção se o status HTTP for de erro
            # (400, 500, etc.). Antes de levantar, logamos o corpo da resposta
            # — APIs como a do Bacen colocam a mensagem útil ali.
            if response.is_error:
                log.error(
                    "bacen.http_error",
                    status=response.status_code,
                    url=str(response.url),
                    body=response.text[:500],
                )
            response.raise_for_status()

            # Converte o JSON da resposta em dicionário Python.
            payload = response.json()

            # OData empacota os registros num campo chamado "value".
            # Se não existir, devolvemos [] como default.
            records = payload.get("value", [])

            # Se a página veio vazia, terminamos.
            if not records:
                break

            # ENTREGA REGISTROS, UM A UM, USANDO yield.
            # Quem chamar essa função recebe cada registro na hora dele aparecer,
            # sem esperar todas as páginas terminarem. É como um cursor SQL.
            for record in records:
                yield record
                yielded += 1
                # Se o usuário pediu max_records, paramos no limite.
                if max_records is not None and yielded >= max_records:
                    log.info("bacen.max_records_reached", yielded=yielded)
                    return  # encerra o gerador

            # Se vieram menos registros que pedimos, esta é a última página.
            # Não pedimos mais uma rodada — economiza uma requisição.
            if len(records) < self.page_size:
                break

            # Senão, avança o "ponteiro" para a próxima página.
            skip += self.page_size
