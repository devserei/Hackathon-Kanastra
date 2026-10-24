import sys
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
        self.cliente = TestClient(criar_aplicacao({}))

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


class LoteExemploTest(unittest.TestCase):
    def test_junta_o_exemplo_com_o_estoque(self) -> None:
        cliente = TestClient(criar_aplicacao())
        resposta = cliente.post("/lotes/exemplo")
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        por_numero = {linha["nu_documento"]: linha for linha in corpo["linhas"]}
        self.assertTrue(por_numero["NOVA-100"]["aceita"])
        self.assertEqual(por_numero["NOVA-100"]["liquido_centavos"], 49000)
        self.assertIn("Cheque", por_numero["NOVA-CHEQUE"]["motivos"][0])
        self.assertIn("mínimo", por_numero["NOVA-BAIXA"]["motivos"][0])
        self.assertIn("Prazo", por_numero["NOVA-PRAZO"]["motivos"][0])
        self.assertIn("BAIXADA", por_numero["NOVA-SIT"]["motivos"][0])
        self.assertIn("limite", por_numero["NOVA-GRUPO"]["motivos"][0])
        self.assertIn("já foi adquirida", por_numero["DUP-1"]["motivos"][0])
        self.assertEqual(corpo["aceitas"], 2)
        self.assertEqual(corpo["total_liquido_centavos"], 58800)
        self.assertEqual(corpo["total_face_recusado_centavos"], 445_000)
