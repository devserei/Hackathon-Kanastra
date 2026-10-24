"""Lê o CSV publicado sem reescrevê-lo. O texto do arquivo entra em UTF-8."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

CODIFICACAO = "utf-8"
MARCA_DE_ORDEM = b"\xef\xbb\xbf"

COLUNAS = (
    "NOME_FUNDO",
    "DOC_FUNDO",
    "NOME_CEDENTE",
    "DOC_CEDENTE",
    "NOME_SACADO",
    "DOC_SACADO",
    "NU_DOCUMENTO",
    "TIPO_RECEBIVEL",
    "VALOR_NOMINAL",
    "DATA_VENCIMENTO_ORIGINAL",
    "DATA_AQUISICAO",
)


class ErroLinha(Exception):
    """A linha não pôde ser lida. Isso é diferente de uma recusa do fundo."""


class CodificacaoIncompativel(ErroLinha):
    """O arquivo não está em UTF-8. Outra codificação não é interpretada no lugar."""


class ValorInvalido(ErroLinha):
    """O texto não é um valor em reais."""


def para_centavos(texto: str) -> int:
    limpo = texto.strip()
    if not limpo:
        raise ValorInvalido("valor vazio")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except Exception as erro:
        raise ValorInvalido(f"valor inválido: {texto}") from erro
    centavos = (valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(centavos)


@dataclass(frozen=True)
class Nota:
    nome_fundo: str
    doc_fundo: str
    nome_cedente: str
    doc_cedente: str
    nome_sacado: str
    doc_sacado: str
    nu_documento: str
    tipo_recebivel: str
    valor_centavos: int
    vencimento: date
    aquisicao: date


def ler_texto(caminho: Path) -> str:
    dados = Path(caminho).read_bytes()
    if dados.startswith(MARCA_DE_ORDEM):
        dados = dados[3:]
    try:
        return dados.decode(CODIFICACAO)
    except UnicodeDecodeError as erro:
        raise CodificacaoIncompativel(
            "Arquivo fora de UTF-8. Latin-1 e Windows-1252 não são aceitos, "
            "para não trocar os acentos por outro caractere."
        ) from erro


def ler_linha(texto: str) -> Nota:
    campos = next(csv.reader([texto.rstrip("\r\n")], delimiter=";"))
    if campos == list(COLUNAS):
        raise ErroLinha("cabeçalho não é uma nota")
    if len(campos) != len(COLUNAS):
        raise ErroLinha(f"A linha tem {len(campos)} colunas. O formato tem {len(COLUNAS)}.")
    valores = {coluna: campos[indice].strip() for indice, coluna in enumerate(COLUNAS)}
    numero = valores["NU_DOCUMENTO"].strip()
    if not numero:
        raise ErroLinha("número do documento vazio")
    try:
        centavos = para_centavos(valores["VALOR_NOMINAL"])
    except ValorInvalido as erro:
        raise ErroLinha(str(erro)) from erro
    return Nota(
        nome_fundo=valores["NOME_FUNDO"],
        doc_fundo=valores["DOC_FUNDO"],
        nome_cedente=valores["NOME_CEDENTE"],
        doc_cedente=valores["DOC_CEDENTE"],
        nome_sacado=valores["NOME_SACADO"],
        doc_sacado=valores["DOC_SACADO"],
        nu_documento=numero,
        tipo_recebivel=valores["TIPO_RECEBIVEL"],
        valor_centavos=centavos,
        vencimento=_data(valores["DATA_VENCIMENTO_ORIGINAL"], "vencimento"),
        aquisicao=_data(valores["DATA_AQUISICAO"], "aquisição"),
    )


def _data(texto: str, nome: str) -> date:
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError as erro:
        raise ErroLinha(f"{nome} inválido: {texto}") from erro


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding=CODIFICACAO)
    texto = sys.stdin.readline()
    if not texto:
        raise SystemExit(1)
    try:
        nota = ler_linha(texto)
    except ErroLinha as erro:
        print(erro, file=sys.stderr)
        raise SystemExit(1) from erro
    print(f"{nota.nu_documento} {nota.valor_centavos}")


if __name__ == "__main__":
    main()
