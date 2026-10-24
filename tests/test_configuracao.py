import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from antecipe.configuracao import ConfiguracaoInvalida, carregar


class ConfiguracaoOficialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.configuracao = carregar(RAIZ)

    def test_abre_o_fundo_oficial(self) -> None:
        self.assertEqual(self.configuracao.fundo_nome, "ANTECIPE FIDC")
        self.assertEqual(self.configuracao.fundo_cnpj, "92.234.400/0001-80")
        self.assertEqual(self.configuracao.metodo, "DESCONTO_SIMPLES")
        self.assertEqual(self.configuracao.taxa_mensal_percentual, "2.0")
        self.assertEqual(self.configuracao.base_dias, 30)

    def test_le_os_validadores_do_json(self) -> None:
        por_codigo = {item.codigo: item for item in self.configuracao.validadores}
        self.assertFalse(por_codigo["PRAZO_MINIMO"].ativo)
        self.assertEqual(por_codigo["VALOR_MINIMO"].parametros["valor_minimo"], 100.0)
        self.assertEqual(por_codigo["CONCENTRACAO_MAXIMA_SACADO"].parametros["percentual_maximo"], 10.0)
        self.assertEqual(len(self.configuracao.ativos()), 7)


class ConfiguracaoInvalidaTest(unittest.TestCase):
    def test_rejeita_json_ausente(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ConfiguracaoInvalida):
                carregar(Path(pasta))
