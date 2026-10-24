import { useEffect, useState } from "react";
import { reais } from "../reais";

const POR_PAGINA = 50;

export function ListaNotas({ titulo, linhas, vazio, modo }) {
  const [pagina, setPagina] = useState(0);

  useEffect(() => {
    setPagina(0);
  }, [linhas]);

  const inicio = pagina * POR_PAGINA;
  const fatia = linhas.slice(inicio, inicio + POR_PAGINA);
  const colunas = modo === "aceitas" ? ["Documento", "Líquido"] : ["Documento", "Motivo"];

  return (
    <section className="bloco">
      <h2>{titulo}</h2>
      {linhas.length === 0 ? (
        <p className="vazio">{vazio}</p>
      ) : (
        <>
          <table className="notas">
            <thead>
              <tr>
                {colunas.map((coluna) => (
                  <th key={coluna}>{coluna}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fatia.map((linha, indice) => (
                <tr key={`${linha.nu_documento}-${inicio + indice}`}>
                  <td>{linha.nu_documento || "—"}</td>
                  <td>{modo === "aceitas" ? reais(linha.liquido_centavos) : linha.motivos.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="paginas">
            <button type="button" disabled={inicio === 0} onClick={() => setPagina((atual) => atual - 1)}>
              Anterior
            </button>
            <span>
              {inicio + 1}–{inicio + fatia.length} de {linhas.length}
            </span>
            <button
              type="button"
              disabled={inicio + fatia.length >= linhas.length}
              onClick={() => setPagina((atual) => atual + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </section>
  );
}
