const TEMAS = {
  preto: {
  "--dock-panel": "rgba(24, 24, 27, 0.72)",
  "--dock-panel-edge": "rgba(255, 255, 255, 0.08)",
  "--dock-panel-highlight": "rgba(255, 255, 255, 0.07)",
  "--dock-panel-shadow": "0 22px 44px -20px rgba(0, 0, 0, 0.8), 0 6px 16px -8px rgba(0, 0, 0, 0.5)",
  "--dock-tile": "linear-gradient(180deg, #3f3f46 0%, #18181b 100%)",
  "--dock-tile-edge": "rgba(255, 255, 255, 0.08)",
  "--dock-tile-highlight": "rgba(255, 255, 255, 0.12)",
  "--dock-tile-shadow": "0 4px 10px -4px rgba(0, 0, 0, 0.7)",
  "--dock-ink": "#f4f4f5",
  "--dock-label": "#18181b",
  "--dock-label-ink": "#f4f4f5",
  "--dock-dot": "#f4f4f5",
  "--dock-accent": "#a1a1aa",
  "--dock-badge": "#3f3f46",
  },
  bege: {
    "--dock-panel": "rgba(255, 253, 248, 0.92)",
    "--dock-panel-edge": "rgba(18, 12, 7, 0.1)",
    "--dock-panel-highlight": "rgba(255, 255, 255, 0.8)",
    "--dock-panel-shadow": "0 12px 28px -18px rgba(18, 12, 7, 0.4)",
    "--dock-tile": "linear-gradient(180deg, #fffdf8 0%, #e4dece 100%)",
    "--dock-tile-edge": "rgba(18, 12, 7, 0.12)",
    "--dock-tile-highlight": "rgba(255, 255, 255, 0.9)",
    "--dock-tile-shadow": "0 2px 6px -3px rgba(18, 12, 7, 0.28)",
    "--dock-ink": "#120c07",
    "--dock-label": "#f8f1e0",
    "--dock-label-ink": "#120c07",
    "--dock-dot": "#064e3b",
    "--dock-accent": "#047857",
    "--dock-badge": "#064e3b",
  },
};

export function pintarDock(elemento) {
  const tema = document.documentElement.dataset.tema === "bege" ? TEMAS.bege : TEMAS.preto;
  for (const [chave, valor] of Object.entries(tema)) elemento.style.setProperty(chave, valor);
}

const BASE = 36;

export function montarDock(anfitriao, itens, aoEscolher) {
  const dock = document.createElement("div");
  dock.className = "dock dock--bottom";
  dock.setAttribute("role", "toolbar");
  dock.setAttribute("aria-label", "Filtro das notas recusadas");
  dock.style.setProperty("--dock-base", `${BASE}px`);
  dock.style.setProperty("--dock-thickness", "36px");
  dock.style.setProperty("--dock-gap", "6px");
  dock.style.setProperty("--dock-pad", "0px");
  dock.style.setProperty("--dock-reach", "0px");
  dock.style.setProperty("--dock-round", "0.5");
  pintarDock(dock);

  const botoes = itens.map((item) => {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "dock-item";
    botao.setAttribute("aria-label", item.label);
    botao.dataset.id = item.id;
    const tile = document.createElement("span");
    tile.className = "dock-tile";
    const face = document.createElement("span");
    face.className = "dock-face";
    face.innerHTML = item.icone;
    const selo = document.createElement("span");
    selo.className = "dock-badge";
    selo.textContent = String(item.contagem);
    tile.append(face, selo);
    const ponto = document.createElement("span");
    ponto.className = "dock-dot";
    ponto.setAttribute("aria-hidden", "true");
    ponto.hidden = true;
    const rotulo = document.createElement("span");
    rotulo.className = "dock-label";
    rotulo.setAttribute("aria-hidden", "true");
    rotulo.textContent = item.label;
    botao.append(tile, ponto, rotulo);
    botao.addEventListener("click", () => aoEscolher(item.id));
    dock.append(botao);
    return { item, botao, tile, ponto };
  });

  anfitriao.replaceChildren(dock);

  return {
    marcar(id) {
      for (const entrada of botoes) {
        const ativo = entrada.item.id === id;
        entrada.ponto.hidden = !ativo;
        entrada.botao.setAttribute("aria-pressed", ativo ? "true" : "false");
      }
    },
  };
}
