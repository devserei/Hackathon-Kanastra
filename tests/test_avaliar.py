import sys
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.avaliar import CodigoDesconhecido, avaliar_nota
from antecipe.configuracao import Validador, carregar
from antecipe.normalizar import Nota
from antecipe.regras import digitos

RAIZ = Path(__file__).resolve().parents[1]
OPERACAO = date(2026, 10, 24)
CNPJ = "22.144.961/0001-02"


def _nota(**trocas: object) -> Nota:
    dados: dict[str, object] = {
        "nome_fundo": "ANTECIPE FIDC",
        "doc_fundo": "92.234.400/0001-80",
        "nome_cedente": "CEDENTE",
        "doc_cedente": "10.062.050/0001-57",
        "nome_sacado": "SACADO",
        "doc_sacado": CNPJ,
        "nu_documento": "725714",
        "tipo_recebivel": "Duplicata",
        "valor_centavos": 100_000,
        "vencimento": OPERACAO + timedelta(days=30),
        "aquisicao": date(2026, 4, 27),
    }
    dados.update(trocas)
    return Nota(**dados)  # type: ignore[arg-type]


class AvaliarNotaTest(unittest.TestCase):
    def setUp(self) -> None:
        base = carregar(RAIZ)
        self.configuracao = replace(
            base,
            situacao_cadastral=replace(
                base.situacao_cadastral,
                por_cnpj={digitos(CNPJ): "ATIVA"},
            ),
        )

    def test_valor_minimo_exato_entra(self) -> None:
        resultado = avaliar_nota(_nota(valor_centavos=10_000), self.configuracao)
        self.assertEqual(resultado.motivos, ())
        self.assertIsNotNone(resultado.liquido_centavos)

    def test_abaixo_do_minimo(self) -> None:
        resultado = avaliar_nota(_nota(valor_centavos=9_999), self.configuracao)
        self.assertEqual(
            resultado.motivos,
            ("Valor de R$ 99,99. O mínimo deste fundo é R$ 100,00.",),
        )
        self.assertIsNone(resultado.liquido_centavos)

    def test_prazo_zero_entra_sem_desconto(self) -> None:
        resultado = avaliar_nota(_nota(vencimento=OPERACAO, valor_centavos=100_000), self.configuracao)
        self.assertFalse(resultado.recusada)
        self.assertEqual(resultado.desconto_centavos, 0)
        self.assertEqual(resultado.liquido_centavos, 100_000)

    def test_prazo_180_entra(self) -> None:
        resultado = avaliar_nota(
            _nota(vencimento=OPERACAO + timedelta(days=180), valor_centavos=100_000),
            self.configuracao,
        )
        self.assertFalse(resultado.recusada)
        self.assertEqual(resultado.desconto_centavos, 12_000)
        self.assertEqual(resultado.liquido_centavos, 88_000)

    def test_prazo_181_sai(self) -> None:
        resultado = avaliar_nota(
            _nota(vencimento=OPERACAO + timedelta(days=181)),
            self.configuracao,
        )
        self.assertEqual(resultado.motivos, ("Prazo de 181 dias. O máximo é 180.",))

    def test_cheque_sai(self) -> None:
        resultado = avaliar_nota(_nota(tipo_recebivel="Cheque"), self.configuracao)
        self.assertEqual(
            resultado.motivos,
            ("Tipo Cheque. Este fundo compra Duplicata e Duplicata de Serviço.",),
        )

    def test_cnpj_invalido(self) -> None:
        numeros = digitos(CNPJ)
        trocado = numeros[:-1] + ("0" if numeros[-1] != "0" else "1")
        resultado = avaliar_nota(_nota(doc_sacado=trocado), self.configuracao)
        self.assertIn("CNPJ do sacado com dígito verificador inválido.", resultado.motivos)

    def test_prazo_minimo_desligado_nao_recusa(self) -> None:
        nota = _nota(vencimento=OPERACAO + timedelta(days=10))
        self.assertFalse(avaliar_nota(nota, self.configuracao).recusada)
        ligados = tuple(
            replace(item, ativo=True) if item.codigo == "PRAZO_MINIMO" else item
            for item in self.configuracao.validadores
        )
        recusa = avaliar_nota(nota, replace(self.configuracao, validadores=ligados))
        self.assertEqual(recusa.motivos, ("Prazo de 10 dias. O mínimo é 30.",))

    def test_junta_motivos_independentes(self) -> None:
        resultado = avaliar_nota(
            _nota(
                tipo_recebivel="Cheque",
                valor_centavos=9_999,
                vencimento=date(2026, 10, 23),
            ),
            self.configuracao,
        )
        self.assertEqual(
            resultado.motivos,
            (
                "Tipo Cheque. Este fundo compra Duplicata e Duplicata de Serviço.",
                "Valor de R$ 99,99. O mínimo deste fundo é R$ 100,00.",
                "Vencida em 23/10/2026. A operação é em 24/10/2026.",
            ),
        )

    def test_codigo_desconhecido_interrompe(self) -> None:
        configuracao = replace(
            self.configuracao,
            validadores=self.configuracao.validadores + (Validador("REGRA_NOVA", True, {}),),
        )
        with self.assertRaises(CodigoDesconhecido):
            avaliar_nota(_nota(), configuracao)

    def test_concentracao_ativa_fica_para_a_carteira(self) -> None:
        resultado = avaliar_nota(_nota(), self.configuracao)
        self.assertEqual(resultado.regras_adiadas, ("CONCENTRACAO_MAXIMA_SACADO",))

    def test_sem_cadastro_informa_a_mensagem_do_contrato(self) -> None:
        resultado = avaliar_nota(_nota(), carregar(RAIZ))
        self.assertEqual(resultado.motivos, ("Situação cadastral não encontrada",))
