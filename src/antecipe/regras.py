"""Regras do JSON, chamadas pelo avaliar. Não é uma etapa do fluxo."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from antecipe.configuracao import Configuracao
from antecipe.normalizar import Nota


class CodigoDesconhecido(Exception):
    """Um código do JSON não tem implementação. O lote para."""

    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__(f"validador desconhecido: {codigo}")


ADIADOS = (
    "CONCENTRACAO_MAXIMA_SACADO",
    "CONCENTRACAO_MAXIMA_CEDENTE",
)


def aplicar(nota: Nota, configuracao: Configuracao) -> tuple[tuple[str, ...], tuple[str, ...]]:
    desconhecidos = [
        item.codigo
        for item in configuracao.validadores
        if item.codigo not in _REGISTRO and item.codigo not in ADIADOS
    ]
    if desconhecidos:
        raise CodigoDesconhecido(desconhecidos[0])

    motivos: list[str] = []
    adiadas: list[str] = []
    for item in configuracao.validadores:
        if item.codigo in ADIADOS:
            if item.ativo:
                adiadas.append(item.codigo)
            continue
        if not item.ativo:
            continue
        motivo = _REGISTRO[item.codigo](nota, item.parametros, configuracao)
        if motivo:
            motivos.append(motivo)
    return tuple(motivos), tuple(adiadas)


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
        raise ValueError("desconto simples exige valor e prazo não negativos e base maior que zero")
    numerador = Decimal(valor_centavos) * Decimal(taxa_mensal_percentual) * Decimal(dias)
    denominador = Decimal(100) * Decimal(base_dias)
    return int((numerador / denominador).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _cnpj_sacado(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    del parametros, configuracao
    numeros = digitos(nota.doc_sacado)
    if len(numeros) != 14:
        return "CNPJ do sacado não tem 14 dígitos."
    if not cnpj_valido(nota.doc_sacado):
        return "CNPJ do sacado com dígito verificador inválido."
    return None


def _situacao(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    aceitas = parametros.get("situacoes_aceitas")
    if not isinstance(aceitas, list) or not aceitas:
        raise ValueError("SITUACAO_CADASTRAL_SACADO exige situacoes_aceitas")
    status = configuracao.situacao_cadastral.por_cnpj.get(digitos(nota.doc_sacado))
    if status is None:
        return configuracao.situacao_cadastral.mensagem_ausente
    if status not in aceitas:
        return f"Situação cadastral {status}. Este fundo aceita {_lista(aceitas)}."
    return None


def _tipo(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    del configuracao
    aceitos = parametros.get("tipos_aceitos")
    if not isinstance(aceitos, list) or not aceitos:
        raise ValueError("TIPO_RECEBIVEL exige tipos_aceitos")
    if nota.tipo_recebivel in aceitos:
        return None
    return f"Tipo {nota.tipo_recebivel}. Este fundo compra {_lista(aceitos)}."


def _valor_minimo(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    del configuracao
    minimo = _numero_para_centavos(parametros["valor_minimo"])
    if nota.valor_centavos >= minimo:
        return None
    return f"Valor de {_reais(nota.valor_centavos)}. O mínimo deste fundo é {_reais(minimo)}."


def _nao_vencida(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    del parametros
    operacao = _operacao(configuracao)
    if nota.vencimento >= operacao:
        return None
    return (
        f"Vencida em {nota.vencimento.strftime('%d/%m/%Y')}. "
        f"A operação é em {operacao.strftime('%d/%m/%Y')}."
    )


def _prazo_maximo(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    maximo = parametros["prazo_maximo_dias"]
    if isinstance(maximo, bool) or not isinstance(maximo, int):
        raise ValueError("PRAZO_MAXIMO exige prazo_maximo_dias inteiro")
    dias = (nota.vencimento - _operacao(configuracao)).days
    if dias <= maximo:
        return None
    return f"Prazo de {dias} dias. O máximo é {maximo}."


def _prazo_minimo(nota: Nota, parametros: dict[str, Any], configuracao: Configuracao) -> str | None:
    minimo = parametros["prazo_minimo_dias"]
    if isinstance(minimo, bool) or not isinstance(minimo, int):
        raise ValueError("PRAZO_MINIMO exige prazo_minimo_dias inteiro")
    dias = (nota.vencimento - _operacao(configuracao)).days
    if dias >= minimo:
        return None
    return f"Prazo de {dias} dias. O mínimo é {minimo}."


def _operacao(configuracao: Configuracao):
    return datetime.strptime(configuracao.data_operacao, "%Y-%m-%d").date()


def _numero_para_centavos(valor: int | float) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError("parâmetro de valor não é numérico")
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _reais(centavos: int) -> str:
    sinal = "-" if centavos < 0 else ""
    reais, frac = divmod(abs(centavos), 100)
    milhar = f"{reais:,}".replace(",", ".")
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


_REGISTRO: dict[str, Callable[[Nota, dict[str, Any], Configuracao], str | None]] = {
    "CNPJ_SACADO_VALIDO": _cnpj_sacado,
    "SITUACAO_CADASTRAL_SACADO": _situacao,
    "TIPO_RECEBIVEL": _tipo,
    "VALOR_MINIMO": _valor_minimo,
    "NAO_VENCIDA": _nao_vencida,
    "PRAZO_MAXIMO": _prazo_maximo,
    "PRAZO_MINIMO": _prazo_minimo,
}
