import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.regras import cnpj_valido as valido, digitos, raiz


class CnpjTest(unittest.TestCase):
    def test_filiais_da_mesma_raiz(self) -> None:
        matriz = "58.206.002/0001-11"
        filial = "58.206.002/0003-83"
        self.assertTrue(valido(matriz))
        self.assertTrue(valido(filial))
        self.assertEqual(raiz(matriz), raiz(filial))
        self.assertEqual(raiz(matriz), "58206002")

    def test_rejeita_digito_e_sequencia(self) -> None:
        numeros = digitos("22.144.961/0001-02")
        self.assertTrue(valido(numeros))
        trocado = numeros[:-1] + ("0" if numeros[-1] != "0" else "1")
        self.assertFalse(valido(trocado))
        self.assertFalse(valido("00000000000000"))
        self.assertFalse(valido("123"))
