export async function enviarLote(arquivo) {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  const resposta = await fetch("/lotes", { method: "POST", body: dados });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = typeof corpo.detail === "string" ? corpo.detail : "Não foi possível ler o lote.";
    throw new Error(detalhe);
  }
  return corpo;
}

export async function enviarExemplo() {
  const resposta = await fetch("/lotes/exemplo", { method: "POST" });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = typeof corpo.detail === "string" ? corpo.detail : "Não foi possível ler o lote.";
    throw new Error(detalhe);
  }
  return corpo;
}
