# Antecipe FIDC

Classifica um lote de recebíveis e mostra o que o fundo aceita, o que recusa e quanto paga.

## Pré-requisitos

Python 3.11 ou mais novo.

## Subir a aplicação

Na pasta do projeto.

PowerShell:

```
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
```

Bash:

```
bash iniciar.sh
```

Abra http://127.0.0.1:8000

Escolha o CSV do lote e clique em **Clique aqui para analisar o lote**. **Consultar notas salvas** abre as notas já aceitas, sem enviar um arquivo novo.

Para ver o banco gravar, envie o arquivo que já vem no clone:

```
data/lote_teste.csv
```

São 20 recibos. A tela mostra 13 aceitas, de REC-01 a REC-13, e 7 recusadas. **Consultar notas salvas** passa a listar essas 13. Enviar o mesmo arquivo de novo recusa as 13 como parcela já adquirida.

## Onde fica o CSV

O clone não traz o estoque. Depois do `git clone`, a pasta `data/` tem `.gitkeep` e `lote_teste.csv`.

Para analisar as 100.554 linhas, copie o CSV da organização para este caminho, com este nome:

```
data/estoque_antecipe.csv
```

Sem esse arquivo a aplicação sobe do mesmo jeito. A tela abre e **Consultar notas salvas** responde vazia até que um lote novo seja aceito. O estoque só é necessário para a análise das 100 mil linhas.

Não envie o estoque ao Git. A pasta `data/` fica de fora de propósito, com a exceção do lote de teste. O mesmo vale para `data/lote_500k.csv`, `data/lote_1m.csv` e para o banco `data/antecipe.db`, que o servidor cria sozinho quando uma nota nova é aceita.

Estes três nomes são só análise e não entram no banco: `estoque_antecipe.csv`, `lote_500k.csv` e `lote_1m.csv`. Qualquer outro nome grava as notas aceitas.

O mock de situação cadastral já está em `config/cnpj_situacao_mock.csv`. Os sacados que este fundo recusa estão em `config/sacados_recusados.txt`. As regras do fundo estão em `config/validadores_antecipe.json`.

A página que o servidor abre é `web/estatico`.

## O que a tela mostra

Quantidade aceita, quantidade recusada e o líquido do lote. Cada nota recusada mostra o motivo. Na recusa cadastral, o motivo cita o CNPJ e diz que ele está na lista de recusa do fundo. Dá para alternar aceitas e recusadas, filtrar a categoria, buscar o número do documento, filtrar o líquido das aceitas e ordenar. A lista mostra 10, 20, 50, 100 ou 200 notas por página.

**Consultar notas salvas** lê o banco local, sem um CSV novo. As notas aceitas de um lote novo ficam em `data/antecipe.db`. Esse arquivo não entra no Git. O estoque oficial, o lote de 500 mil linhas e o de 1 milhão são só análise: não são gravados no banco.

A nota entra se o CNPJ do sacado é válido, ele não está na lista de recusa do fundo, o tipo é duplicata, o valor é de pelo menos R$ 100,00 e o prazo entre a aquisição e o vencimento não passa de 180 dias. O desconto usa outra data: 2% ao mês, da operação em 24/10/2026 até o vencimento. A concentração recusa o sacado que passa de 10% do fundo. A parcela repetida é o mesmo cedente, o mesmo número e o mesmo vencimento.

`POST /lotes` recebe o CSV no campo `arquivo`. Com `pagina` e `tamanho` na consulta, a resposta traz só aquela página e um `id`. `GET /lotes/{id}` pede outra página do mesmo lote. `GET /carteira` lista as notas já aceitas.

## Linha de comando

```
$env:PYTHONPATH = "src"
python -m antecipe.lote CAMINHO_DO_CSV
```

## Desempenho

A leitura e a decisão percorrem o arquivo uma vez. Tempos medidos com `python -m antecipe.lote` nesta máquina:

- 100.554 linhas (`data/estoque_antecipe.csv`): 3,5 s
- 500.000 linhas (`data/lote_500k.csv`): 17,1 s

## Log

Cada lote acrescenta uma linha JSON em `logs/lotes.log`, com `id`, `resultado`, a duração, as quantidades e os códigos das regras. Se o lote para antes da decisão, a linha sai com `resultado` igual a `erro` e quantidades zeradas, sem o texto da falha. O arquivo não guarda nome, CNPJ, número do documento, valor nem o texto da linha. A pasta `logs/` não entra no Git.
