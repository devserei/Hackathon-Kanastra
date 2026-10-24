import { montarDock, pintarDock } from "./dock.js";
import { criarLattice } from "./lattice.js";
import { montarScanner } from "./scanner.js";
import { montarTopography } from "./topography.js";

const arquivo = document.querySelector("#arquivo");
const nome = document.querySelector("#nome");
const enviar = document.querySelector("#enviar");
const estado = document.querySelector("#estado");
const erro = document.querySelector("#erro");
const resumo = document.querySelector("#resumo");
const listas = document.querySelector("#listas");
const FILTROS = [
  { id: "todas", label: "Todas", icone: icone("todas"), casa: () => true },
  { id: "tipo", label: "Tipo", icone: icone("tipo"), casa: (linha) => tem(linha, "TIPO_RECEBIVEL") },
  { id: "valor", label: "Valor", icone: icone("valor"), casa: (linha) => tem(linha, "VALOR_MINIMO") },
  { id: "prazo", label: "Prazo", icone: icone("prazo"), casa: (linha) => tem(linha, "PRAZO_MAXIMO") },
  { id: "cadastro", label: "Cadastro", icone: icone("cadastro"), casa: (linha) => tem(linha, "SITUACAO_CADASTRAL_SACADO") },
  { id: "grupo", label: "Grupo", icone: icone("grupo"), casa: (linha) => tem(linha, "CONCENTRACAO_MAXIMA_SACADO") },
  { id: "duplicata", label: "Duplicata", icone: icone("duplicata"), casa: (linha) => linha.motivos.some((motivo) => motivo.includes("já foi adquirida")) },
];

const paginas = { aceitas: 0, recusadas: 0, salvas: 0 };
let linhasAtuais = [];
let lattice = null;
let filtro = "todas";
let vista = "aceitas";
let dock = null;
let porPagina = 50;
let busca = "";
let valorMin = "";
let valorMax = "";
let ordem = "";
let cedente = "";
let vencimento = "";
let registro = "";
let movimento = "";
let loteId = "";
let contagens = null;
let totalLista = 0;
let pedido = 0;
let buscaTimer = 0;

const SCANNER = {
  preto: {
    color1: "#f4f4f5",
    color2: "#71717a",
    color3: "#d4d4d8",
    brightness: 0.45,
    glow: 0.28,
    vignette: 0.62,
    scanlineIntensity: 0.22,
    grainIntensity: 0.035,
    opacity: 0.85,
    lightMode: false,
  },
  bege: {
    color1: "#064e3b",
    color2: "#047857",
    color3: "#a7f3d0",
    brightness: 0.62,
    glow: 0.16,
    vignette: 0.18,
    scanlineIntensity: 0.08,
    grainIntensity: 0.02,
    opacity: 0.42,
    lightMode: true,
  },
};

const TOPOGRAFIA = {
  preto: {
    color: "#075A44",
    lightMode: false,
    brightness: 1,
    glow: 0.6,
    opacity: 1,
  },
  bege: {
    color: "#075A44",
    lightMode: true,
    brightness: 1.15,
    glow: 0.22,
    opacity: 0.92,
  },
};

function opcoesTopografia(tema) {
  return TOPOGRAFIA[tema === "bege" ? "bege" : "preto"];
}

function pintarLattice(raiz) {
  if (!raiz) return;
  const bege = document.documentElement.dataset.tema === "bege";
  const cor = bege ? "#064e3b" : "#f4f4f5";
  const marca = raiz.dataset.status === "error" ? (bege ? "#9f1239" : "#d4d4d8") : bege ? "#064e3b" : "#e4e4e7";
  raiz.style.setProperty("--ll-color", cor);
  raiz.style.setProperty("--ll-glow", cor);
  raiz.style.setProperty("--ll-mark", marca);
  raiz.style.setProperty("--ll-mark-glow", marca);
}

const fundo = document.querySelector(".fundo");
let temaInicial = "preto";
try {
  temaInicial = localStorage.getItem("antecipe-tema") === "bege" ? "bege" : "preto";
} catch {
  temaInicial = "preto";
}
document.documentElement.dataset.tema = temaInicial;
montarScanner(fundo, SCANNER[temaInicial]);
aplicarTema(temaInicial);

const boasVindas = document.querySelector("#boas-vindas");
let pararTopografia = montarTopography(document.querySelector(".fundo-topo"), opcoesTopografia(temaInicial));
document.querySelector("#entrar").addEventListener("click", () => {
  pararTopografia?.();
  pararTopografia = null;
  boasVindas.hidden = true;
  document.querySelector("main").hidden = false;
});

arquivo.addEventListener("change", () => {
  const escolhido = arquivo.files?.[0];
  nome.textContent = escolhido ? escolhido.name : "Nenhum arquivo";
  enviar.disabled = !escolhido;
});

document.querySelector("#envio").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const escolhido = arquivo.files?.[0];
  if (!escolhido) return;
  const dados = new FormData();
  dados.append("arquivo", escolhido);
  await analisar("/lotes", dados);
});

document.querySelectorAll("button.tema").forEach((botao) => {
  botao.addEventListener("click", () => {
    aplicarTema(document.documentElement.dataset.tema === "bege" ? "preto" : "bege");
  });
});
document.querySelector("#ver-aceitas").addEventListener("click", () => escolherVista("aceitas"));
document.querySelector("#ver-recusadas").addEventListener("click", () => escolherVista("recusadas"));
document.querySelector("#ver-salvas").addEventListener("click", () => escolherVista("salvas"));
document.querySelector("#consultar-salvas").addEventListener("click", () => escolherVista("salvas"));
document.querySelector("#busca").addEventListener("input", (evento) => {
  busca = evento.target.value;
  paginas[vista] = 0;
  if (vista !== "salvas" && !loteId) {
    desenhar();
    return;
  }
  window.clearTimeout(buscaTimer);
  buscaTimer = window.setTimeout(() => {
    movimento = "pagina";
    atualizar();
  }, 200);
});
document.querySelector("#faixa").addEventListener("input", (evento) => {
  const campo = evento.target;
  if (campo.id === "valor-min") valorMin = campo.value;
  if (campo.id === "valor-max") valorMax = campo.value;
  paginas.aceitas = 0;
  if (!loteId) {
    desenhar();
    return;
  }
  window.clearTimeout(buscaTimer);
  buscaTimer = window.setTimeout(() => {
    movimento = "pagina";
    atualizar();
  }, 200);
});
document.querySelector("#consulta-salva").addEventListener("input", (evento) => {
  const campo = evento.target;
  if (campo.id === "cedente") cedente = campo.value;
  if (campo.id === "vencimento") vencimento = campo.value;
  if (campo.id === "registro") registro = campo.value;
  paginas.salvas = 0;
  window.clearTimeout(buscaTimer);
  buscaTimer = window.setTimeout(() => {
    movimento = "pagina";
    atualizar();
  }, 200);
});
document.querySelector("#ordens").addEventListener("click", (evento) => {
  const botao = evento.target.closest("button[data-ordem]");
  if (!botao) return;
  ordem = ordem === botao.dataset.ordem ? "" : botao.dataset.ordem;
  marcarOrdem();
  paginas.aceitas = 0;
  movimento = "pagina";
  atualizar();
});
document.querySelector(".tamanhos").addEventListener("click", (evento) => {
  const botao = evento.target.closest("button[data-tamanho]");
  if (!botao) return;
  porPagina = Number(botao.dataset.tamanho);
  paginas.aceitas = 0;
  paginas.recusadas = 0;
  paginas.salvas = 0;
  marcarTamanho();
  movimento = "pagina";
  atualizar();
});

listas.addEventListener("click", (evento) => {
  const botao = evento.target.closest("button[data-grupo]");
  if (!botao || botao.disabled) return;
  paginas[botao.dataset.grupo] += Number(botao.dataset.direcao);
  movimento = "pagina";
  atualizar();
});

async function analisar(caminho, corpo) {
  enviar.disabled = true;
  erro.hidden = true;
  filtro = "todas";
  vista = "aceitas";
  busca = "";
  valorMin = "";
  valorMax = "";
  ordem = "";
  paginas.aceitas = 0;
  paginas.recusadas = 0;
  loteId = "";
  document.querySelector("#dock").hidden = true;
  mostrarLattice("working");
  const params = paramsConsulta(1);
  const destino = `${caminho}${caminho.includes("?") ? "&" : "?"}${params}`;
  try {
    const resposta = await fetch(destino, { method: "POST", body: corpo });
    const json = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      throw new Error(typeof json.detail === "string" ? json.detail : "Não foi possível ler o lote.");
    }
    lattice?.concluir();
    mostrar(json);
  } catch (falha) {
    resumo.hidden = true;
    listas.hidden = true;
    mostrarLattice("error");
    erro.hidden = false;
    erro.textContent = falha.message || "Não foi possível ler o lote.";
  } finally {
    enviar.disabled = !arquivo.files?.[0];
  }
}

function mostrarLattice(status) {
  limparLattice();
  estado.hidden = false;
  lattice = criarLattice({
    status,
    label: "Lendo o CSV",
    errorLabel: "Falha na leitura",
    glow: status === "working",
    showTimer: status === "working",
  });
  estado.append(lattice.elemento);
  pintarLattice(lattice.elemento);
}

function limparLattice() {
  lattice?.parar();
  lattice = null;
  estado.replaceChildren();
  estado.hidden = true;
}

function mostrar(resultado) {
  document.querySelector("#aceitas").textContent = resultado.aceitas;
  document.querySelector("#recusadas").textContent = resultado.recusadas;
  document.querySelector("#liquido").textContent = reais(resultado.total_liquido_centavos);
  loteId = resultado.id || "";
  contagens = resultado.contagens || null;
  totalLista = resultado.total_lista ?? resultado.linhas.length;
  linhasAtuais = resultado.linhas;
  filtro = "todas";
  vista = "aceitas";
  busca = "";
  valorMin = "";
  valorMax = "";
  ordem = "";
  document.querySelector("#busca").value = "";
  document.querySelector("#valor-min").value = "";
  document.querySelector("#valor-max").value = "";
  paginas.aceitas = 0;
  paginas.recusadas = 0;
  marcarTamanho();
  marcarOrdem();
  resumo.hidden = false;
  listas.hidden = false;
  montarFiltro();
  desenhar();
}

function aplicarTema(tema) {
  const bege = tema === "bege";
  document.documentElement.dataset.tema = bege ? "bege" : "preto";
  try {
    localStorage.setItem("antecipe-tema", document.documentElement.dataset.tema);
  } catch {
    /* o tema segue só nesta visita */
  }
  document.querySelectorAll("button.tema").forEach((botao) => {
    botao.setAttribute("aria-pressed", bege ? "true" : "false");
    botao.setAttribute("aria-label", bege ? "Usar tema preto" : "Usar tema bege");
  });
  fundo.__ajuste?.(SCANNER[document.documentElement.dataset.tema]);
  document.querySelector(".fundo-topo")?.__ajuste?.(opcoesTopografia(document.documentElement.dataset.tema));
  pintarLattice(document.querySelector(".lattice-loader"));
  const moldura = document.querySelector("#dock .dock");
  if (moldura) pintarDock(moldura);
}

function mostrarDock(visivel) {
  const anfitriao = document.querySelector("#dock");
  if (!anfitriao.querySelector(".dock")) return;
  anfitriao.hidden = false;
  anfitriao.classList.toggle("recolhido", !visivel);
}

function escolherVista(proxima) {
  if (proxima === vista && proxima !== "salvas") return;
  movimento = proxima === "recusadas" ? "recusa" : proxima === "aceitas" ? "aceite" : "pagina";
  vista = proxima;
  document.querySelector("#listas").hidden = false;
  document.querySelector("#ver-aceitas").setAttribute("aria-pressed", proxima === "aceitas" ? "true" : "false");
  document.querySelector("#ver-recusadas").setAttribute("aria-pressed", proxima === "recusadas" ? "true" : "false");
  document.querySelector("#ver-salvas").setAttribute("aria-pressed", proxima === "salvas" ? "true" : "false");
  mostrarDock(proxima === "recusadas");
  atualizar();
}

function desenhar() {
  document.querySelector("#ver-aceitas").setAttribute("aria-pressed", vista === "aceitas" ? "true" : "false");
  document.querySelector("#ver-recusadas").setAttribute("aria-pressed", vista === "recusadas" ? "true" : "false");
  document.querySelector("#ver-salvas").setAttribute("aria-pressed", vista === "salvas" ? "true" : "false");
  mostrarDock(vista === "recusadas");
  document.querySelector("#faixa").hidden = vista !== "aceitas";
  document.querySelector("#ordens").hidden = vista !== "aceitas";
  document.querySelector("#consulta-salva").hidden = vista !== "salvas";
  if (vista === "salvas") {
    desenharBloco(document.querySelector("#bloco-lista"), {
      linhas: linhasAtuais,
      total: totalLista,
      grupo: "salvas",
      marca: "linha-aceita",
      vazio: vazioSalvas(),
      colunas: ["Documento", "Cedente", "Sacado", "Vencimento", "Valor", "Registro"],
      celulas: (linha) => [
        linha.nu_documento || "—",
        linha.cedente || "—",
        linha.sacado || "—",
        linha.vencimento || "—",
        reais(linha.valor_centavos),
        linha.registro || "—",
      ],
    });
    return;
  }
  const regra = FILTROS.find((item) => item.id === filtro) ?? FILTROS[0];
  const categoria = document.querySelector("#categoria");
  if (vista === "recusadas") {
    categoria.hidden = false;
    categoria.textContent = `Categoria: ${regra.label}`;
  } else {
    categoria.hidden = true;
  }
  const locais = vista === "aceitas"
    ? ordenarLocais(linhasAtuais.filter((linha) => linha.aceita && combina(linha) && naFaixa(linha)))
    : linhasAtuais.filter((linha) => !linha.aceita && regra.casa(linha) && combina(linha));
  desenharBloco(document.querySelector("#bloco-lista"), {
    linhas: loteId ? linhasAtuais : locais,
    total: loteId ? totalLista : locais.length,
    grupo: vista,
    marca: vista === "aceitas" ? "linha-aceita" : "linha-recusada",
    vazio: vista === "aceitas"
      ? vazio("aceita")
      : busca.trim()
        ? "Nenhuma nota com esse documento."
        : filtro === "todas"
          ? "Nenhuma nota recusada."
          : "Nenhuma nota nesta categoria.",
    colunas: vista === "aceitas" ? ["Documento", "Líquido"] : ["Documento", "Motivo"],
    celulas: vista === "aceitas"
      ? (linha) => [linha.nu_documento || "—", reais(linha.liquido_centavos)]
      : (linha) => [linha.nu_documento || "—", linha.motivos.join(" · ")],
  });
}

function desenharBloco(elemento, bloco) {
  const direcao = movimento;
  movimento = "";
  elemento.replaceChildren();
  if (bloco.linhas.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "vazio";
    vazio.textContent = bloco.vazio;
    elemento.append(vazio);
  } else {
    const inicio = paginas[bloco.grupo] * porPagina;
    const fatia = loteId || bloco.grupo === "salvas" ? bloco.linhas : bloco.linhas.slice(inicio, inicio + porPagina);
    elemento.append(paginacao(bloco.grupo, inicio, fatia.length, bloco.total));
    elemento.append(tabela(bloco.colunas, fatia, bloco.celulas, bloco.marca));
  }
  animar(elemento, direcao);
}

function animar(elemento, direcao) {
  elemento.classList.remove("entra-aceite", "entra-recusa", "entra-pagina");
  if (!direcao) return;
  void elemento.offsetWidth;
  elemento.classList.add(direcao === "recusa" ? "entra-recusa" : direcao === "aceite" ? "entra-aceite" : "entra-pagina");
}

function tabela(colunas, linhas, celulas, marca) {
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
    tr.className = marca;
    for (const texto of celulas(linha)) tr.append(celula(texto));
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
  botaoPagina.className = "secundario";
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

async function atualizar() {
  if (vista === "salvas") {
    await atualizarSalvas();
    return;
  }
  if (!loteId) {
    desenhar();
    return;
  }
  const meu = ++pedido;
  const params = paramsConsulta(paginas[vista] + 1);
  try {
    const resposta = await fetch(`/lotes/${loteId}?${params}`);
    const json = await resposta.json().catch(() => ({}));
    if (meu !== pedido) return;
    if (!resposta.ok) {
      throw new Error(typeof json.detail === "string" ? json.detail : "Não foi possível abrir esta página.");
    }
    linhasAtuais = json.linhas;
    totalLista = json.total_lista;
    contagens = json.contagens;
    pintarContagens();
    desenhar();
  } catch (falha) {
    if (meu !== pedido) return;
    erro.hidden = false;
    erro.textContent = falha.message || "Não foi possível abrir esta página.";
  }
}

async function atualizarSalvas() {
  const meu = ++pedido;
  const params = new URLSearchParams({
    pagina: String(paginas.salvas + 1),
    tamanho: String(porPagina),
    busca,
    cedente,
    vencimento,
    registro,
  });
  try {
    const resposta = await fetch(`/carteira?${params}`);
    const json = await resposta.json().catch(() => ({}));
    if (meu !== pedido) return;
    if (!resposta.ok) {
      throw new Error(typeof json.detail === "string" ? json.detail : "Não foi possível consultar as notas salvas.");
    }
    linhasAtuais = json.linhas;
    totalLista = json.total_lista;
    desenhar();
  } catch (falha) {
    if (meu !== pedido) return;
    erro.hidden = false;
    erro.textContent = falha.message || "Não foi possível consultar as notas salvas.";
  }
}

function vazioSalvas() {
  if (busca.trim() || cedente.trim() || vencimento.trim() || registro.trim()) {
    return "Nenhuma nota salva com esse filtro.";
  }
  return "Nenhuma nota salva.";
}

function pintarContagens() {
  if (!contagens) return;
  for (const item of FILTROS) {
    const selo = document.querySelector(`#dock [data-id="${item.id}"] .dock-badge`);
    if (selo) selo.textContent = String(contagens[item.id] ?? 0);
  }
}

function montarFiltro() {
  const recusadas = linhasAtuais.filter((linha) => !linha.aceita);
  const anfitriao = document.querySelector("#dock");
  dock = montarDock(
    anfitriao,
    FILTROS.map((item) => ({
      ...item,
      contagem: contagens ? contagens[item.id] ?? 0 : recusadas.filter(item.casa).length,
    })),
    (id) => {
      filtro = id;
      paginas.recusadas = 0;
      dock.marcar(id);
      movimento = "pagina";
      atualizar();
    },
  );
  dock.marcar(filtro);
  mostrarDock(vista === "recusadas");
}

function paramsConsulta(pagina) {
  const params = new URLSearchParams({
    pagina: String(pagina),
    tamanho: String(porPagina),
    vista,
    filtro,
    busca,
  });
  if (vista !== "aceitas") return params;
  const minimo = centavosDe(valorMin);
  const maximo = centavosDe(valorMax);
  if (minimo != null) params.set("valor_min", String(minimo));
  if (maximo != null) params.set("valor_max", String(maximo));
  if (ordem) params.set("ordem", ordem);
  return params;
}

function centavosDe(texto) {
  const limpo = texto.trim();
  if (!limpo) return null;
  const numero = Number(limpo.replace(/\./g, "").replace(",", "."));
  if (!Number.isFinite(numero)) return null;
  return Math.round(numero * 100);
}

function naFaixa(linha) {
  const minimo = centavosDe(valorMin);
  const maximo = centavosDe(valorMax);
  if (minimo == null && maximo == null) return true;
  const valor = linha.liquido_centavos;
  if (valor == null) return false;
  if (minimo != null && valor < minimo) return false;
  if (maximo != null && valor > maximo) return false;
  return true;
}

function ordenarLocais(lista) {
  if (!ordem) return lista;
  return [...lista].sort((esquerda, direita) => {
    const a = esquerda.liquido_centavos ?? -1;
    const b = direita.liquido_centavos ?? -1;
    return ordem === "crescente" ? a - b : b - a;
  });
}

function marcarOrdem() {
  for (const botao of document.querySelectorAll("button[data-ordem]")) {
    botao.setAttribute("aria-pressed", botao.dataset.ordem === ordem ? "true" : "false");
  }
}

function combina(linha) {
  const termo = busca.trim().toLowerCase();
  if (!termo) return true;
  return (linha.nu_documento || "").toLowerCase().includes(termo);
}

function vazio(tipo) {
  if (busca.trim()) return "Nenhuma nota com esse documento.";
  if (tipo === "aceita" && (valorMin.trim() || valorMax.trim())) return "Nenhuma nota nessa faixa.";
  return tipo === "aceita" ? "Nenhuma nota aceita." : "Nenhuma nota recusada.";
}

function marcarTamanho() {
  for (const botao of document.querySelectorAll("button[data-tamanho]")) {
    botao.setAttribute("aria-pressed", Number(botao.dataset.tamanho) === porPagina ? "true" : "false");
  }
}

function tem(linha, codigo) {
  return (linha.codigos || []).includes(codigo);
}

function icone(nome) {
  const traco = "fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.6\" stroke-linecap=\"round\" stroke-linejoin=\"round\"";
  const formas = {
    todas: `<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/>`,
    tipo: `<path d="M5 7h14M5 12h14M5 17h9"/>`,
    valor: `<path d="M12 4v16"/><path d="M16 7.5c0-1.5-1.8-2.5-4-2.5s-4 1-4 2.5 1.8 2.5 4 2.5 4 1 4 2.5-1.8 2.5-4 2.5-4-1-4-2.5"/>`,
    prazo: `<circle cx="12" cy="12" r="7"/><path d="M12 8v4.5L15 15"/>`,
    cadastro: `<circle cx="12" cy="9" r="3"/><path d="M6.5 18.5c1-2.4 3-3.5 5.5-3.5s4.5 1.1 5.5 3.5"/>`,
    grupo: `<circle cx="8" cy="10" r="2.2"/><circle cx="16" cy="10" r="2.2"/><path d="M4.8 17.5c.6-1.8 1.8-2.7 3.2-2.7s2.6.9 3.2 2.7"/><path d="M12.8 17.5c.6-1.8 1.8-2.7 3.2-2.7s2.6.9 3.2 2.7"/>`,
    duplicata: `<rect x="7" y="6" width="11" height="13" rx="1.5"/><path d="M6 16.5V5.5A1.5 1.5 0 0 1 7.5 4H15"/>`,
  };
  return `<svg viewBox="0 0 24 24" width="15" height="15" ${traco}>${formas[nome]}</svg>`;
}

function reais(centavos) {
  if (centavos == null) return "";
  const negativo = centavos < 0;
  const absoluto = Math.abs(centavos);
  const inteiros = Math.floor(absoluto / 100).toLocaleString("pt-BR");
  const frac = String(absoluto % 100).padStart(2, "0");
  return `${negativo ? "-" : ""}R$ ${inteiros},${frac}`;
}
