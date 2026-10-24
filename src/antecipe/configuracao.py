"""Abre o JSON oficial do fundo."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfiguracaoInvalida(Exception):
    """O JSON de configuração não pode ser usado."""


@dataclass(frozen=True)
class Validador:
    codigo: str
    ativo: bool
    parametros: dict[str, Any]


@dataclass(frozen=True)
class Configuracao:
    fundo_nome: str
    fundo_cnpj: str
    validadores: tuple[Validador, ...]
    metodo: str
    taxa_mensal_percentual: str
    base_dias: int

    def ativos(self) -> tuple[Validador, ...]:
        return tuple(item for item in self.validadores if item.ativo)


def carregar(raiz: Path | None = None) -> Configuracao:
    base = Path(__file__).resolve().parents[2] if raiz is None else raiz
    dados = _ler_json(base / "config" / "validadores_antecipe.json")
    if not isinstance(dados, dict):
        raise ConfiguracaoInvalida("o JSON do fundo precisa ser um objeto")
    fundo = dados.get("fundo")
    preco = dados.get("precificacao")
    lista = dados.get("validadores")
    if not isinstance(fundo, dict) or not isinstance(preco, dict) or not isinstance(lista, list):
        raise ConfiguracaoInvalida("o JSON do fundo está incompleto")
    taxa = preco.get("taxa_mensal_percentual")
    base_dias = preco.get("base_dias")
    if isinstance(taxa, bool) or not isinstance(taxa, (int, float)):
        raise ConfiguracaoInvalida("taxa mensal inválida")
    if isinstance(base_dias, bool) or not isinstance(base_dias, int) or base_dias <= 0:
        raise ConfiguracaoInvalida("base de dias inválida")
    return Configuracao(
        fundo_nome=_texto(fundo, "nome"),
        fundo_cnpj=_texto(fundo, "cnpj"),
        validadores=tuple(_validador(item, i) for i, item in enumerate(lista)),
        metodo=_texto(preco, "metodo"),
        taxa_mensal_percentual=str(taxa),
        base_dias=base_dias,
    )


def _validador(item: Any, indice: int) -> Validador:
    if not isinstance(item, dict):
        raise ConfiguracaoInvalida(f"validador {indice} inválido")
    codigo = item.get("codigo")
    ativo = item.get("ativo")
    parametros = item.get("parametros")
    if not isinstance(codigo, str) or not codigo.strip():
        raise ConfiguracaoInvalida(f"validador {indice} sem código")
    if not isinstance(ativo, bool) or not isinstance(parametros, dict):
        raise ConfiguracaoInvalida(f"validador {codigo} incompleto")
    return Validador(codigo, ativo, parametros)


def _texto(origem: dict[str, Any], campo: str) -> str:
    valor = origem.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ConfiguracaoInvalida(f"{campo} inválido")
    return valor


def carregar_sacados(raiz: Path | None = None) -> frozenset[str]:
    base = Path(__file__).resolve().parents[2] if raiz is None else raiz
    caminho = base / "config" / "sacados_recusados.txt"
    if not caminho.is_file():
        raise ConfiguracaoInvalida("arquivo ausente: sacados_recusados.txt")
    sacados: set[str] = set()
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("#"):
            continue
        numeros = "".join(caractere for caractere in texto if caractere.isdigit())
        if len(numeros) != 14:
            raise ConfiguracaoInvalida("sacado recusado sem 14 dígitos")
        sacados.add(numeros)
    return frozenset(sacados)


def _ler_json(caminho: Path) -> Any:
    if not caminho.is_file():
        raise ConfiguracaoInvalida(f"arquivo ausente: {caminho.name}")
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ConfiguracaoInvalida(f"JSON inválido em {caminho.name}") from erro


def main() -> None:
    configuracao = carregar()
    print(f"{configuracao.fundo_nome}: {len(configuracao.ativos())} validadores ativos")


if __name__ == "__main__":
    main()
