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

## Onde fica o CSV

O arquivo grande da organização fica em `data/estoque_antecipe.csv`. Essa pasta não entra no Git.

O mock de situação cadastral já está em `config/cnpj_situacao_mock.csv`. Os sacados que este fundo recusa estão em `config/sacados_recusados.txt`. As regras do fundo estão em `config/validadores_antecipe.json`.

A página que o servidor abre é `web/estatico`.

## O que a tela mostra

Quantidade aceita, quantidade recusada e o líquido do lote. Cada nota recusada mostra o motivo. Na recusa cadastral, o motivo cita o CNPJ e diz que ele está na lista de recusa do fundo. Dá para alternar aceitas e recusadas, filtrar a categoria, buscar o número do documento, filtrar o líquido das aceitas e ordenar. A lista mostra 10, 20, 50, 100 ou 200 notas por página.

**Consultar notas salvas** lê o banco local, sem um CSV novo. As notas aceitas de um lote novo ficam em `data/antecipe.db`. Esse arquivo não entra no Git. O estoque oficial é só análise: ele não é gravado no banco.

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
