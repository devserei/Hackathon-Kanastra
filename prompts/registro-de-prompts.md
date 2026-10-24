# Registro de prompts

Arquivo exigido pelo item 4.1.2 do Edital do Hackathon Kanastra: todos os prompts usados no desenvolvimento, em ordem cronológica, com a descrição do que foi feito com cada resposta.

---

## Prompt 1

- **Data e hora:** 2026-10-24 09:50 (UTC-3)
- **Prompt:**

> Crie os arquivos de log, source, gitignore, uma pasta chamada data (onde armazenaremos o arquivo csv) e demais pastas necessárias que achar necessário para iniciarmos nosso trabalho.
>
> Considere o horário deste prompt e esta mesma mensagem como sendo o prompt #1.

- **O que foi feito com a resposta:** Criada a estrutura inicial do repositório, sem código de aplicação. Pastas: `src/` (código-fonte), `config/` (regras e validadores alteráveis sem deploy), `logs/` (logs de execução, fora do Git), `data/` (dataset) e `prompts/` (este registro). O arquivo `estoque_antecipe.csv` foi movido da raiz para `data/`. O `.gitignore` exclui segredos, dependências, logs de execução e o CSV, para não versionar credenciais nem dados da carteira.

## Prompt 2

- **Data e hora:** 2026-10-24 09:52 (UTC-3)
- **Prompt:**

> Digira estas informações do Notion, pois preciso realizar algumas perguntas sobre escopo do projeto, regras de negócio, dicas para realizarmos o tratamento do CSV e demais dados. 

- **O que foi feito com a resposta:** Tetxo do Notion digerido com sucesso. Arquivo CSV e JSON ainda não foram lidos.

## Prompt 3

- **Data e hora:** 2026-10-24 10:01 (UTC-3)
- **Prompt:**

> Explique-me mais sobre as regras de negócio e tente encontrar corner cases para termos cuidado ao construir o sistema. Seja minucioso na resposta, pois nunca construí um sistema financeiro.
>
> Para lhe ajudar, considere:
> 1. Leia as 20 primeiras linhas do CSV;
> 2. Um arquivo JSON contendo mais regras de negócio (validadores e precificação do ANTECIPE FIDC);
> 3. Se achar necessário, podemos criar um arquivo skill.md para armazenar as regras e otimizar a janela de contexto. Ou, se o Cursor já tiver uma funcionalidade nativa podemos usar ela para facilitar.

- **O que foi feito com a resposta:** Lidas as 20 primeiras linhas de `data/estoque_antecipe.csv` e varridas as 100.554 linhas para achar casos de borda. Explicadas as regras do JSON, a diferença entre estoque e lote enviado pela empresa, a fórmula de desconto simples e os cuidados de duplicidade, concentração, datas, dinheiro e logs. Nenhum código de aplicação foi escrito. A sugestão de `skill.md` foi recusada em favor de uma Cursor Rule nativa, ainda não criada.

## Prompt 4

- **Data e hora:** 2026-10-24 10:22 (UTC-3)
- **Prompt:**

> Vamos iniciar a etapa 1 do projeto. Crie o contrato com as decisões fechadas e o arquivo de operação que o sistema lê.

- **O que foi feito com a resposta:** Criados `config/contrato.md` e `config/operacao.json`, como pedido. Para complementar, também ficaram o cadastro local vazio `config/situacao_cadastral.json`, o módulo `src/antecipe/configuracao.py`, que abre o JSON oficial do fundo junto com esses arquivos, e os testes em `tests/test_configuracao.py`. Seis testes passaram. A stack foi registrada no contrato: Python 3.11+, motor próprio, FastAPI e HTML estático nas etapas seguintes. 

config/contrato.md, o texto das decisões

config/operacao.json, as mesmas decisões em formato que o programa lê

config/situacao_cadastral.json, um cadastro vazio

src/antecipe/configuracao.py e tests/test_configuracao.py

## Prompt 5

- **Data e hora:** 2026-10-24 10:41 (UTC-3)
- **Prompt:**

> Vamos iniciar a Etapa 2 agora. Para ela, tenho em mente algumas ideias.
>
> Mas antes, você vê necessidade em normalizarmos este arquivo? Pois nos valores com vírgula ou ponto seria interessante utilizarmos valores inteiros.
>
> 1. Ler uma linha com separador `;`, decimal com vírgula, data dia/mês/ano e número do documento como texto.
> 2. Validar o CNPJ pelos dígitos verificadores.
> 3. Criar um validador por código do JSON. Validador com ativo falso executa pruning. Código desconhecido interrompe o lote.
> 4. Calcular o desconto simples: valor de face × 2% × (dias ÷ 30), em centavos.
> 5. Devolver todos os motivos independentes da mesma nota.
> 6. Trataremos esta etapa usando critérios UNIX, se necessário faremos pequenos códigos python em que cada um resolve um problema e independe do outro.

- **O que foi feito com a resposta:** O CSV não foi reescrito. A leitura de uma linha, em `src/antecipe/linha.py`, é a normalização. Sobre vírgula e ponto: `dinheiro.py` não guarda float. O texto `2.278,08` ou `2278,08` passa por `Decimal` e vira centavos inteiros (227808). O desconto em `preco.py` também usa `Decimal` e arredonda o resultado para centavos, meio centavo para cima. Cada problema ficou num módulo próprio: dinheiro, CNPJ, prazo, preço e um arquivo por validador. `avaliar.py` junta os motivos da mesma nota. Concentração continua adiada, porque depende da carteira. 34 testes passaram.

## Prompt 6

- **Data e hora:** 2026-10-24 10:53 (UTC-3)
- **Prompt:**

> Quis mudar o nome do arquivo Python para normalizar.py.
>
> Qual é a codificação do arquivo, por exemplo UTF-8? Isso gera alguma incompatibilidade para lermos os dados no futuro?

- **O que foi feito com a resposta:** `src/antecipe/linha.py` passou a se chamar `src/antecipe/normalizar.py`, e os imports foram atualizados. O estoque é UTF-8. `ler_texto` aceita UTF-8 com ou sem BOM, então um arquivo salvo pelo Excel nessa codificação continua legível, com os acentos preservados. Latin-1 e Windows-1252 são recusados em vez de serem lidos com o caractere trocado. UTF-8 não impede ler no futuro um arquivo no mesmo formato. Outra codificação é incompatível de propósito.

## Prompt 7

- **Data e hora:** 2026-10-24 11:04 (UTC-3)
- **Prompt:**

> Estou achando muito complicado o fluxo que você está usando. Essa complexidade é padrão ou podemos deixar o sistema um pouco mais simples?
>
> O fluxo que eu quero é normalizar, depois avaliar, e os próximos passos nessa mesma sequência.

- **O que foi feito com a resposta:** O caminho de uma nota passou a ser `normalizar.py` e, em seguida, `avaliar.py`. As regras deixaram de ser uma etapa e foram para `regras.py`, chamado só pelo avaliar. Saíram `dinheiro.py`, `cnpj.py`, `prazo.py`, `preco.py` e a pasta `validadores/`. A configuração continua em `configuracao.py`, fora dessa sequência. Os testes seguiram passando.

## Prompt 8

- **Data e hora:** 2026-10-24 11:42 (UTC-3)
- **Prompt:**

> Vamos iniciar a etapa de indexação.

- **O que foi feito com a resposta:** Criado `src/antecipe/estoque.py`, o passo depois do avaliar. Um passe lê o estoque com `ler_linha` e monta o índice. `buscar` responde se a chave cedente + número + vencimento já existe, e `total_raiz` soma a carteira do ANTECIPE por raiz de CNPJ. `avaliar_nota` não entra nesse passe. Três testes passaram, inclusive o arquivo de 100 mil linhas.

## Prompt 9

- **Data e hora:** 2026-10-24 11:53 (UTC-3)
- **Prompt:**

> Perfeito, faça:
>
> 1. Os cortes e simplificações;
> 2. Teste o código novo;
> 3. Envie os comandos para eu mesmo testar o código;
> 4. Etapa 4;
> 5. Prompts novos

- **O que foi feito com a resposta:** O fluxo ficou em `normalizar.py`, `avaliar.py` e `lote.py`. Saíram `regras.py`, `estoque.py`, `contrato.md`, `operacao.json` e o cadastro vazio. A situação cadastral só recusa quando existe uma lista. O lote decide duplicidade e concentração de cima para baixo. 26 testes passaram.

## Prompt 10

- **Data e hora:** 2026-10-24 12:04 (UTC-3)
- **Prompt:**

> Perfeito, faça um frontend bem simples pois vamos altrá-lo usando componentes do React Bits depois. Preciso apenas avaliar as informações de recusas para fazermos uma filtragem depois. 

- **O que foi feito com a resposta:** A tela envia o CSV e mostra a decisão do lote: aceita ou recusada, motivo, líquido e total. A página que abre agora está em `web/estatico` e o `servidor.py` chama o mesmo `lote.py`. Os componentes React ficaram em `web/src/components` (`Envio`, `Resumo`, `ListaNotas`) para serem trocados pelos do React Bits.

## Prompt 11

- **Data e hora:** 2026-10-24 12:31 (UTC-3)
- **Prompt:**

> Faça essa junção de código ou automação para mim, depois anote o prompt

- **O que foi feito com a resposta:** O estoque continua fixo e o arquivo novo entra pelo lote. Criei `exemplos/lote_novo.csv` e o botão "Lote de exemplo", que chama `processar` com os dois. O exemplo tem uma nota aceita e quatro recusas: já adquirida, cheque, valor abaixo do mínimo e concentração.

## Prompt 12

- **Data e hora:** 2026-10-24 12:34 (UTC-3)
- **Prompt:**

> Qual é a escalabilidade deste serviço? Quero a complexidade e o O(n) das varreduras, das leituras e das comparações que ainda formos fazer. Isso aguenta arquivos de 500 mil linhas, 1 milhão, 2 milhões, 3 milhões?

- **O que foi feito com a resposta:** A leitura e a decisão são uma passagem em cada arquivo, O(n). A comparação com o estoque, depois do índice pronto, é O(1) por nota. O estoque de 100 mil linhas leva cerca de 1,6 s. Quinhentas mil linhas seguem o mesmo formato, na casa de 8 s. Um, dois e três milhões continuam lineares, com o limite prático na memória, porque o arquivo inteiro entra de uma vez e a resposta devolve todas as linhas.

## Prompt 13

- **Data e hora:** 2026-10-24 13:51 (UTC-3)
- **Prompt:**

> Vimos os dois arquivos novos do Notion, o resultado esperado das 100 mil linhas e o mock de situação cadastral. Estamos implementando os dois no projeto.

- **O que foi feito com a resposta:** O `cnpj_situacao_mock.csv` passou a alimentar a regra de situação cadastral. O arquivo enviado é classificado como a carteira: prazo entre aquisição e vencimento, concentração pela participação final de cada raiz no fundo, e o `resultado_esperado_100k.json` confere essas decisões nas 100.554 linhas.

## Prompt 14

- **Data e hora:** 2026-10-24 14:06 (UTC-3)
- **Prompt:**

> Ok, para finalizarmos este projeto, o que falta? Lembre-se das 8 etapas ou mais

- **O que foi feito com a resposta:** O README passou a explicar como subir a tela. Cada lote grava um log JSON só com duração, quantidades e códigos das regras. O estoque de 100.554 linhas levou 3,1 s e um arquivo de 500.000 linhas, no mesmo formato, levou 15,9 s. A tela mostra o valor de face que ficou de fora.