export function Envio({ arquivo, aoEscolher, aoEnviar, aoExemplo, enviando }) {
  return (
    <form
      className="envio"
      onSubmit={(evento) => {
        evento.preventDefault();
        aoEnviar();
      }}
    >
      <label>
        CSV do lote
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(evento) => aoEscolher(evento.target.files?.[0] ?? null)}
        />
      </label>
      <button type="submit" disabled={!arquivo || enviando}>
        {enviando ? "Analisando…" : "Analisar lote"}
      </button>
      <button id="exemplo" type="button" disabled={enviando} onClick={aoExemplo}>
        Lote de exemplo
      </button>
    </form>
  );
}
