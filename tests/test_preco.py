import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.avaliar import desconto_simples


class PrecoTest(unittest.TestCase):
    def test_trinta_dias_em_mil_reais(self) -> None:
        desconto = desconto_simples(100_000, 30, "2.0", 30)
        self.assertEqual(desconto, 2_000)
        self.assertEqual(100_000 - desconto, 98_000)

    def test_um_dia_arredonda_meio_centavo_para_cima(self) -> None:
        self.assertEqual(desconto_simples(100_000, 1, "2.0", 30), 67)

    def test_prazo_zero_nao_desconta(self) -> None:
        self.assertEqual(desconto_simples(100_000, 0, "2.0", 30), 0)

    def test_exemplo_da_primeira_linha(self) -> None:
        self.assertEqual(desconto_simples(227_808, 163, "2.0", 30), 24_755)
