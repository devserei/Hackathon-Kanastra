"""Segunda etapa do fluxo: recebe a nota normalizada, aplica as regras e calcula o líquido."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from antecipe.configuracao import Configuracao
from antecipe.normalizar import Nota
from antecipe.regras import CodigoDesconhecido, aplicar, desconto_simples

__all__ = ["CodigoDesconhecido", "ResultadoNota", "avaliar_nota", "desconto_simples"]


@dataclass(frozen=True)
class ResultadoNota:
    motivos: tuple[str, ...]
    desconto_centavos: int | None
    liquido_centavos: int | None
    regras_adiadas: tuple[str, ...]

    @property
    def recusada(self) -> bool:
        return bool(self.motivos)


def avaliar_nota(nota: Nota, configuracao: Configuracao) -> ResultadoNota:
    motivos, adiadas = aplicar(nota, configuracao)
    if motivos:
        return ResultadoNota(motivos, None, None, adiadas)

    operacao = datetime.strptime(configuracao.data_operacao, "%Y-%m-%d").date()
    dias = (nota.vencimento - operacao).days
    desconto = desconto_simples(
        nota.valor_centavos,
        dias,
        configuracao.precificacao.taxa_mensal_percentual,
        configuracao.precificacao.base_dias,
    )
    return ResultadoNota((), desconto, nota.valor_centavos - desconto, adiadas)
