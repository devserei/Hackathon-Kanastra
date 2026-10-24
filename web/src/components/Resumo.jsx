import { reais } from "../reais";

export function Resumo({ resultado }) {
  return (
    <section className="resumo">
      <p className="barra-aceita">
        <span>Aceitas</span>
        <strong>{resultado.aceitas}</strong>
      </p>
      <p className="barra-recusada">
        <span>Recusadas</span>
        <strong>{resultado.recusadas}</strong>
      </p>
      <p>
        <span>Líquido do lote</span>
        <strong>{reais(resultado.total_liquido_centavos)}</strong>
      </p>
    </section>
  );
}
