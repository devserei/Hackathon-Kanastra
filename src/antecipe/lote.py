"""Lê o estoque uma vez e decide o lote da empresa, de cima para baixo."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from antecipe.avaliar import avaliar_nota, digitos, raiz
from antecipe.configuracao import Configuracao, Validador, carregar
from antecipe.normalizar import COLUNAS, ErroLinha, ler_linha, ler_texto

CABECALHO = ";".join(COLUNAS)


@dataclass(frozen=True)
class Indice:
    chaves: set[tuple[str, str, date]]
    total_fundo_centavos: int
    por_raiz_centavos: dict[str, int]


@dataclass(frozen=True)
class LinhaLote:
    nu_documento: str
    motivos: tuple[str, ...]
    liquido_centavos: int | None
    codigos: tuple[str, ...] = ()

    @property
    def aceita(self) -> bool:
        return not self.motivos


@dataclass(frozen=True)
class ResultadoLote:
    linhas: tuple[LinhaLote, ...]
    total_liquido_centavos: int
    total_face_recusado_centavos: int = 0

    @property
    def aceitas(self) -> int:
        return sum(1 for linha in self.linhas if linha.aceita)

    @property
    def recusadas(self) -> int:
        return len(self.linhas) - self.aceitas


def montar(caminho: Path, doc_fundo: str) -> Indice:
    alvo = digitos(doc_fundo)
    chaves: set[tuple[str, str, date]] = set()
    total = 0
    por_raiz: dict[str, int] = {}
    for nota in _notas(caminho):
        chaves.add((digitos(nota.doc_cedente), nota.nu_documento, nota.vencimento))
        if digitos(nota.doc_fundo) != alvo:
            continue
        total += nota.valor_centavos
        grupo = raiz(nota.doc_sacado)
        if grupo is not None:
            por_raiz[grupo] = por_raiz.get(grupo, 0) + nota.valor_centavos
    return Indice(chaves, total, por_raiz)


def carregar_cadastro(caminho: Path) -> dict[str, str]:
    if not caminho.is_file():
        return {}
    cadastro: dict[str, str] = {}
    for linha in ler_texto(caminho).splitlines():
        if not linha.strip() or linha.lower().startswith("doc;"):
            continue
        documento, situacao = linha.split(";", 1)
        cadastro[digitos(documento)] = situacao.strip()
    return cadastro


def processar(
    caminho: Path,
    configuracao: Configuracao,
    cadastro: dict[str, str] | None = None,
    registro: Path | None = None,
) -> ResultadoLote:
    inicio = time.perf_counter()
    notas = list(_notas_ou_erro(caminho))
    totais, grupos = _totais(notas)
    regra = next(
        (item for item in configuracao.validadores if item.ativo and item.codigo == "CONCENTRACAO_MAXIMA_SACADO"),
        None,
    )
    vistas: set[tuple[str, str, date]] = set()
    linhas: list[LinhaLote] = []
    soma = 0
    face_recusado = 0
    for nota_ou_erro in notas:
        if isinstance(nota_ou_erro, ErroLinha):
            linhas.append(LinhaLote("", (str(nota_ou_erro),), None))
            continue
        nota = nota_ou_erro
        resultado = avaliar_nota(nota, configuracao, cadastro)
        motivos = list(resultado.motivos)
        codigos = list(resultado.codigos)
        liquido = resultado.liquido_centavos
        if not motivos:
            chave = (digitos(nota.doc_cedente), nota.nu_documento, nota.vencimento)
            if chave in vistas:
                motivos.append(
                    "Esta parcela já foi adquirida: mesmo cedente, mesmo número e mesmo vencimento."
                )
                liquido = None
            else:
                vistas.add(chave)
                motivo = _concentracao(nota, totais, grupos, regra)
                if motivo:
                    motivos.append(motivo)
                    codigos.append("CONCENTRACAO_MAXIMA_SACADO")
                    liquido = None
        else:
            liquido = None
        if liquido is not None:
            soma += liquido
        else:
            face_recusado += nota.valor_centavos
        linhas.append(LinhaLote(nota.nu_documento, tuple(motivos), liquido, tuple(codigos)))
    resultado = ResultadoLote(tuple(linhas), soma, face_recusado)
    _registrar(resultado, int((time.perf_counter() - inicio) * 1000), registro)
    return resultado


def _totais(notas: list) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    totais: dict[str, int] = {}
    grupos: dict[str, dict[str, int]] = {}
    for nota in notas:
        if isinstance(nota, ErroLinha):
            continue
        fundo = digitos(nota.doc_fundo)
        totais[fundo] = totais.get(fundo, 0) + nota.valor_centavos
        grupo = raiz(nota.doc_sacado)
        if grupo is None:
            continue
        por_raiz = grupos.setdefault(fundo, {})
        por_raiz[grupo] = por_raiz.get(grupo, 0) + nota.valor_centavos
    return totais, grupos


def _concentracao(nota, totais: dict[str, int], grupos: dict[str, dict[str, int]], regra: Validador | None) -> str | None:
    if regra is None:
        return None
    grupo = raiz(nota.doc_sacado)
    if grupo is None:
        return "CNPJ do sacado não permite calcular a concentração."
    fundo = digitos(nota.doc_fundo)
    total = totais.get(fundo, 0)
    ocupado = grupos.get(fundo, {}).get(grupo, 0)
    if total <= 0:
        return None
    limite = Decimal(str(regra.parametros["percentual_maximo"]))
    if Decimal(ocupado) * 100 <= limite * Decimal(total):
        return None
    percentual = (Decimal(ocupado) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    texto = f"{percentual}".replace(".", ",")
    limite_texto = f"{limite}".replace(".", ",")
    return f"O grupo do sacado ficaria com {texto}% do fundo. O limite é {limite_texto}%."


def _registrar(resultado: ResultadoLote, duracao_ms: int, destino: Path | None) -> None:
    contagem: dict[str, int] = {}
    for linha in resultado.linhas:
        for codigo in linha.codigos:
            contagem[codigo] = contagem.get(codigo, 0) + 1
    evento = {
        "duracao_ms": duracao_ms,
        "linhas": len(resultado.linhas),
        "aceitas": resultado.aceitas,
        "recusadas": resultado.recusadas,
        "codigos": dict(sorted(contagem.items())),
    }
    caminho = destino or (Path(__file__).resolve().parents[2] / "logs" / "lotes.log")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")


def _notas(caminho: Path):
    for item in _notas_ou_erro(caminho):
        if isinstance(item, ErroLinha):
            raise item
        yield item


def _notas_ou_erro(caminho: Path):
    for linha in ler_texto(caminho).splitlines():
        if not linha.strip() or linha.strip() == CABECALHO:
            continue
        try:
            yield ler_linha(linha)
        except ErroLinha as erro:
            yield erro


def main() -> None:
    if len(sys.argv) != 2:
        print("uso: python -m antecipe.lote CAMINHO_DO_LOTE", file=sys.stderr)
        raise SystemExit(1)
    raiz = Path(__file__).resolve().parents[2]
    resultado = processar(
        Path(sys.argv[1]),
        carregar(raiz),
        carregar_cadastro(raiz / "config" / "cnpj_situacao_mock.csv"),
    )
    print(
        f"aceitas {resultado.aceitas} recusadas {resultado.recusadas} "
        f"liquido_centavos {resultado.total_liquido_centavos}"
    )
    for linha in resultado.linhas:
        estado = "ok" if linha.aceita else "recusada"
        print(f"{estado} {linha.nu_documento} {linha.liquido_centavos or ''} {' | '.join(linha.motivos)}")


if __name__ == "__main__":
    main()
