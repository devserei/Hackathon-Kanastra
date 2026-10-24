import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.normalizar import ValorInvalido, para_centavos
from antecipe.regras import _reais as formatar_reais


class DinheiroTest(unittest.TestCase):
    def test_virgula_e_milhar(self) -> None:
        self.assertEqual(para_centavos("2278,08"), 227808)
        self.assertEqual(para_centavos("2.278,08"), 227808)
        self.assertEqual(para_centavos("100"), 10000)
        self.assertEqual(para_centavos("99,99"), 9999)
        self.assertEqual(para_centavos("100,00"), 10000)

    def test_rejeita_texto(self) -> None:
        with self.assertRaises(ValorInvalido):
            para_centavos("abc")

    def test_formato_brasileiro(self) -> None:
        self.assertEqual(formatar_reais(9999), "R$ 99,99")
        self.assertEqual(formatar_reais(10000), "R$ 100,00")
        self.assertEqual(formatar_reais(100000), "R$ 1.000,00")
