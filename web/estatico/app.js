const POR_PAGINA = 50;

const arquivo = document.querySelector("#arquivo");
const enviar = document.querySelector("#enviar");
const erro = document.querySelector("#erro");
const resumo = document.querySelector("#resumo");
const listas = document.querySelector("#listas");

const paginas = { aceitas: 0, recusadas: 0 };
let linhasAtuais = [];

arquivo.addEventListener("change", () => {
  enviar.disabled = !arquivo.files?.[0];
});

document.querySelector("#envio").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const escolhido = arquivo.files?.[0];
  if (!escolhido) {
    return;
  }
  const dados = new FormData();
  dados.append("arquivo", escolhido);
  await analisar("/lotes", dados);
});

document.querySelector("#exemplo").addEventListener("click", () => analisar("/lotes/exemplo"));

async function analisar(caminho, corpo) {
  enviar.disabled = true;
  document.querySelector("#exemplo").disabled = true;
  enviar.textContent = "Analisando…";
  erro.hidden = true;
  try {
    const resposta = await fetch(caminho, { method: "POST", body: corpo });
    const json = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      throw new Error(typeof json.detail === "string" ? json.detail : "Não foi possível ler o lote.");
    }
    mostrar(json);
  } catch (falha) {
    resumo.hidden = true;
    listas.hidden = true;
    erro.hidden = false;
    erro.textContent = falha.message || "Não foi possível ler o lote.";
  } finally {
    enviar.disabled = !arquivo.files?.[0];
    document.querySelector("#exemplo").disabled = false;
    enviar.textContent = "Analisar lote";
  }
}

listas.addEventListener("click", (evento) => {
  const botao = evento.target.closest("button[data-grupo]");
  if (!botao || botao.disabled) {
    return;
  }
  paginas[botao.dataset.grupo] += Number(botao.dataset.direcao);
  desenhar();
});

function mostrar(resultado) {
  document.querySelector("#aceitas").textContent = resultado.aceitas;
  document.querySelector("#recusadas").textContent = resultado.recusadas;
  document.querySelector("#liquido").textContent = reais(resultado.total_liquido_centavos);
  document.querySelector("#face").textContent = reais(resultado.total_face_recusado_centavos);
  linhasAtuais = resultado.linhas;
  paginas.aceitas = 0;
  paginas.recusadas = 0;
  resumo.hidden = false;
  listas.hidden = false;
  desenhar();
}

function desenhar() {
  const aceitas = linhasAtuais.filter((linha) => linha.aceita);
  const recusadas = linhasAtuais.filter((linha) => !linha.aceita);
  desenharBloco(document.querySelector("#bloco-aceitas"), {
    titulo: "Aceitas",
    linhas: aceitas,
    grupo: "aceitas",
    vazio: "Nenhuma nota aceita.",
    colunas: ["Documento", "Líquido"],
    celulas: (linha) => [linha.nu_documento || "—", reais(linha.liquido_centavos)],
  });
  desenharBloco(document.querySelector("#bloco-recusadas"), {
    titulo: "Recusadas",
    linhas: recusadas,
    grupo: "recusadas",
    vazio: "Nenhuma nota recusada.",
    colunas: ["Documento", "Motivo"],
    celulas: (linha) => [linha.nu_documento || "—", linha.motivos.join(" ")],
  });
}

function desenharBloco(elemento, bloco) {
  elemento.replaceChildren();
  const titulo = document.createElement("h2");
  titulo.textContent = bloco.titulo;
  elemento.append(titulo);
  if (bloco.linhas.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "vazio";
    vazio.textContent = bloco.vazio;
    elemento.append(vazio);
    return;
  }
  const inicio = paginas[bloco.grupo] * POR_PAGINA;
  const fatia = bloco.linhas.slice(inicio, inicio + POR_PAGINA);
  elemento.append(tabela(bloco.colunas, fatia, bloco.celulas));
  elemento.append(paginacao(bloco.grupo, inicio, fatia.length, bloco.linhas.length));
}

function tabela(colunas, linhas, celulas) {
  const table = document.createElement("table");
  table.className = "notas";
  const cabecalho = document.createElement("thead");
  const linhaCabecalho = document.createElement("tr");
  for (const coluna of colunas) {
    const th = document.createElement("th");
    th.textContent = coluna;
    linhaCabecalho.append(th);
  }
  cabecalho.append(linhaCabecalho);
  const corpo = document.createElement("tbody");
  for (const linha of linhas) {
    const tr = document.createElement("tr");
    for (const texto of celulas(linha)) {
      tr.append(celula(texto));
    }
    corpo.append(tr);
  }
  table.append(cabecalho, corpo);
  return table;
}

function paginacao(grupo, inicio, quantidade, total) {
  const barra = document.createElement("div");
  barra.className = "paginas";
  const anterior = botao("Anterior", grupo, -1, inicio === 0);
  const proxima = botao("Próxima", grupo, 1, inicio + quantidade >= total);
  const texto = document.createElement("span");
  texto.textContent = `${inicio + 1}–${inicio + quantidade} de ${total}`;
  barra.append(anterior, texto, proxima);
  return barra;
}

function botao(rotulo, grupo, direcao, desabilitado) {
  const botaoPagina = document.createElement("button");
  botaoPagina.type = "button";
  botaoPagina.textContent = rotulo;
  botaoPagina.dataset.grupo = grupo;
  botaoPagina.dataset.direcao = String(direcao);
  botaoPagina.disabled = desabilitado;
  return botaoPagina;
}

function celula(texto) {
  const td = document.createElement("td");
  td.textContent = texto;
  return td;
}

function reais(centavos) {
  if (centavos == null) {
    return "";
  }
  const negativo = centavos < 0;
  const absoluto = Math.abs(centavos);
  const inteiros = Math.floor(absoluto / 100).toLocaleString("pt-BR");
  const frac = String(absoluto % 100).padStart(2, "0");
  return `${negativo ? "-" : ""}R$ ${inteiros},${frac}`;
}
