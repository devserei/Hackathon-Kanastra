export function reais(centavos) {
  if (centavos == null) {
    return "";
  }
  const negativo = centavos < 0;
  const absoluto = Math.abs(centavos);
  const inteiros = Math.floor(absoluto / 100).toLocaleString("pt-BR");
  const frac = String(absoluto % 100).padStart(2, "0");
  return `${negativo ? "-" : ""}R$ ${inteiros},${frac}`;
}
