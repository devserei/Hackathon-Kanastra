import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antecipe.avaliar import CodigoDesconhecido
from antecipe.configuracao import Validador, carregar
from antecipe.lote import carregar_cadastro, montar, processar
from antecipe.normalizar import COLUNAS

RAIZ = Path(__file__).resolve().parents[1]
FUNDO = "92.234.400/0001-80"


def _csv(*linhas: str) -> Path:
    pasta = Path(tempfile.mkdtemp())
    caminho = pasta / "notas.csv"
    caminho.write_text(";".join(COLUNAS) + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def _linha(**trocas: str) -> str:
    campos = {
        "NOME_FUNDO": "ANTECIPE FIDC",
        "DOC_FUNDO": FUNDO,
        "NOME_CEDENTE": "CEDENTE",
        "DOC_CEDENTE": "10.062.050/0001-57",
        "NOME_SACADO": "SACADO",
        "DOC_SACADO": "01.000.171/0001-83",
        "NU_DOCUMENTO": "NOVA-1",
        "TIPO_RECEBIVEL": "Duplicata",
        "VALOR_NOMINAL": "100,00",
        "DATA_VENCIMENTO_ORIGINAL": "23/11/2026",
        "DATA_AQUISICAO": "24/10/2026",
    }
    campos.update(trocas)
    return ";".join(campos[coluna] for coluna in COLUNAS)


class LoteTest(unittest.TestCase):
    def test_classifica_o_arquivo(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="BOA", VALOR_NOMINAL="100,00"),
            _linha(NU_DOCUMENTO="BAIXA", VALOR_NOMINAL="50,00", DOC_SACADO="01.031.862/0001-44"),
            _linha(NU_DOCUMENTO="BOA", VALOR_NOMINAL="100,00"),
            _linha(NU_DOCUMENTO="GRANDE", VALOR_NOMINAL="2000,00", DOC_SACADO="01.026.553/0001-86"),
            _linha(
                NU_DOCUMENTO="PRAZO",
                DOC_SACADO="01.065.182/0001-41",
                DATA_AQUISICAO="01/01/2025",
                DATA_VENCIMENTO_ORIGINAL="01/01/2026",
            ),
            _linha(NU_DOCUMENTO="CHEQUE", TIPO_RECEBIVEL="Cheque", DOC_SACADO="01.104.610/0001-06"),
        )
        resultado = processar(lote, carregar(RAIZ))
        por_numero = {}
        for linha in resultado.linhas:
            por_numero.setdefault(linha.nu_documento, linha)
        self.assertTrue(por_numero["BOA"].aceita)
        self.assertEqual(por_numero["BOA"].liquido_centavos, 9_800)
        self.assertIn("mínimo", por_numero["BAIXA"].motivos[0])
        segunda = [linha for linha in resultado.linhas if linha.nu_documento == "BOA"][1]
        self.assertIn("já foi adquirida", segunda.motivos[0])
        self.assertIn("limite", por_numero["GRANDE"].motivos[0])
        self.assertIn("365", por_numero["PRAZO"].motivos[0])
        self.assertIn("Cheque", por_numero["CHEQUE"].motivos[0])
        self.assertEqual(resultado.total_face_recusado_centavos, 235_000)

    def test_cadastro_baixado_recusa(self) -> None:
        lote = _csv(
            _linha(NU_DOCUMENTO="BOA", VALOR_NOMINAL="500,00"),
            _linha(NU_DOCUMENTO="SIT", DOC_SACADO="03.601.302/0001-03", VALOR_NOMINAL="100,00"),
            _linha(NU_DOCUMENTO="BASE", DOC_SACADO="01.026.553/0001-86", VALOR_NOMINAL="5000,00"),
        )
        cadastro = carregar_cadastro(RAIZ / "config" / "cnpj_situacao_mock.csv")
        resultado = processar(lote, carregar(RAIZ), cadastro)
        sit = next(linha for linha in resultado.linhas if linha.nu_documento == "SIT")
        self.assertIn("SITUACAO_CADASTRAL_SACADO", sit.codigos)
        self.assertIn("não é aceita", sit.motivos[0])

    def test_estoque_publicado_bate_com_o_gabarito(self) -> None:
        gabarito = RAIZ / "data" / "resultado_esperado_100k.json"
        estoque = RAIZ / "data" / "estoque_antecipe.csv"
        if not gabarito.is_file() or not estoque.is_file():
            self.skipTest("arquivos do Notion ausentes")
        esperado = {item["linha"]: item for item in json.loads(gabarito.read_text(encoding="utf-8"))}
        cadastro = carregar_cadastro(RAIZ / "config" / "cnpj_situacao_mock.csv")
        resultado = processar(estoque, carregar(RAIZ), cadastro)
        self.assertEqual(len(resultado.linhas), len(esperado))
        for numero, linha in enumerate(resultado.linhas, start=2):
            item = esperado[numero]
            self.assertEqual(linha.nu_documento, item["id"])
            self.assertEqual(linha.aceita, item["status"] == "APROVADO", msg=f"linha {numero}")
            self.assertEqual(tuple(linha.codigos), tuple(item.get("barrado_por") or []), msg=f"linha {numero}")
        self.assertEqual(resultado.aceitas, 85_215)
        self.assertEqual(resultado.recusadas, 15_339)

    def test_log_guarda_contagem_e_nao_a_nota(self) -> None:
        destino = Path(tempfile.mkdtemp()) / "lotes.log"
        lote = _csv(_linha(NU_DOCUMENTO="DOC-SIGILOSO", DOC_SACADO="01.000.171/0001-83", VALOR_NOMINAL="500,00"))
        processar(lote, carregar(RAIZ), registro=destino)
        texto = destino.read_text(encoding="utf-8")
        registro = json.loads(texto)
        self.assertEqual(
            set(registro),
            {"id", "duracao_ms", "linhas", "aceitas", "recusadas", "codigos", "resultado"},
        )
        self.assertEqual(registro["resultado"], "ok")
        self.assertEqual(len(registro["id"]), 12)
        self.assertEqual(registro["linhas"], 1)
        self.assertNotIn("DOC-SIGILOSO", texto)
        self.assertNotIn("01.000.171", texto)
        self.assertNotIn("500,00", texto)

    def test_log_de_erro_nao_grava_a_linha(self) -> None:
        destino = Path(tempfile.mkdtemp()) / "lotes.log"
        lote = _csv(_linha(NU_DOCUMENTO="DOC-SIGILOSO", VALOR_NOMINAL="500,00"))
        configuracao = carregar(RAIZ)
        ruim = replace(
            configuracao,
            validadores=configuracao.validadores + (Validador("NAO_EXISTE", True, {}),),
        )
        with self.assertRaises(CodigoDesconhecido):
            processar(lote, ruim, registro=destino)
        texto = destino.read_text(encoding="utf-8")
        registro = json.loads(texto)
        self.assertEqual(registro["resultado"], "erro")
        self.assertEqual(registro["linhas"], 0)
        self.assertNotIn("DOC-SIGILOSO", texto)
        self.assertNotIn("500,00", texto)
        self.assertNotIn("NAO_EXISTE", texto)

    def test_consulta_notas_salvas_por_documento_cedente_e_vencimento(self) -> None:
        from datetime import date

        from antecipe.lote import consultar_salvas

        pasta = Path(tempfile.mkdtemp())
        carteira = pasta / "antecipe.db"
        processar(
            _csv(
                _linha(NU_DOCUMENTO="OUTRA", VALOR_NOMINAL="100,00"),
                _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
            ),
            carregar(RAIZ),
            carteira=carteira,
        )
        pagina = consultar_salvas(carteira, busca="OUTRA")
        self.assertEqual(pagina["total_lista"], 1)
        self.assertEqual(pagina["linhas"][0]["cedente"], "10.062.050/0001-57")
        self.assertEqual(pagina["linhas"][0]["vencimento"], "23/11/2026")
        self.assertEqual(pagina["linhas"][0]["registro"], date.today().strftime("%d/%m/%Y"))
        self.assertEqual(consultar_salvas(carteira, cedente="00.000.000")["total_lista"], 0)
        self.assertEqual(consultar_salvas(carteira, vencimento="01/01/2020")["total_lista"], 0)
        self.assertEqual(consultar_salvas(carteira, registro="00/0000")["total_lista"], 0)

    def test_segunda_consulta_recusa_a_mesma_nota(self) -> None:
        pasta = Path(tempfile.mkdtemp())
        carteira = pasta / "antecipe.db"
        lote = _csv(
            _linha(NU_DOCUMENTO="OUTRA", VALOR_NOMINAL="100,00"),
            _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
        )
        primeira = processar(lote, carregar(RAIZ), carteira=carteira)
        self.assertTrue(any(linha.nu_documento == "OUTRA" and linha.aceita for linha in primeira.linhas))
        segunda = processar(lote, carregar(RAIZ), carteira=carteira)
        outra = next(linha for linha in segunda.linhas if linha.nu_documento == "OUTRA")
        self.assertIn("já foi adquirida", outra.motivos[0])
        from antecipe.lote import consultar_salvas

        self.assertEqual(consultar_salvas(carteira, busca="OUTRA")["total_lista"], 1)
        self.assertEqual(consultar_salvas(carteira, busca="BASE")["total_lista"], 0)

    def test_nota_recusada_nao_entra_na_carteira(self) -> None:
        pasta = Path(tempfile.mkdtemp())
        carteira = pasta / "antecipe.db"
        processar(
            _csv(_linha(NU_DOCUMENTO="CHEQUE", TIPO_RECEBIVEL="Cheque")),
            carregar(RAIZ),
            carteira=carteira,
        )
        self.assertFalse(carteira.exists())
        resultado = processar(
            _csv(
                _linha(NU_DOCUMENTO="OUTRA", VALOR_NOMINAL="100,00"),
                _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
            ),
            carregar(RAIZ),
            carteira=carteira,
        )
        self.assertTrue(any(linha.nu_documento == "OUTRA" and linha.aceita for linha in resultado.linhas))

    def test_concentracao_considera_o_que_ja_foi_aceito(self) -> None:
        pasta = Path(tempfile.mkdtemp())
        carteira = pasta / "antecipe.db"
        processar(
            _csv(
                _linha(NU_DOCUMENTO="PEQUENA", VALOR_NOMINAL="100,00"),
                _linha(NU_DOCUMENTO="BASE", VALOR_NOMINAL="5000,00", DOC_SACADO="01.026.553/0001-86"),
            ),
            carregar(RAIZ),
            carteira=carteira,
        )
        resultado = processar(
            _csv(_linha(NU_DOCUMENTO="PEQUENA-2", VALOR_NOMINAL="100,00")),
            carregar(RAIZ),
            carteira=carteira,
        )
        self.assertIn("CONCENTRACAO_MAXIMA_SACADO", resultado.linhas[0].codigos)
        self.assertIn("limite", resultado.linhas[0].motivos[0])

    def test_estoque_publicado_tem_uma_raiz_acima_do_limite(self) -> None:
        indice = montar(RAIZ / "data" / "estoque_antecipe.csv", FUNDO)
        acima = [valor for valor in indice.por_raiz_centavos.values() if valor * 100 > indice.total_fundo_centavos * 10]
        self.assertEqual(len(acima), 1)
        self.assertGreater(len(indice.chaves), 100_000)
