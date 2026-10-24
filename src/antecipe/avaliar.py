"""Recebe a nota normalizada, aplica as regras do JSON e calcula o líquido."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from antecipe.configuracao import Configuracao
from antecipe.normalizar import Nota

DATA_OPERACAO = date(2026, 10, 24)
DO_LOTE = ("CONCENTRACAO_MAXIMA_SACADO", "CONCENTRACAO_MAXIMA_CEDENTE")


class CodigoDesconhecido(Exception):
    """Um código do JSON não tem implementação. O lote para."""

    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__(f"validador desconhecido: {codigo}")


@dataclass(frozen=True)
class ResultadoNota:
    motivos: tuple[str, ...]
    desconto_centavos: int | None
    liquido_centavos: int | None
    codigos: tuple[str, ...] = ()

    @property
    def recusada(self) -> bool:
        return bool(self.motivos)


def avaliar_nota(
    nota: Nota,
    configuracao: Configuracao,
    cadastro: dict[str, str] | None = None,
) -> ResultadoNota:
    desconhecido = next(
        (
            item.codigo
            for item in configuracao.validadores
            if item.codigo not in _REGISTRO and item.codigo not in DO_LOTE
        ),
        None,
    )
    if desconhecido:
        raise CodigoDesconhecido(desconhecido)

    motivos: list[str] = []
    codigos: list[str] = []
    for item in configuracao.validadores:
        if not item.ativo or item.codigo in DO_LOTE:
            continue
        motivo = _REGISTRO[item.codigo](nota, item.parametros, cadastro or {})
        if motivo:
            motivos.append(motivo)
            codigos.append(item.codigo)
    if motivos:
        return ResultadoNota(tuple(motivos), None, None, tuple(codigos))

    dias = max(0, (nota.vencimento - DATA_OPERACAO).days)
    desconto = desconto_simples(
        nota.valor_centavos,
        dias,
        configuracao.taxa_mensal_percentual,
        configuracao.base_dias,
    )
    return ResultadoNota((), desconto, nota.valor_centavos - desconto, ())


def digitos(documento: str) -> str:
    return "".join(caractere for caractere in documento if caractere.isdigit())


def raiz(documento: str) -> str | None:
    numeros = digitos(documento)
    if len(numeros) < 8:
        return None
    return numeros[:8]


def cnpj_valido(documento: str) -> bool:
    numeros = digitos(documento)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    return _digito(numeros[:12]) == numeros[12] and _digito(numeros[:13]) == numeros[13]


def desconto_simples(valor_centavos: int, dias: int, taxa_mensal_percentual: str, base_dias: int) -> int:
    if valor_centavos < 0 or dias < 0 or base_dias <= 0:
        raise ValueError("desconto simples exige valor e prazo não negativos")
    numerador = Decimal(valor_centavos) * Decimal(taxa_mensal_percentual) * Decimal(dias)
    denominador = Decimal(100) * Decimal(base_dias)
    return int((numerador / denominador).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _cnpj(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del parametros, cadastro
    if len(digitos(nota.doc_sacado)) != 14:
        return "CNPJ do sacado não tem 14 dígitos."
    if not cnpj_valido(nota.doc_sacado):
        return "CNPJ do sacado com dígito verificador inválido."
    return None


def _situacao(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    if not cadastro:
        return None
    status = cadastro.get(digitos(nota.doc_sacado))
    if status is None:
        return None
    aceitas = parametros.get("situacoes_aceitas") or []
    if status not in aceitas:
        return f"Situação cadastral {status}. Este fundo aceita {_lista(aceitas)}."
    return None


def _tipo(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del cadastro
    aceitos = parametros.get("tipos_aceitos") or []
    if nota.tipo_recebivel in aceitos:
        return None
    return f"Tipo {nota.tipo_recebivel}. Este fundo compra {_lista(aceitos)}."


def _valor(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del cadastro
    minimo = _centavos(parametros["valor_minimo"])
    if nota.valor_centavos >= minimo:
        return None
    return f"Valor de {_reais(nota.valor_centavos)}. O mínimo deste fundo é {_reais(minimo)}."


def _vencida(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del parametros, cadastro
    if nota.vencimento >= nota.aquisicao:
        return None
    return (
        f"Vencida em {nota.vencimento.strftime('%d/%m/%Y')}. "
        f"A aquisição é em {nota.aquisicao.strftime('%d/%m/%Y')}."
    )


def _prazo_maximo(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del cadastro
    maximo = parametros["prazo_maximo_dias"]
    dias = (nota.vencimento - nota.aquisicao).days
    if dias <= maximo:
        return None
    return f"Prazo de {dias} dias. O máximo é {maximo}."


def _prazo_minimo(nota: Nota, parametros: dict[str, Any], cadastro: dict[str, str]) -> str | None:
    del cadastro
    minimo = parametros["prazo_minimo_dias"]
    dias = (nota.vencimento - nota.aquisicao).days
    if dias >= minimo:
        return None
    return f"Prazo de {dias} dias. O mínimo é {minimo}."


def _centavos(valor: int | float) -> int:
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _reais(centavos: int) -> str:
    reais, frac = divmod(abs(centavos), 100)
    milhar = f"{reais:,}".replace(",", ".")
    sinal = "-" if centavos < 0 else ""
    return f"{sinal}R$ {milhar},{frac:02d}"


def _lista(itens: list[Any]) -> str:
    textos = [str(item) for item in itens]
    if len(textos) == 1:
        return textos[0]
    return ", ".join(textos[:-1]) + " e " + textos[-1]


def _digito(base: str) -> str:
    pesos = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2) if len(base) == 12 else (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    resto = sum(int(numero) * peso for numero, peso in zip(base, pesos)) % 11
    return "0" if resto < 2 else str(11 - resto)


_REGISTRO: dict[str, Callable[[Nota, dict[str, Any], dict[str, str]], str | None]] = {
    "CNPJ_SACADO_VALIDO": _cnpj,
    "SITUACAO_CADASTRAL_SACADO": _situacao,
    "TIPO_RECEBIVEL": _tipo,
    "VALOR_MINIMO": _valor,
    "NAO_VENCIDA": _vencida,
    "PRAZO_MAXIMO": _prazo_maximo,
    "PRAZO_MINIMO": _prazo_minimo,
}
