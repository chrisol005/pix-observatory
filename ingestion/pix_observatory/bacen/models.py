"""
================================================================================
 bacen/models.py — Modelos Pydantic tipados dos endpoints Bacen
================================================================================

POR QUE EXISTE ESSE ARQUIVO?

O cliente Bacen (`client.py`) devolve `dict` puro — bom para a camada bronze,
onde a regra é "preserve o dado exatamente como veio da fonte". Mas todo
código a JUSANTE — análise, ML, transformações, testes — fica melhor
trabalhando com objetos tipados, validados, com nomes em snake_case.

Este arquivo é essa camada de tradução. Você pega um dict bruto do Bacen
e instancia o model correspondente. Pydantic valida, normaliza nomes,
converte tipos.

--------------------------------------------------------------------------------
 CONCEITOS DE PYDANTIC QUE APARECEM AQUI
--------------------------------------------------------------------------------

1) `BaseModel` — classe base do Pydantic. Toda classe que herda dela vira
   um "schema" validador: ao instanciar, Pydantic checa tipos, ranges,
   valores aceitos, e levanta erro detalhado se algo não bate.

2) `Field(alias="X")` — o JSON do Bacen usa "Nome", "TipoChave" (PascalCase
   e/ou inconsistente). Em Python preferimos `institution_name`, `key_type`.
   `alias` mapeia "esse campo Python chama-se assim, mas no JSON entra com
   esse nome alternativo".

3) `model_config = ConfigDict(populate_by_name=True)` — permite criar o
   model tanto com o nome Python quanto com o alias. Sem isso, só o alias
   funcionaria, o que atrapalha código limpo.

4) `Enum` — restringe um campo a um conjunto fechado de valores. Se a
   Bacen mandar um valor novo (ex.: novo tipo de chave), a validação
   FALHA — o que é bom, porque a gente fica sabendo da mudança em vez
   de gravar lixo silenciosamente.

5) `Field(pattern=...)` e `Field(ge=0)` — validações de formato e range
   declarativas. ISPB precisa ser 8 dígitos; qtdChaves não pode ser
   negativo.

--------------------------------------------------------------------------------
 COMO USAR
--------------------------------------------------------------------------------

    from pix_observatory.bacen.models import ChavePix

    # Validar um registro vindo do Parquet:
    raw = {"Data": "2025-07-31", "ISPB": "02480577", "Nome": "X", ...}
    chave = ChavePix(**raw)
    print(chave.snapshot_date)       # date(2025, 7, 31)
    print(chave.user_type)           # NaturezaUsuario.PF
    print(chave.key_count)           # 968

    # Validar uma lista inteira:
    chaves = [ChavePix(**r) for r in records]
================================================================================
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# -----------------------------------------------------------------------------
# Enums — domínios fechados que a Bacen usa
# -----------------------------------------------------------------------------


class NaturezaUsuario(str, Enum):
    """Tipo de titular da chave PIX.

    Por que herdar de `str, Enum`? Faz o enum se comportar como string em
    serialização (JSON, Parquet), mantendo a validação.
    """

    PESSOA_FISICA = "PF"
    PESSOA_JURIDICA = "PJ"


class TipoChave(str, Enum):
    """Tipo da chave PIX cadastrada.

    Os 5 tipos definidos pelo Bacen. Atenção: a documentação oficial cita
    "telefone" e "EVP", mas os dados reais devolvem "Celular" e "Aleatória"
    — usamos os valores que de fato aparecem na API.
    """

    EMAIL = "e-mail"
    CPF = "CPF"
    CNPJ = "CNPJ"
    CELULAR = "Celular"
    ALEATORIA = "Aleatória"


# -----------------------------------------------------------------------------
# Models — um por endpoint Bacen
# -----------------------------------------------------------------------------


class ChavePix(BaseModel):
    """Snapshot mensal de chaves PIX por participante / tipo / natureza.

    Cada registro representa: "no fim do mês X, o participante Y tinha N
    chaves do tipo Z cadastradas para usuários PF (ou PJ)".

    Endpoint Bacen: ChavesPix(Data=@Data)
    Documentação: https://dadosabertos.bcb.gov.br/dataset/pix/resource/933bb35c-31e7-4514-9282-2c8400ea21a1
    """

    # ConfigDict é a forma moderna (Pydantic v2) de configurar o model.
    # - populate_by_name: aceita tanto nome Python quanto alias na construção
    # - str_strip_whitespace: remove espaços em branco de strings (alguns
    #   nomes vinham com espaços extras nos dados que olhei)
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    # `alias=` mapeia para o nome do campo no JSON do Bacen.
    # O nome Python (snake_case) é o que usamos no código.
    snapshot_date: date = Field(
        alias="Data",
        description="Data do snapshot — último dia útil do mês de referência.",
    )

    ispb: str = Field(
        alias="ISPB",
        pattern=r"^\d{8}$",
        description="ISPB (Identificador de Sistema de Pagamentos Brasileiro) — 8 dígitos.",
    )

    institution_name: str = Field(
        alias="Nome",
        min_length=1,
        description="Nome curto da instituição participante do PIX.",
    )

    user_type: NaturezaUsuario = Field(
        alias="NaturezaUsuario",
        description="Tipo de titular: PF (pessoa física) ou PJ (pessoa jurídica).",
    )

    key_type: TipoChave = Field(
        alias="TipoChave",
        description="Tipo da chave PIX (e-mail, CPF, CNPJ, telefone, EVP).",
    )

    key_count: int = Field(
        alias="qtdChaves",
        ge=0,
        description="Quantidade de chaves cadastradas neste recorte.",
    )

    segment: str = Field(
        alias="Segmento",
        description="Segmento da instituição (ex.: 'Banco Comercial', 'Cooperativa de Crédito').",
    )
