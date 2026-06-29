"""
================================================================================
 cli.py — O "controle remoto" do projeto
================================================================================

ESTE ARQUIVO TRANSFORMA O SEU PROJETO EM UM COMANDO DE TERMINAL.

Sem ele, para rodar a ingestão você teria que abrir o Python no modo
interativo, importar funções, etc. — assim como faz em notebook Jupyter.

Com este arquivo, depois de instalar o pacote, basta digitar no terminal:

    pixo bacen ingest EstoqueDeChavesPix --max-records 10

E o seu computador entende como: "execute aquela função Python lá dentro,
com esses parâmetros".

É a mesma ideia de comandos que você já usa todo dia:
    git commit -m "mensagem"
    aws s3 cp arquivo.csv s3://bucket/
    docker-compose up -d

Todos esses são "CLIs" (Command Line Interfaces) construídos por
desenvolvedores. Você está construindo um CLI agora, igualzinho.

--------------------------------------------------------------------------------
 PEÇAS NOVAS QUE APARECEM AQUI E O QUE CADA UMA SIGNIFICA
--------------------------------------------------------------------------------

1) `typer` — é uma biblioteca Python que torna fácil criar CLIs.
   Sem typer, você teria que escrever ~50 linhas para parsear argumentos,
   gerar mensagens de --help, validar tipos, etc.
   Typer faz tudo isso lendo a "assinatura" das suas funções.

2) `app = typer.Typer(...)` — cria o "objeto controlador" do seu CLI.
   Pense como criar uma planilha vazia onde depois você vai colocar abas.

3) `bacen_app = typer.Typer(...)` — cria um "sub-comando".
   É o que permite o comando ficar bonito assim: `pixo bacen ingest`
   em vez de `pixo bacen_ingest`. Cada palavra é um nível na árvore.

4) `app.add_typer(bacen_app, name="bacen")` — pendura o sub-comando
   debaixo do principal. Análogo a "esta aba se chama 'bacen'".

5) `@bacen_app.command("ingest")` — esse `@` em cima de uma função é
   um DECORATOR. Em português grosseiro: "antes da minha função
   nascer, faça uma mágica nela". Aqui, ele REGISTRA a função
   como sendo um comando chamado "ingest" debaixo do "bacen".

   Decorator não é um conceito de Python básico — é um padrão avançado.
   Por enquanto, leia "@bacen_app.command('ingest')" como uma etiqueta
   colada na função dizendo: "esta função é o comando ingest".

6) `typer.Argument(...)` vs `typer.Option(...)`:
   - Argument: parâmetro POSICIONAL e OBRIGATÓRIO.
     `pixo bacen ingest EstoqueDeChavesPix` — o "EstoqueDeChavesPix"
     é o argumento, não tem flag na frente.
   - Option: parâmetro OPCIONAL com flag.
     `--max-records 10` — começa com `--`, tem nome, pode faltar.

   Os dois servem para typer saber o tipo, a descrição (que aparece
   no --help) e o valor padrão.

7) `if __name__ == "__main__":` no final — é uma convenção Python para
   dizer "se este arquivo for executado diretamente, rode `app()`".
   Você provavelmente já viu isso em scripts. Não precisa entender
   profundamente agora, só saber que é a "ignição" do CLI.

--------------------------------------------------------------------------------
 ONDE O NOME "pixo" É REGISTRADO
--------------------------------------------------------------------------------

O nome "pixo" não aparece neste arquivo — ele está no pyproject.toml:

    [project.scripts]
    pixo = "pix_observatory.cli:app"

Isso diz ao instalador (uv/pip): "quando alguém digitar `pixo` no
terminal, execute o objeto `app` do módulo `pix_observatory.cli`".

Por isso, depois de `uv pip install -e ".[dev]"`, o `pixo` vira um
comando real no seu sistema.
================================================================================
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import structlog
import typer

from pix_observatory.bacen.ingest import ingest_endpoint

# -----------------------------------------------------------------------------
# Criando o CLI principal e o sub-CLI "bacen".
# -----------------------------------------------------------------------------
# `app` é o controlador raiz. Quando você digita só `pixo`, ele é quem responde.
# Damos um help para aparecer bonito na hora do `pixo --help`.
app = typer.Typer(help="PIX Observatory CLI — ferramentas de ingestão e operação.")

# `bacen_app` é um sub-grupo. Vai abrigar todos os comandos relacionados a
# coisas que envolvem a API do Bacen.
bacen_app = typer.Typer(help="Comandos relacionados à ingestão da API Bacen Olinda.")

# Pendura o sub-grupo no app principal sob o nome "bacen".
# Isso é o que permite a forma `pixo bacen <comando>`.
app.add_typer(bacen_app, name="bacen")

# Um logger estruturado — usaremos para registrar o que aconteceu, não para
# print()s ad-hoc. Mais sobre isso em config.py.
log = structlog.get_logger(__name__)


# -----------------------------------------------------------------------------
# O comando em si: `pixo bacen ingest`
# -----------------------------------------------------------------------------
#
# O decorator `@bacen_app.command("ingest")` registra a função abaixo como
# sendo o comando "ingest" do sub-grupo "bacen". Não execute essa função
# diretamente; o typer chama ela quando você roda o terminal.
#
# Typer LÊ a assinatura da função (tipos, defaults, `typer.Argument/Option`)
# para gerar automaticamente:
#  - validação de tipos (vai reclamar se você passar texto onde espera int)
#  - mensagem de --help bonita
#  - conversão de valores (ex: string YYYY-MM-DD → objeto date)
@bacen_app.command("ingest")
def bacen_ingest(
    # Argument: parâmetro POSICIONAL obrigatório.
    # Quem rodar tem que digitar o nome do endpoint logo após "ingest".
    endpoint: str = typer.Argument(
        ...,  # os "..." significam "obrigatório, sem default"
        help="Nome do endpoint OData (ex.: EstoqueDeChavesPix).",
    ),
    # Option: parâmetros opcionais com flags. Note os dois nomes em --filter:
    # "--filter" é o que o usuário digita; o nome da variável Python interna é
    # "filter_query" (não usamos "filter" porque é palavra reservada em Python).
    filter_query: str = typer.Option(
        None,
        "--filter",
        help='Expressão OData $filter (ex.: "AnoMes ge 202401").',
    ),
    order_by: str = typer.Option(
        None,
        "--order-by",
        help="Expressão OData $orderby. Recomendado ao paginar.",
    ),
    max_records: int = typer.Option(
        None,
        "--max-records",
        help="Parar depois de N registros (útil para testes).",
    ),
    output_root: Path = typer.Option(
        None,
        "--output-root",
        help="Sobrescreve a raiz dos arquivos brutos (padrão: settings.raw_root).",
    ),
    run_date: str = typer.Option(
        None,
        "--date",
        help="Data da partição YYYY-MM-DD (padrão: hoje).",
    ),
    params: list[str] = typer.Option(
        [],
        "--param",
        "-p",
        help='Parâmetro extra "chave=valor" (repetível). Ex.: --param "@Data=\'2026-05-31\'"',
    ),
) -> None:
    """Busca dados de um endpoint Olinda do Bacen e grava como Parquet.

    Esta docstring vira a descrição que aparece em `pixo bacen ingest --help`.
    """
    # Se o usuário passou --date "2026-06-08", convertemos para objeto date.
    # Se não passou, deixamos como None — a função interna usa o dia atual.
    parsed_date = date.fromisoformat(run_date) if run_date else None

    # Converte a lista de strings "chave=valor" num dict {chave: valor}.
    # Útil para parâmetros nomeados do Olinda como @Data='2026-05-31'.
    extra_params: dict[str, str] = {}
    for item in params:
        if "=" not in item:
            raise typer.BadParameter(f"--param deve ser 'chave=valor', recebido: {item}")
        key, _, value = item.partition("=")
        extra_params[key] = value

    # Chama a "receita completa" — a função que faz o trabalho pesado.
    # Note que este arquivo (cli.py) NÃO contém lógica de negócio. Ele só
    # traduz "linha de comando" → "chamada de função Python". Toda a lógica
    # de verdade está em bacen/ingest.py. Isso é PROPOSITAL: amanhã podemos
    # chamar `ingest_endpoint` direto do Airflow, sem passar pelo CLI.
    out = ingest_endpoint(
        endpoint,
        run_date=parsed_date,
        filter_query=filter_query,
        order_by=order_by,
        max_records=max_records,
        output_root=output_root,
        extra_params=extra_params or None,
    )

    # typer.echo() é como `print()`, mas integrado com o typer (lida com
    # cores, redirecionamento de saída, etc.). Pode usar print(); echo é
    # só uma convenção mais profissional.
    typer.echo(f"Wrote {out}")


# -----------------------------------------------------------------------------
# Ignição quando o arquivo é rodado diretamente (não via `pixo`).
# -----------------------------------------------------------------------------
# Útil quando você quer testar sem instalar: `python -m pix_observatory.cli`.
# Em uso normal você invoca via `pixo` (registrado no pyproject.toml).
if __name__ == "__main__":
    app()
