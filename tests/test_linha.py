import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.normalizar import COLUNAS, CodificacaoIncompativel, ErroLinha, ler_linha, ler_texto

RAIZ = Path(__file__).resolve().parents[1]


def _linha(**trocas: str) -> str:
    campos = {
        "NOME_FUNDO": "ANTECIPE FIDC",
        "DOC_FUNDO": "92.234.400/0001-80",
        "NOME_CEDENTE": "NLR INDÚSTRIA DE ESTOFADOS LTDA ME",
        "DOC_CEDENTE": "10.062.050/0001-57",
        "NOME_SACADO": "TECIDOS SANTARÉM LTDA ME",
        "DOC_SACADO": "22.144.961/0001-02",
        "NU_DOCUMENTO": "725714",
        "TIPO_RECEBIVEL": "Duplicata",
        "VALOR_NOMINAL": "2278,08",
        "DATA_VENCIMENTO_ORIGINAL": "07/10/2026",
        "DATA_AQUISICAO": "27/04/2026",
    }
    campos.update(trocas)
    return ";".join(campos[coluna] for coluna in COLUNAS)


class LinhaTest(unittest.TestCase):
    def test_le_decimal_virgula_e_data_brasileira(self) -> None:
        nota = ler_linha(_linha())
        self.assertEqual(nota.nu_documento, "725714")
        self.assertEqual(nota.valor_centavos, 227808)
        self.assertEqual(nota.vencimento, date(2026, 10, 7))
        self.assertEqual(nota.aquisicao, date(2026, 4, 27))

    def test_preserva_zeros_e_hifen(self) -> None:
        self.assertEqual(ler_linha(_linha(NU_DOCUMENTO="000351153")).nu_documento, "000351153")
        self.assertEqual(ler_linha(_linha(NU_DOCUMENTO="1-759172")).nu_documento, "1-759172")

    def test_aceita_ponto_de_milhar(self) -> None:
        self.assertEqual(ler_linha(_linha(VALOR_NOMINAL="2.278,08")).valor_centavos, 227808)

    def test_data_ruim_e_erro_de_linha(self) -> None:
        with self.assertRaises(ErroLinha):
            ler_linha(_linha(DATA_VENCIMENTO_ORIGINAL="32/10/2026"))

    def test_valor_ruim_e_erro_de_linha(self) -> None:
        with self.assertRaises(ErroLinha):
            ler_linha(_linha(VALOR_NOMINAL="abc"))

    def test_colunas_incompletas(self) -> None:
        with self.assertRaises(ErroLinha):
            ler_linha("só;tres;campos")

    def test_primeira_linha_do_estoque(self) -> None:
        caminho = RAIZ / "data" / "estoque_antecipe.csv"
        if not caminho.is_file():
            self.skipTest("arquivo do Notion ausente")
        texto = ler_texto(caminho)
        nota = ler_linha(texto.splitlines()[1])
        self.assertEqual(nota.nu_documento, "725714")
        self.assertEqual(nota.doc_sacado, "22.144.961/0001-02")
        self.assertEqual(nota.valor_centavos, 227808)
        self.assertIn("INDÚSTRIA", texto)

    def test_utf8_com_bom_preserva_acento(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "amostra.csv"
            caminho.write_bytes("INDÚSTRIA".encode("utf-8-sig"))
            self.assertEqual(ler_texto(caminho), "INDÚSTRIA")

    def test_latin1_e_recusado(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "amostra.csv"
            caminho.write_bytes("INDÚSTRIA".encode("latin-1"))
            with self.assertRaises(CodificacaoIncompativel):
                ler_texto(caminho)
