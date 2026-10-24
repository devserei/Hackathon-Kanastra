"""Recebe o CSV do lote e devolve a mesma decisão de lote.py."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from antecipe.configuracao import carregar
from antecipe.lote import ResultadoLote, carregar_cadastro, processar
from antecipe.normalizar import CodificacaoIncompativel, ErroLinha

RAIZ = Path(__file__).resolve().parents[2]
EXEMPLO = RAIZ / "exemplos" / "lote_novo.csv"


def criar_aplicacao(cadastro: dict[str, str] | None = None) -> FastAPI:
    situacao = carregar_cadastro(RAIZ / "config" / "cnpj_situacao_mock.csv") if cadastro is None else cadastro
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
    async def receber_lote(arquivo: UploadFile = File(...)) -> dict[str, object]:
        conteudo = await arquivo.read()
        if not conteudo.strip():
            raise HTTPException(status_code=400, detail="O arquivo do lote está vazio.")
        temporario = _gravar(conteudo)
        try:
            resultado = processar(temporario, carregar(RAIZ), situacao)
        except CodificacaoIncompativel as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroLinha as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        finally:
            temporario.unlink(missing_ok=True)
        return _json(resultado)

    @aplicacao.post("/lotes/exemplo")
    def lote_exemplo() -> dict[str, object]:
        if not EXEMPLO.is_file():
            raise HTTPException(status_code=404, detail="Lote de exemplo ausente.")
        try:
            resultado = processar(EXEMPLO, carregar(RAIZ), situacao)
        except CodificacaoIncompativel as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        except ErroLinha as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        return _json(resultado)

    return aplicacao


def _gravar(conteudo: bytes) -> Path:
    descritor, nome = tempfile.mkstemp(suffix=".csv")
    try:
        os.write(descritor, conteudo)
    finally:
        os.close(descritor)
    return Path(nome)


def _json(resultado: ResultadoLote) -> dict[str, object]:
    return {
        "aceitas": resultado.aceitas,
        "recusadas": resultado.recusadas,
        "total_liquido_centavos": resultado.total_liquido_centavos,
        "total_face_recusado_centavos": resultado.total_face_recusado_centavos,
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


app = criar_aplicacao()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
