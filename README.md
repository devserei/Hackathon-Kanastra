# Antecipe FIDC

Classifica um lote de recebíveis e mostra o que o fundo aceita, o que recusa e quanto paga.

## Pré-requisitos

Python 3.11 ou mais novo.

## Subir a aplicação

Na pasta do projeto:

```
python -m pip install -r requirements.txt
```

No PowerShell:

```
$env:PYTHONPATH = "src"
python -m antecipe.servidor
```

No bash:

```
PYTHONPATH=src python -m antecipe.servidor
```

Abra http://127.0.0.1:8000

O botão **Lote de exemplo** classifica `exemplos/lote_novo.csv`. Para outro arquivo, escolha o CSV e clique em **Analisar lote**.

## Onde fica o CSV

O arquivo grande da organização fica em `data/estoque_antecipe.csv`. Essa pasta não entra no Git.

O mock de situação cadastral já está em `config/cnpj_situacao_mock.csv`. As regras do fundo estão em `config/validadores_antecipe.json`.

## O que a tela mostra

Quantidade aceita, quantidade recusada, líquido do lote e o valor de face que ficou de fora. Cada nota recusada mostra o motivo. A tabela mostra 50 notas por vez.

A mesma decisão sai em `POST /lotes`, enviando o CSV no campo `arquivo`.

## Linha de comando

```
$env:PYTHONPATH = "src"
python -m antecipe.lote CAMINHO_DO_CSV
```

## Desempenho

A leitura e a decisão percorrem o arquivo uma vez. Tempos medidos com `python -m antecipe.lote` nesta máquina:

- 100.554 linhas (`data/estoque_antecipe.csv`): 3,1 s
- 500.000 linhas, no mesmo formato: 15,9 s

## Log

Cada lote acrescenta uma linha JSON em `logs/lotes.log`, com a duração, as quantidades e os códigos das regras. O arquivo não guarda nome, CNPJ, número do documento, valor nem o texto da linha. A pasta `logs/` não entra no Git.
