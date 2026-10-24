"""Recorta o lote já classificado para uma página da tela."""

from __future__ import annotations

from antecipe.lote import LinhaLote, ResultadoLote

TAMANHOS = (10, 20, 50, 100, 200)


def _tipo(linha: LinhaLote) -> bool:
    return "TIPO_RECEBIVEL" in linha.codigos


def _valor(linha: LinhaLote) -> bool:
    return "VALOR_MINIMO" in linha.codigos


def _prazo(linha: LinhaLote) -> bool:
    return "PRAZO_MAXIMO" in linha.codigos


def _cadastro(linha: LinhaLote) -> bool:
    return "SITUACAO_CADASTRAL_SACADO" in linha.codigos


def _grupo(linha: LinhaLote) -> bool:
    return "CONCENTRACAO_MAXIMA_SACADO" in linha.codigos


def _duplicata(linha: LinhaLote) -> bool:
    return any("já foi adquirida" in motivo for motivo in linha.motivos)


FILTROS = {
    "todas": lambda linha: True,
    "tipo": _tipo,
    "valor": _valor,
    "prazo": _prazo,
    "cadastro": _cadastro,
    "grupo": _grupo,
    "duplicata": _duplicata,
}


def consultar(
    resultado: ResultadoLote,
    vista: str = "aceitas",
    filtro: str = "todas",
    busca: str = "",
    pagina: int = 1,
    tamanho: int = 50,
    valor_min: int | None = None,
    valor_max: int | None = None,
    ordem: str = "",
) -> dict[str, object]:
    vista_ok = vista if vista in ("aceitas", "recusadas") else "aceitas"
    filtro_ok = filtro if filtro in FILTROS else "todas"
    tamanho_ok = tamanho if tamanho in TAMANHOS else 50
    pagina_ok = pagina if pagina > 0 else 1
    termo = busca.strip().casefold()
    recusadas = [linha for linha in resultado.linhas if not linha.aceita]
    contagens = {
        nome: sum(1 for linha in recusadas if regra(linha))
        for nome, regra in FILTROS.items()
    }
    if vista_ok == "aceitas":
        lista = [
            linha
            for linha in resultado.linhas
            if linha.aceita and _busca(linha, termo) and _faixa(linha, valor_min, valor_max)
        ]
        lista = _ordenar(lista, ordem)
    else:
        regra = FILTROS[filtro_ok]
        lista = [linha for linha in recusadas if regra(linha) and _busca(linha, termo)]
    inicio = (pagina_ok - 1) * tamanho_ok
    return {
        "vista": vista_ok,
        "filtro": filtro_ok,
        "pagina": pagina_ok,
        "tamanho": tamanho_ok,
        "total_lista": len(lista),
        "contagens": contagens,
        "linhas": [_json_linha(linha) for linha in lista[inicio : inicio + tamanho_ok]],
    }


def _busca(linha: LinhaLote, termo: str) -> bool:
    if not termo:
        return True
    return termo in linha.nu_documento.casefold()


def _faixa(linha: LinhaLote, minimo: int | None, maximo: int | None) -> bool:
    if minimo is None and maximo is None:
        return True
    valor = linha.liquido_centavos
    if valor is None:
        return False
    if minimo is not None and valor < minimo:
        return False
    if maximo is not None and valor > maximo:
        return False
    return True


def _ordenar(lista: list[LinhaLote], ordem: str) -> list[LinhaLote]:
    if ordem not in ("crescente", "decrescente"):
        return lista
    return sorted(
        lista,
        key=lambda linha: linha.liquido_centavos if linha.liquido_centavos is not None else -1,
        reverse=ordem == "decrescente",
    )


def _json_linha(linha: LinhaLote) -> dict[str, object]:
    return {
        "nu_documento": linha.nu_documento,
        "aceita": linha.aceita,
        "motivos": list(linha.motivos),
        "codigos": list(linha.codigos),
        "liquido_centavos": linha.liquido_centavos,
    }
