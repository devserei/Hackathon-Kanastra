import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.normalizar import COLUNAS
from antecipe.servidor import criar_aplicacao

FUNDO = "92.234.400/0001-80"


def _csv(*linhas: str) -> bytes:
    texto = ";".join(COLUNAS) + "\n" + "\n".join(linhas) + "\n"
    return texto.encode("utf-8")


def _linha(**trocas: str) -> str:
    campos = {
        "NOME_FUNDO": "ANTECIPE FIDC",
        "DOC_FUNDO": FUNDO,
        "NOME_CEDENTE": "CEDENTE",
        "DOC_CEDENTE": "10.062.050/0001-57",
        "NOME_SACADO": "SACADO",
        "DOC_SACADO": "58.206.002/0001-11",
        "NU_DOCUMENTO": "NOVA-1",
        "TIPO_RECEBIVEL": "Duplicata",
        "VALOR_NOMINAL": "100,00",
        "DATA_VENCIMENTO_ORIGINAL": "23/11/2026",
        "DATA_AQUISICAO": "24/10/2026",
    }
    campos.update(trocas)
    return ";".join(campos[coluna] for coluna in COLUNAS)


class ServidorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pasta = tempfile.TemporaryDirectory()
        carteira = Path(self.pasta.name) / "antecipe.db"
        self.cliente = TestClient(criar_aplicacao({}, carteira))

    def tearDown(self) -> None:
        self.pasta.cleanup()

    def test_devolve_a_decisao_do_lote(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="BOA", VALOR_NOMINAL="100,00", DOC_SACADO="01.000.171/0001-83"),
            _linha(NU_DOCUMENTO="GRANDE", VALOR_NOMINAL="1000,00", DOC_SACADO="01.026.553/0001-86"),
        )
        resposta = self.cliente.post("/lotes", files={"arquivo": ("lote.csv", lote, "text/csv")})
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(corpo["aceitas"], 1)
        self.assertEqual(corpo["recusadas"], 1)
        self.assertEqual(corpo["total_liquido_centavos"], 9800)
        self.assertEqual(corpo["total_face_recusado_centavos"], 100_000)
        self.assertTrue(corpo["linhas"][0]["aceita"])
        self.assertIn("CONCENTRACAO_MAXIMA_SACADO", corpo["linhas"][1]["codigos"])

    def test_segunda_consulta_recusa_a_mesma_nota(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="OUTRA", VALOR_NOMINAL="100,00", DOC_SACADO="01.000.171/0001-83"),
            _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
        )
        arquivos = {"arquivo": ("lote.csv", lote, "text/csv")}
        primeira = self.cliente.post("/lotes", files=arquivos)
        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(primeira.json()["aceitas"], 1)
        segunda = self.cliente.post("/lotes", files=arquivos)
        self.assertEqual(segunda.status_code, 200)
        outra = next(linha for linha in segunda.json()["linhas"] if linha["nu_documento"] == "OUTRA")
        self.assertIn("já foi adquirida", outra["motivos"][0])

    def test_estoque_nao_entra_na_carteira(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="OUTRA", VALOR_NOMINAL="100,00", DOC_SACADO="01.000.171/0001-83"),
            _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
        )
        arquivos = {"arquivo": ("estoque_antecipe.csv", lote, "text/csv")}
        primeira = self.cliente.post("/lotes", files=arquivos)
        segunda = self.cliente.post("/lotes", files=arquivos)
        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(primeira.json()["aceitas"], 1)
        self.assertEqual(segunda.json()["aceitas"], 1)
        self.assertFalse((Path(self.pasta.name) / "antecipe.db").exists())

    def test_arquivo_vazio(self) -> None:
        resposta = self.cliente.post("/lotes", files={"arquivo": ("lote.csv", b"   ", "text/csv")})
        self.assertEqual(resposta.status_code, 400)

    def test_recusa_latin1(self) -> None:
        resposta = self.cliente.post(
            "/lotes",
            files={"arquivo": ("lote.csv", "INDÚSTRIA".encode("latin-1"), "text/csv")},
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("UTF-8", resposta.json()["detail"])


    def test_a_pagina_nao_traz_o_lote_inteiro(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="BOA", VALOR_NOMINAL="100,00", DOC_SACADO="01.000.171/0001-83"),
            _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
        )
        resposta = self.cliente.post(
            "/lotes",
            files={"arquivo": ("lote.csv", lote, "text/csv")},
            params={"pagina": 1, "tamanho": 10, "vista": "aceitas"},
        )
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(corpo["aceitas"], 1)
        self.assertEqual(corpo["total_lista"], 1)
        self.assertEqual(len(corpo["linhas"]), 1)
