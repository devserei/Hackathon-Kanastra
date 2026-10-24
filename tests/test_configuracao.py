import json
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

    def test_preserva_validadores_inativos(self) -> None:
        codigos = [item.codigo for item in self.configuracao.validadores]
        self.assertEqual(
            codigos,
            [
                "CNPJ_SACADO_VALIDO",
                "SITUACAO_CADASTRAL_SACADO",
                "TIPO_RECEBIVEL",
                "VALOR_MINIMO",
                "NAO_VENCIDA",
                "PRAZO_MAXIMO",
                "CONCENTRACAO_MAXIMA_SACADO",
                "PRAZO_MINIMO",
                "CONCENTRACAO_MAXIMA_CEDENTE",
            ],
        )
        ativos = [item.codigo for item in self.configuracao.validadores_ativos()]
        self.assertNotIn("PRAZO_MINIMO", ativos)
        self.assertNotIn("CONCENTRACAO_MAXIMA_CEDENTE", ativos)
        self.assertEqual(len(ativos), 7)

    def test_le_parametros_do_json(self) -> None:
        por_codigo = {item.codigo: item.parametros for item in self.configuracao.validadores}
        self.assertEqual(por_codigo["VALOR_MINIMO"]["valor_minimo"], 100.0)
        self.assertEqual(por_codigo["PRAZO_MAXIMO"]["prazo_maximo_dias"], 180)
        self.assertEqual(por_codigo["CONCENTRACAO_MAXIMA_SACADO"]["percentual_maximo"], 10.0)
        self.assertEqual(por_codigo["CONCENTRACAO_MAXIMA_SACADO"]["agrupamento"], "RAIZ_CNPJ")
        self.assertEqual(por_codigo["PRAZO_MINIMO"]["prazo_minimo_dias"], 30)
        self.assertEqual(self.configuracao.precificacao.metodo, "DESCONTO_SIMPLES")
        self.assertEqual(self.configuracao.precificacao.taxa_mensal_percentual, "2.0")
        self.assertEqual(self.configuracao.precificacao.base_dias, 30)

    def test_trava_o_contrato_operacional(self) -> None:
        self.assertEqual(self.configuracao.data_operacao, "2026-10-24")
        self.assertEqual(
            self.configuracao.chave_recebivel,
            ("doc_cedente", "nu_documento", "data_vencimento"),
        )
        self.assertTrue(self.configuracao.preservar_numero_documento)
        self.assertTrue(self.configuracao.valor_fora_da_chave)
        self.assertEqual(self.configuracao.dinheiro.unidade, "centavos")
        self.assertEqual(self.configuracao.dinheiro.arredondamento, "HALF_UP")
        self.assertTrue(self.configuracao.prazo.vence_no_dia_entra)
        self.assertTrue(self.configuracao.concentracao.inclui_notas_vencidas)
        self.assertFalse(self.configuracao.concentracao.nota_recusada_por_outra_regra_ocupa_limite)
        self.assertEqual(self.configuracao.concentracao.ordem_do_lote, "arquivo_de_cima_para_baixo")
        self.assertEqual(self.configuracao.situacao_cadastral.ausente, "recusar")
        self.assertEqual(
            self.configuracao.situacao_cadastral.mensagem_ausente,
            "Situação cadastral não encontrada",
        )
        self.assertEqual(self.configuracao.situacao_cadastral.por_cnpj, {})


class ConfiguracaoInvalidaTest(unittest.TestCase):
    def test_rejeita_json_ausente(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ConfiguracaoInvalida):
                carregar(Path(pasta))

    def test_rejeita_cnpj_mascarado_no_cadastro(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            base = Path(pasta)
            _copiar_config_oficial(base)
            (base / "config" / "situacao_cadastral.json").write_text(
                json.dumps({"por_cnpj": {"92.234.400/0001-80": "ATIVA"}}),
                encoding="utf-8",
            )
            with self.assertRaises(ConfiguracaoInvalida):
                carregar(base)


def _copiar_config_oficial(base: Path) -> None:
    destino = base / "config"
    destino.mkdir()
    for nome in ("validadores_antecipe.json", "operacao.json", "situacao_cadastral.json"):
        (destino / nome).write_text((RAIZ / "config" / nome).read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
