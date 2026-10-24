import { useMemo, useState } from "react";
import { enviarExemplo, enviarLote } from "./api";
import { Envio } from "./components/Envio";
import { ListaNotas } from "./components/ListaNotas";
import { Resumo } from "./components/Resumo";

export default function App() {
  const [arquivo, setArquivo] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar() {
    await executar(() => enviarLote(arquivo));
  }

  async function aoExemplo() {
    await executar(enviarExemplo);
  }

  async function executar(pedido) {
    setEnviando(true);
    setErro("");
    try {
      setResultado(await pedido());
    } catch (falha) {
      setResultado(null);
      setErro(falha.message || "Não foi possível ler o lote.");
    } finally {
      setEnviando(false);
    }
  }

  const aceitas = useMemo(() => resultado?.linhas.filter((linha) => linha.aceita) ?? [], [resultado]);
  const recusadas = useMemo(() => resultado?.linhas.filter((linha) => !linha.aceita) ?? [], [resultado]);

  return (
    <main>
      <header>
        <p className="marca">Antecipe FIDC</p>
        <h1>Lote de recebíveis</h1>
      </header>
      <Envio arquivo={arquivo} aoEscolher={setArquivo} aoEnviar={aoEnviar} aoExemplo={aoExemplo} enviando={enviando} />
      {erro ? <p className="erro">{erro}</p> : null}
      {resultado ? (
        <>
          <Resumo resultado={resultado} />
          <ListaNotas titulo="Aceitas" linhas={aceitas} vazio="Nenhuma nota aceita." modo="aceitas" />
          <ListaNotas titulo="Recusadas" linhas={recusadas} vazio="Nenhuma nota recusada." modo="recusadas" />
        </>
      ) : null}
    </main>
  );
}
