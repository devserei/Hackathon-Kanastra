"""Recebe o CSV do lote e devolve a mesma decisão de lote.py."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from antecipe.configuracao import carregar
from antecipe.consulta import consultar
from antecipe.lote import ResultadoLote, carregar_cadastro, consultar_salvas, processar
from antecipe.normalizar import CodificacaoIncompativel, ErroLinha

RAIZ = Path(__file__).resolve().parents[2]
CARTEIRA = RAIZ / "data" / "antecipe.db"
SEM_CARTEIRA = {"estoque_antecipe.csv", "lote_500k.csv", "lote_1m.csv"}
_LOTES: dict[str, ResultadoLote] = {}
_ORDEM: list[str] = []


def criar_aplicacao(cadastro: dict[str, str] | None = None, carteira: Path | None = None) -> FastAPI:
    situacao = carregar_cadastro(RAIZ / "config" / "cnpj_situacao_mock.csv") if cadastro is None else cadastro
    destino_carteira = CARTEIRA if carteira is None else carteira
    aplicacao = FastAPI(title="Antecipe")
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    @aplicacao.get("/saude")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    @aplicacao.get("/")
    def pagina() -> FileResponse:
        return FileResponse(RAIZ / "web" / "estatico" / "index.html")

    aplicacao.mount("/estatico", StaticFiles(directory=RAIZ / "web" / "estatico"), name="estatico")

    @aplicacao.post("/lotes")
    async def receber_lote(
        arquivo: UploadFile = File(...),
        pagina: int | None = None,
        tamanho: int = 50,
        vista: str = "aceitas",
        filtro: str = "todas",
        busca: str = "",
        valor_min: int | None = None,
        valor_max: int | None = None,
        ordem: str = "",
    ) -> dict[str, object]:
        conteudo = await arquivo.read()
        if not conteudo.strip():
            raise HTTPException(status_code=400, detail="O arquivo do lote está vazio.")
        temporario = _gravar(conteudo)
        try:
            resultado = processar(
                temporario,
                carregar(RAIZ),
                situacao,
                carteira=_carteira_do_envio(arquivo.filename, destino_carteira),
            )
        except CodificacaoIncompativel as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroLinha as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        finally:
            temporario.unlink(missing_ok=True)
        if pagina is None:
            return _json(resultado)
        return _pagina(resultado, pagina, tamanho, vista, filtro, busca, valor_min, valor_max, ordem)

    @aplicacao.get("/carteira")
    def ler_notas_salvas(
        pagina: int = 1,
        tamanho: int = 50,
        busca: str = "",
        cedente: str = "",
        vencimento: str = "",
        registro: str = "",
    ) -> dict[str, object]:
        try:
            return consultar_salvas(destino_carteira, busca, cedente, vencimento, registro, pagina, tamanho)
        except ErroLinha as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro

    @aplicacao.get("/lotes/{lote_id}")
    def ler_pagina(
        lote_id: str,
        pagina: int = 1,
        tamanho: int = 50,
        vista: str = "aceitas",
        filtro: str = "todas",
        busca: str = "",
        valor_min: int | None = None,
        valor_max: int | None = None,
        ordem: str = "",
    ) -> dict[str, object]:
        resultado = _LOTES.get(lote_id)
        if resultado is None:
            raise HTTPException(status_code=404, detail="Este lote não está mais na memória. Analise o arquivo de novo.")
        pagina_atual = consultar(
            resultado, vista, filtro, busca, pagina, tamanho, valor_min, valor_max, ordem
        )
        return {**_resumo(resultado), "id": lote_id, **pagina_atual}

    return aplicacao


def _carteira_do_envio(nome: str | None, destino: Path) -> Path | None:
    if Path(nome or "").name.casefold() in SEM_CARTEIRA:
        return None
    return destino


def _gravar(conteudo: bytes) -> Path:
    descritor, nome = tempfile.mkstemp(suffix=".csv")
    try:
        os.write(descritor, conteudo)
    finally:
        os.close(descritor)
    return Path(nome)


def _resumo(resultado: ResultadoLote) -> dict[str, object]:
    return {
        "aceitas": resultado.aceitas,
        "recusadas": resultado.recusadas,
        "total_liquido_centavos": resultado.total_liquido_centavos,
        "total_face_recusado_centavos": resultado.total_face_recusado_centavos,
    }


def _json(resultado: ResultadoLote) -> dict[str, object]:
    return {
        **_resumo(resultado),
        "linhas": [
            {
                "nu_documento": linha.nu_documento,
                "aceita": linha.aceita,
                "motivos": list(linha.motivos),
                "codigos": list(linha.codigos),
                "liquido_centavos": linha.liquido_centavos,
            }
            for linha in resultado.linhas
        ],
    }


def _pagina(
    resultado: ResultadoLote,
    pagina: int,
    tamanho: int,
    vista: str,
    filtro: str,
    busca: str,
    valor_min: int | None = None,
    valor_max: int | None = None,
    ordem: str = "",
) -> dict[str, object]:
    ident = uuid.uuid4().hex[:12]
    _LOTES[ident] = resultado
    _ORDEM.append(ident)
    while len(_ORDEM) > 3:
        _LOTES.pop(_ORDEM.pop(0), None)
    return {
        **_resumo(resultado),
        "id": ident,
        **consultar(resultado, vista, filtro, busca, pagina, tamanho, valor_min, valor_max, ordem),
    }


app = criar_aplicacao()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
