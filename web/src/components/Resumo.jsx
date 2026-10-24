import { reais } from "../reais";

export function Resumo({ resultado }) {
  return (
    <section className="resumo">
      <p>
        <span>Aceitas</span>
        <strong>{resultado.aceitas}</strong>
      </p>
      <p>
        <span>Recusadas</span>
        <strong>{resultado.recusadas}</strong>
      </p>
      <p>
        <span>Líquido do lote</span>
        <strong>{reais(resultado.total_liquido_centavos)}</strong>
      </p>
      <p>
        <span>Face que ficou de fora</span>
        <strong>{reais(resultado.total_face_recusado_centavos)}</strong>
      </p>
    </section>
  );
}
