import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.consulta import consultar
from antecipe.lote import LinhaLote, ResultadoLote


def _lote() -> ResultadoLote:
    linhas = (
        LinhaLote("A", (), 10_000),
        LinhaLote("B", (), 50_000),
        LinhaLote("C", (), 20_000),
        LinhaLote("X", ("Tipo Cheque.",), None, ("TIPO_RECEBIVEL",)),
    )
    return ResultadoLote(linhas, 80_000, 0)


class ConsultaAceitasTest(unittest.TestCase):
    def test_faixa_de_liquido(self) -> None:
        pagina = consultar(_lote(), valor_min=15_000, valor_max=40_000)
        self.assertEqual([linha["nu_documento"] for linha in pagina["linhas"]], ["C"])
        self.assertEqual(pagina["total_lista"], 1)

    def test_ordem_crescente_e_decrescente(self) -> None:
        crescente = consultar(_lote(), ordem="crescente")
        decrescente = consultar(_lote(), ordem="decrescente")
        self.assertEqual([linha["nu_documento"] for linha in crescente["linhas"]], ["A", "C", "B"])
        self.assertEqual([linha["nu_documento"] for linha in decrescente["linhas"]], ["B", "C", "A"])

    def test_faixa_nao_mexe_nas_recusadas(self) -> None:
        pagina = consultar(_lote(), vista="recusadas", valor_min=1, valor_max=2, ordem="crescente")
        self.assertEqual([linha["nu_documento"] for linha in pagina["linhas"]], ["X"])
