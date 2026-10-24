# Contrato da etapa 1

Decisões fechadas. O código lê `validadores_antecipe.json` e `operacao.json`. Número de regra de fundo (mínimo, prazo, taxa, concentração) só existe no JSON oficial.

## Stack

Python 3.11 ou mais novo. O motor fica em `src/antecipe`, sem framework. A API da etapa 5 será FastAPI. A tela da etapa 6 será HTML estático servido por essa API. Os testes usam `unittest`.

## Operação

A data da operação é 24/10/2026.

A chave do recebível é o CNPJ do cedente, o número do documento e o vencimento. Zeros à esquerda e hífen do número permanecem. O valor não entra na chave. A mesma chave com outro valor é o mesmo recebível, e a compra nova é recusada.

O dinheiro é guardado em centavos. Cada nota é arredondada para duas casas, com meio centavo para cima. O total a receber soma esses líquidos.

O prazo é a quantidade de dias corridos entre a data da operação e o vencimento. Nota que vence na data da operação entra, com desconto zero. Nota que vence em 180 dias entra. Nota que vence em 181 dias sai.

## Concentração e duplicidade

A concentração usa a carteira do ANTECIPE FIDC, com as notas já vencidas incluídas. O CSV não tem baixa. Nota recusada por outra regra não ocupa limite. O lote é lido de cima para baixo, e essa ordem decide quem entra quando o limite estoura.

A duplicidade olha o estoque dos 18 fundos e o próprio lote. Reenviar um lote devolve o resultado já guardado.

## Situação cadastral

O cadastro local é `config/situacao_cadastral.json`, no mapa `por_cnpj`. A chave é o CNPJ com 14 dígitos, sem máscara. Sem registro, a nota é recusada com a mensagem "Situação cadastral não encontrada". O mapa começa vazio.

## O que o JSON oficial continua mandando

Validadores com `ativo` falso ficam no arquivo e ficam fora da avaliação. Um código desconhecido impede o lote. A precificação oficial é desconto simples, 2% ao mês, base de 30 dias, até que o arquivo mude.
