"""Lê o estoque uma vez e decide o lote da empresa, de cima para baixo."""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from antecipe.avaliar import avaliar_nota, digitos, raiz
from antecipe.configuracao import Configuracao, Validador, carregar, carregar_sacados
from antecipe.normalizar import COLUNAS, ErroLinha, Nota, ler_linha, ler_texto

CABECALHO = ";".join(COLUNAS)
_CADEADO = threading.Lock()


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
class Carteira:
    chaves: set[tuple[str, str, date]]
    totais: dict[str, int]
    grupos: dict[str, dict[str, int]]


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
    carteira: Path | None = None,
) -> ResultadoLote:
    inicio = time.perf_counter()
    try:
        if carteira is None:
            resultado, _aceitas = _decidir(caminho, configuracao, cadastro)
        else:
            with _CADEADO:
                memoria = ler_carteira(carteira)
                resultado, aceitas = _decidir(caminho, configuracao, cadastro, memoria)
                anexar_aceitas(carteira, aceitas)
    except Exception:
        _registrar_falha(inicio, registro)
        raise
    _registrar(resultado, int((time.perf_counter() - inicio) * 1000), registro)
    return resultado


def ler_carteira(caminho: Path) -> Carteira:
    notas = [nota for nota, _registro in _linhas_salvas(caminho)]
    chaves = {(digitos(nota.doc_cedente), nota.nu_documento, nota.vencimento) for nota in notas}
    totais, grupos = _totais(notas)
    return Carteira(chaves, totais, grupos)


def consultar_salvas(
    caminho: Path,
    busca: str = "",
    cedente: str = "",
    vencimento: str = "",
    registro: str = "",
    pagina: int = 1,
    tamanho: int = 50,
) -> dict[str, object]:
    tamanho_ok = tamanho if tamanho in (10, 20, 50, 100, 200) else 50
    pagina_ok = pagina if pagina > 0 else 1
    if not caminho.is_file():
        return {"pagina": pagina_ok, "tamanho": tamanho_ok, "total_lista": 0, "linhas": []}
    termo = busca.strip().casefold()
    cedente_ok = "".join(caractere for caractere in cedente if caractere.isdigit()) or cedente.strip().casefold()
    vencimento_ok = vencimento.strip()
    registro_ok = registro.strip()
    filtro = """
        (? = '' OR instr(lower(nu_documento), ?) > 0)
        AND (? = '' OR instr(lower(doc_cedente), ?) > 0 OR instr(cedente, ?) > 0)
        AND (? = '' OR instr(vencimento, ?) > 0)
        AND (? = '' OR instr(registro, ?) > 0)
    """
    argumentos = (
        termo, termo,
        cedente_ok, cedente_ok, cedente_ok,
        vencimento_ok, vencimento_ok,
        registro_ok, registro_ok,
    )
    with _banco(caminho) as conexao:
        total = conexao.execute(f"SELECT COUNT(*) FROM notas_aceitas WHERE {filtro}", argumentos).fetchone()[0]
        inicio = (pagina_ok - 1) * tamanho_ok
        linhas = conexao.execute(
            f"""
            SELECT nu_documento, doc_cedente, nome_sacado, vencimento, valor_centavos, registro
            FROM notas_aceitas
            WHERE {filtro}
            ORDER BY registro, nu_documento
            LIMIT ? OFFSET ?
            """,
            (*argumentos, tamanho_ok, inicio),
        ).fetchall()
    return {
        "pagina": pagina_ok,
        "tamanho": tamanho_ok,
        "total_lista": total,
        "linhas": [
            {
                "nu_documento": linha["nu_documento"],
                "cedente": linha["doc_cedente"],
                "sacado": linha["nome_sacado"],
                "vencimento": linha["vencimento"],
                "valor_centavos": linha["valor_centavos"],
                "registro": linha["registro"],
            }
            for linha in linhas
        ],
    }


def anexar_aceitas(caminho: Path, notas: list) -> None:
    if not notas:
        return
    registro = date.today().strftime("%d/%m/%Y")
    with _banco(caminho) as conexao:
        conexao.executemany(
            """
            INSERT OR IGNORE INTO notas_aceitas (
                cedente, nu_documento, vencimento, nome_fundo, doc_fundo, nome_cedente, doc_cedente,
                nome_sacado, doc_sacado, tipo_recebivel, valor_centavos, aquisicao, registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    digitos(nota.doc_cedente),
                    nota.nu_documento,
                    nota.vencimento.strftime("%d/%m/%Y"),
                    nota.nome_fundo,
                    nota.doc_fundo,
                    nota.nome_cedente,
                    nota.doc_cedente,
                    nota.nome_sacado,
                    nota.doc_sacado,
                    nota.tipo_recebivel,
                    nota.valor_centavos,
                    nota.aquisicao.strftime("%d/%m/%Y"),
                    registro,
                )
                for nota in notas
            ],
        )


@contextmanager
def _banco(caminho: Path):
    conexao = _conectar(caminho)
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def _conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS notas_aceitas (
            cedente TEXT NOT NULL,
            nu_documento TEXT NOT NULL,
            vencimento TEXT NOT NULL,
            nome_fundo TEXT NOT NULL,
            doc_fundo TEXT NOT NULL,
            nome_cedente TEXT NOT NULL,
            doc_cedente TEXT NOT NULL,
            nome_sacado TEXT NOT NULL,
            doc_sacado TEXT NOT NULL,
            tipo_recebivel TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL,
            aquisicao TEXT NOT NULL,
            registro TEXT NOT NULL,
            PRIMARY KEY (cedente, nu_documento, vencimento)
        )
        """
    )
    return conexao


def _linhas_salvas(caminho: Path) -> list[tuple[Nota, str]]:
    if not caminho.is_file():
        return []
    with _banco(caminho) as conexao:
        linhas = conexao.execute(
            """
            SELECT nome_fundo, doc_fundo, nome_cedente, doc_cedente, nome_sacado, doc_sacado,
                   nu_documento, tipo_recebivel, valor_centavos, vencimento, aquisicao, registro
            FROM notas_aceitas
            """
        ).fetchall()
    salvas: list[tuple[Nota, str]] = []
    for linha in linhas:
        nota = Nota(
            nome_fundo=linha["nome_fundo"],
            doc_fundo=linha["doc_fundo"],
            nome_cedente=linha["nome_cedente"],
            doc_cedente=linha["doc_cedente"],
            nome_sacado=linha["nome_sacado"],
            doc_sacado=linha["doc_sacado"],
            nu_documento=linha["nu_documento"],
            tipo_recebivel=linha["tipo_recebivel"],
            valor_centavos=linha["valor_centavos"],
            vencimento=datetime.strptime(linha["vencimento"], "%d/%m/%Y").date(),
            aquisicao=datetime.strptime(linha["aquisicao"], "%d/%m/%Y").date(),
        )
        salvas.append((nota, linha["registro"]))
    return salvas


def _decidir(
    caminho: Path,
    configuracao: Configuracao,
    cadastro: dict[str, str] | None,
    carteira: Carteira | None = None,
) -> tuple[ResultadoLote, list]:
    notas = list(_notas_ou_erro(caminho))
    recusados = carregar_sacados()
    totais, grupos = _totais(notas)
    if carteira is not None:
        _somar_carteira(totais, grupos, carteira)
    regra = next(
        (item for item in configuracao.validadores if item.ativo and item.codigo == "CONCENTRACAO_MAXIMA_SACADO"),
        None,
    )
    vistas: set[tuple[str, str, date]] = set() if carteira is None else set(carteira.chaves)
    linhas: list[LinhaLote] = []
    aceitas: list = []
    soma = 0
    face_recusado = 0
    for nota_ou_erro in notas:
        if isinstance(nota_ou_erro, ErroLinha):
            linhas.append(LinhaLote("", (str(nota_ou_erro),), None))
            continue
        nota = nota_ou_erro
        resultado = avaliar_nota(nota, configuracao, cadastro, recusados)
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
            aceitas.append(nota)
        else:
            face_recusado += nota.valor_centavos
        linhas.append(LinhaLote(nota.nu_documento, tuple(motivos), liquido, tuple(codigos)))
    return ResultadoLote(tuple(linhas), soma, face_recusado), aceitas


def _somar_carteira(totais: dict[str, int], grupos: dict[str, dict[str, int]], carteira: Carteira) -> None:
    for fundo, valor in carteira.totais.items():
        totais[fundo] = totais.get(fundo, 0) + valor
    for fundo, por_raiz in carteira.grupos.items():
        destino = grupos.setdefault(fundo, {})
        for grupo, valor in por_raiz.items():
            destino[grupo] = destino.get(grupo, 0) + valor


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
    _escrever(
        {
            "id": uuid.uuid4().hex[:12],
            "duracao_ms": duracao_ms,
            "linhas": len(resultado.linhas),
            "aceitas": resultado.aceitas,
            "recusadas": resultado.recusadas,
            "codigos": dict(sorted(contagem.items())),
            "resultado": "ok",
        },
        destino,
    )


def _registrar_falha(inicio: float, destino: Path | None) -> None:
    _escrever(
        {
            "id": uuid.uuid4().hex[:12],
            "duracao_ms": int((time.perf_counter() - inicio) * 1000),
            "linhas": 0,
            "aceitas": 0,
            "recusadas": 0,
            "codigos": {},
            "resultado": "erro",
        },
        destino,
    )


def _escrever(evento: dict[str, object], destino: Path | None) -> None:
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
