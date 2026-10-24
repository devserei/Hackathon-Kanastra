export function Envio({ arquivo, aoEscolher, aoEnviar, enviando }) {
  return (
    <form
      className="envio"
      onSubmit={(evento) => {
        evento.preventDefault();
        aoEnviar();
      }}
    >
      <label className="arquivo">
        <span>CSV do lote</span>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(evento) => aoEscolher(evento.target.files?.[0] ?? null)}
        />
        <strong>{arquivo ? arquivo.name : "Nenhum arquivo"}</strong>
      </label>
      <div className="acoes">
        <button type="submit" disabled={!arquivo || enviando}>
          Analisar lote
        </button>
      </div>
    </form>
  );
}
