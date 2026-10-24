const ORBITA = { cells: [0, 1, 2, 7, null, 3, 6, 5, 4], loop: 8, scale: 1.2 };
const MARCAS = { done: [2, 3, 5, 7], error: [0, 2, 4, 6, 8] };

function tempo(milissegundos) {
  const segundos = milissegundos / 1000;
  const casas = segundos < 10 ? 2 : 1;
  return `${segundos.toFixed(casas).replace(".", ",")} s`;
}

export function criarLattice({
  label = "Lendo o CSV",
  doneLabel = "Lote lido em",
  errorLabel = "Falha na leitura",
  status = "working",
  color = "#f4f4f5",
  errorColor = "#d4d4d8",
  glow = false,
  showTimer = true,
} = {}) {
  const passo = 90 * ORBITA.scale;
  const ciclo = Math.round(ORBITA.loop * passo);
  const raiz = document.createElement("span");
  raiz.className = "lattice-loader";
  raiz.setAttribute("role", "status");
  raiz.dataset.status = status;
  raiz.dataset.shape = "round";
  if (glow) raiz.dataset.glow = "";
  raiz.style.setProperty("--ll-n", "3");
  raiz.style.setProperty("--ll-cell", "6px");
  raiz.style.setProperty("--ll-gap", "2px");
  raiz.style.setProperty("--ll-font", "15px");
  raiz.style.setProperty("--ll-color", color);
  raiz.style.setProperty("--ll-mark", status === "error" ? errorColor : "#e4e4e7");
  raiz.style.setProperty("--ll-idle", "0.15");
  raiz.style.setProperty("--ll-glow", color);
  raiz.style.setProperty("--ll-mark-glow", errorColor);
  raiz.style.setProperty("--ll-cycle", `${ciclo}ms`);

  const grade = document.createElement("span");
  grade.className = "lattice-loader__grid";
  grade.setAttribute("aria-hidden", "true");
  const corrida = document.createElement("span");
  corrida.className = "lattice-loader__layer lattice-loader__run";
  const marca = document.createElement("span");
  marca.className = "lattice-loader__layer lattice-loader__mark";
  const acesas = MARCAS[status === "error" ? "error" : "done"];
  ORBITA.cells.forEach((unidade, indice) => {
    const celula = document.createElement("span");
    celula.className = "lattice-loader__cell";
    if (unidade == null) celula.dataset.hole = "";
    else celula.style.animationDelay = `${Math.round(unidade * passo)}ms`;
    corrida.append(celula);
    const fixa = document.createElement("span");
    fixa.className = "lattice-loader__cell";
    if (acesas.includes(indice)) fixa.dataset.on = "";
    marca.append(fixa);
  });
  grade.append(corrida, marca);

  const rotulo = document.createElement("span");
  rotulo.className = "lattice-loader__label";
  rotulo.setAttribute("aria-hidden", "true");
  const textoTrabalho = document.createElement("span");
  textoTrabalho.className = "lattice-loader__text";
  textoTrabalho.textContent = label;
  const textoPronto = document.createElement("span");
  textoPronto.className = "lattice-loader__text";
  textoPronto.textContent = doneLabel;
  const textoErro = document.createElement("span");
  textoErro.className = "lattice-loader__text";
  textoErro.textContent = errorLabel;
  if (status === "working") textoTrabalho.dataset.active = "";
  if (status === "done") textoPronto.dataset.active = "";
  if (status === "error") textoErro.dataset.active = "";
  rotulo.append(textoTrabalho, textoPronto, textoErro);

  const leitor = document.createElement("span");
  leitor.className = "lattice-loader__sr";
  leitor.textContent = status === "working" ? `${label}, em andamento` : errorLabel;

  raiz.append(grade, rotulo);
  let relogio = null;
  if (showTimer) {
    relogio = document.createElement("span");
    relogio.className = "lattice-loader__timer";
    relogio.setAttribute("aria-hidden", "true");
    relogio.textContent = "0,00 s";
    raiz.append(relogio);
  }
  raiz.append(leitor);

  let intervalo = 0;
  let decorrido = 0;
  const inicio = performance.now();
  if (status === "working" && relogio) {
    intervalo = window.setInterval(() => {
      decorrido = performance.now() - inicio;
      relogio.textContent = tempo(decorrido);
    }, 100);
  }

  return {
    elemento: raiz,
    parar() {
      window.clearInterval(intervalo);
    },
    concluir() {
      window.clearInterval(intervalo);
      decorrido = performance.now() - inicio;
      if (relogio) relogio.textContent = tempo(decorrido);
      raiz.dataset.status = "done";
      delete raiz.dataset.glow;
      delete textoTrabalho.dataset.active;
      delete textoErro.dataset.active;
      textoPronto.dataset.active = "";
      leitor.textContent = `${doneLabel} ${tempo(decorrido)}`;
    },
  };
}
