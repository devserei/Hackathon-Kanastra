"""Abre o JSON do fundo e o contrato operacional."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class ConfiguracaoInvalida(Exception):
    """O JSON de configuração não pode ser usado."""


CHAVE_RECEBIVEL = ("doc_cedente", "nu_documento", "data_vencimento")


@dataclass(frozen=True)
class Validador:
    codigo: str
    ativo: bool
    parametros: dict[str, Any]


@dataclass(frozen=True)
class Precificacao:
    metodo: str
    taxa_mensal_percentual: str
    base_dias: int


@dataclass(frozen=True)
class Dinheiro:
    unidade: str
    arredondamento: str
    casas_decimais: int
    arredondar_por: str


@dataclass(frozen=True)
class Prazo:
    tipo: str
    inicio: str
    fim: str
    vence_no_dia_entra: bool


@dataclass(frozen=True)
class Concentracao:
    carteira: str
    inclui_notas_vencidas: bool
    nota_recusada_por_outra_regra_ocupa_limite: bool
    ordem_do_lote: str


@dataclass(frozen=True)
class SituacaoCadastral:
    fonte: str
    ausente: str
    mensagem_ausente: str
    por_cnpj: dict[str, str]


@dataclass(frozen=True)
class Configuracao:
    fundo_nome: str
    fundo_cnpj: str
    validadores: tuple[Validador, ...]
    precificacao: Precificacao
    data_operacao: str
    chave_recebivel: tuple[str, ...]
    preservar_numero_documento: bool
    valor_fora_da_chave: bool
    dinheiro: Dinheiro
    prazo: Prazo
    concentracao: Concentracao
    situacao_cadastral: SituacaoCadastral
    duplicidade_escopo: str
    duplicidade_reenvio: str

    def validadores_ativos(self) -> tuple[Validador, ...]:
        return tuple(item for item in self.validadores if item.ativo)


def carregar(raiz: Path | None = None) -> Configuracao:
    base = Path(__file__).resolve().parents[2] if raiz is None else raiz
    regras = _ler_json(base / "config" / "validadores_antecipe.json")
    operacao = _ler_json(base / "config" / "operacao.json")
    fonte_situacao = _texto(operacao.get("situacao_cadastral"), "fonte", "operacao.situacao_cadastral")
    situacao = _ler_json(base / fonte_situacao)
    return _montar(regras, operacao, situacao)


def _montar(regras: Any, operacao: Any, situacao: Any) -> Configuracao:
    fundo = _objeto(regras, "fundo", "validadores")
    precificacao = _objeto(regras, "precificacao", "validadores")
    lista = regras.get("validadores") if isinstance(regras, dict) else None
    if not isinstance(lista, list) or not lista:
        raise ConfiguracaoInvalida("validadores.validadores precisa ser uma lista com ao menos um item")

    validadores = tuple(_validador(item, indice) for indice, item in enumerate(lista))
    codigos = [item.codigo for item in validadores]
    if len(codigos) != len(set(codigos)):
        raise ConfiguracaoInvalida("validadores.codigo repetido")

    taxa = precificacao.get("taxa_mensal_percentual")
    base_dias = precificacao.get("base_dias")
    if isinstance(taxa, bool) or not isinstance(taxa, (int, float)):
        raise ConfiguracaoInvalida("precificacao.taxa_mensal_percentual precisa ser numérica")
    if isinstance(base_dias, bool) or not isinstance(base_dias, int) or base_dias <= 0:
        raise ConfiguracaoInvalida("precificacao.base_dias precisa ser um inteiro maior que zero")

    chave = operacao.get("chave_recebivel") if isinstance(operacao, dict) else None
    if not isinstance(chave, list) or tuple(chave) != CHAVE_RECEBIVEL:
        raise ConfiguracaoInvalida(
            "operacao.chave_recebivel precisa ser doc_cedente, nu_documento e data_vencimento"
        )

    dinheiro = _objeto(operacao, "dinheiro", "operacao")
    prazo = _objeto(operacao, "prazo", "operacao")
    concentracao = _objeto(operacao, "concentracao", "operacao")
    situacao_op = _objeto(operacao, "situacao_cadastral", "operacao")
    duplicidade = _objeto(operacao, "duplicidade", "operacao")
    _conferir_contrato(operacao, dinheiro, prazo, concentracao, situacao_op)

    return Configuracao(
        fundo_nome=_texto(fundo, "nome", "fundo"),
        fundo_cnpj=_texto(fundo, "cnpj", "fundo"),
        validadores=validadores,
        precificacao=Precificacao(
            metodo=_texto(precificacao, "metodo", "precificacao"),
            taxa_mensal_percentual=str(taxa),
            base_dias=base_dias,
        ),
        data_operacao=_data(operacao.get("data_operacao")),
        chave_recebivel=CHAVE_RECEBIVEL,
        preservar_numero_documento=_booleano(operacao, "preservar_numero_documento", "operacao"),
        valor_fora_da_chave=_booleano(operacao, "valor_fora_da_chave", "operacao"),
        dinheiro=Dinheiro(
            unidade=_texto(dinheiro, "unidade", "dinheiro"),
            arredondamento=_texto(dinheiro, "arredondamento", "dinheiro"),
            casas_decimais=_inteiro_positivo(dinheiro.get("casas_decimais"), "dinheiro.casas_decimais"),
            arredondar_por=_texto(dinheiro, "arredondar_por", "dinheiro"),
        ),
        prazo=Prazo(
            tipo=_texto(prazo, "tipo", "prazo"),
            inicio=_texto(prazo, "inicio", "prazo"),
            fim=_texto(prazo, "fim", "prazo"),
            vence_no_dia_entra=_booleano(prazo, "vence_no_dia_entra", "prazo"),
        ),
        concentracao=Concentracao(
            carteira=_texto(concentracao, "carteira", "concentracao"),
            inclui_notas_vencidas=_booleano(concentracao, "inclui_notas_vencidas", "concentracao"),
            nota_recusada_por_outra_regra_ocupa_limite=_booleano(
                concentracao,
                "nota_recusada_por_outra_regra_ocupa_limite",
                "concentracao",
            ),
            ordem_do_lote=_texto(concentracao, "ordem_do_lote", "concentracao"),
        ),
        situacao_cadastral=SituacaoCadastral(
            fonte=_texto(situacao_op, "fonte", "situacao_cadastral"),
            ausente=_texto(situacao_op, "ausente", "situacao_cadastral"),
            mensagem_ausente=_texto(situacao_op, "mensagem_ausente", "situacao_cadastral"),
            por_cnpj=_por_cnpj(situacao),
        ),
        duplicidade_escopo=_texto(duplicidade, "escopo", "duplicidade"),
        duplicidade_reenvio=_texto(duplicidade, "reenvio", "duplicidade"),
    )


def _conferir_contrato(
    operacao: dict[str, Any],
    dinheiro: dict[str, Any],
    prazo: dict[str, Any],
    concentracao: dict[str, Any],
    situacao: dict[str, Any],
) -> None:
    esperado = {
        "preservar_numero_documento": True,
        "valor_fora_da_chave": True,
    }
    for campo, valor in esperado.items():
        if operacao.get(campo) is not valor:
            raise ConfiguracaoInvalida(f"operacao.{campo} precisa ser {valor}")
    if dinheiro.get("unidade") != "centavos" or dinheiro.get("arredondamento") != "HALF_UP":
        raise ConfiguracaoInvalida("dinheiro precisa usar centavos e arredondamento HALF_UP")
    if dinheiro.get("arredondar_por") != "nota" or dinheiro.get("casas_decimais") != 2:
        raise ConfiguracaoInvalida("dinheiro precisa arredondar cada nota em duas casas")
    if prazo.get("tipo") != "dias_corridos" or prazo.get("vence_no_dia_entra") is not True:
        raise ConfiguracaoInvalida("prazo precisa ser em dias corridos e aceitar o vencimento no dia")
    if prazo.get("inicio") != "data_operacao" or prazo.get("fim") != "data_vencimento":
        raise ConfiguracaoInvalida("prazo vai da data da operação até o vencimento")
    if concentracao.get("inclui_notas_vencidas") is not True:
        raise ConfiguracaoInvalida("concentracao inclui as notas vencidas do estoque")
    if concentracao.get("nota_recusada_por_outra_regra_ocupa_limite") is not False:
        raise ConfiguracaoInvalida("nota recusada por outra regra não ocupa limite")
    if concentracao.get("ordem_do_lote") != "arquivo_de_cima_para_baixo":
        raise ConfiguracaoInvalida("o lote é lido de cima para baixo")
    if situacao.get("ausente") != "recusar":
        raise ConfiguracaoInvalida("situação cadastral ausente recusa a nota")


def _validador(item: Any, indice: int) -> Validador:
    if not isinstance(item, dict):
        raise ConfiguracaoInvalida(f"validadores[{indice}] precisa ser um objeto")
    codigo = item.get("codigo")
    ativo = item.get("ativo")
    parametros = item.get("parametros")
    if not isinstance(codigo, str) or not codigo.strip():
        raise ConfiguracaoInvalida(f"validadores[{indice}].codigo inválido")
    if not isinstance(ativo, bool):
        raise ConfiguracaoInvalida(f"validadores[{indice}].ativo precisa ser verdadeiro ou falso")
    if not isinstance(parametros, dict):
        raise ConfiguracaoInvalida(f"validadores[{indice}].parametros precisa ser um objeto")
    return Validador(codigo=codigo, ativo=ativo, parametros=parametros)


def _por_cnpj(situacao: Any) -> dict[str, str]:
    if not isinstance(situacao, dict):
        raise ConfiguracaoInvalida("situacao_cadastral precisa ser um objeto")
    mapa = situacao.get("por_cnpj")
    if not isinstance(mapa, dict):
        raise ConfiguracaoInvalida("situacao_cadastral.por_cnpj precisa ser um objeto")
    convertido: dict[str, str] = {}
    for cnpj, status in mapa.items():
        if not isinstance(cnpj, str) or len(cnpj) != 14 or not cnpj.isdigit():
            raise ConfiguracaoInvalida("chave de por_cnpj precisa ter 14 dígitos")
        if not isinstance(status, str) or not status.strip():
            raise ConfiguracaoInvalida(f"situação cadastral de {cnpj} vazia")
        convertido[cnpj] = status
    return convertido


def _ler_json(caminho: Path) -> Any:
    if not caminho.is_file():
        raise ConfiguracaoInvalida(f"arquivo ausente: {caminho}")
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ConfiguracaoInvalida(f"JSON inválido em {caminho.name}: {erro}") from erro


def _objeto(origem: Any, campo: str, nome: str) -> dict[str, Any]:
    if not isinstance(origem, dict):
        raise ConfiguracaoInvalida(f"{nome} precisa ser um objeto")
    valor = origem.get(campo)
    if not isinstance(valor, dict):
        raise ConfiguracaoInvalida(f"{nome}.{campo} precisa ser um objeto")
    return valor


def _texto(origem: dict[str, Any], campo: str, nome: str) -> str:
    valor = origem.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ConfiguracaoInvalida(f"{nome}.{campo} precisa ser um texto")
    return valor


def _booleano(origem: dict[str, Any], campo: str, nome: str) -> bool:
    valor = origem.get(campo)
    if not isinstance(valor, bool):
        raise ConfiguracaoInvalida(f"{nome}.{campo} precisa ser verdadeiro ou falso")
    return valor


def _inteiro_positivo(valor: Any, nome: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ConfiguracaoInvalida(f"{nome} precisa ser um inteiro maior que zero")
    return valor


def _data(valor: Any) -> str:
    if not isinstance(valor, str):
        raise ConfiguracaoInvalida("operacao.data_operacao precisa ser uma data AAAA-MM-DD")
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError as erro:
        raise ConfiguracaoInvalida("operacao.data_operacao precisa ser uma data AAAA-MM-DD") from erro
    return valor


if __name__ == "__main__":
    configuracao = carregar()
    ativos = len(configuracao.validadores_ativos())
    print(
        f"{configuracao.fundo_nome}: {ativos} validadores ativos, "
        f"operação em {configuracao.data_operacao}"
    )
