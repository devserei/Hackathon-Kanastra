import { useMemo, useState } from "react";
import { enviarLote } from "./api";
import { Envio } from "./components/Envio";
import LatticeLoader from "./components/LatticeLoader";
import { ListaNotas } from "./components/ListaNotas";
import { Resumo } from "./components/Resumo";
import Scanner from "./components/Scanner";

export default function App() {
  const [arquivo, setArquivo] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar() {
    await executar(() => enviarLote(arquivo));
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
    <>
      <div className="fundo">
        <Scanner
          color1="#f4f4f5"
          color2="#71717a"
          color3="#d4d4d8"
          brightness={0.45}
          glow={0.28}
          vignette={0.62}
          scanlineIntensity={0.22}
          grainIntensity={0.035}
          opacity={0.85}
          lightMode={false}
        />
      </div>
      <main>
        <header>
          <p className="marca">Antecipe FIDC</p>
          <h1>Lote de recebíveis</h1>
        </header>
        <Envio arquivo={arquivo} aoEscolher={setArquivo} aoEnviar={aoEnviar} enviando={enviando} />
        {enviando ? (
          <div className="estado">
            <LatticeLoader
              label="Lendo o CSV"
              doneLabel="Lote lido em"
              errorLabel="Falha após"
              status="working"
              color="#f4f4f5"
              doneColor="#e4e4e7"
              errorColor="#a1a1aa"
              glow
              fontSize={15}
            />
          </div>
        ) : null}
        {erro ? (
          <div className="estado">
            <LatticeLoader
              label="Lendo o CSV"
              errorLabel="Falha na leitura"
              status="error"
              showTimer={false}
              color="#f4f4f5"
              errorColor="#d4d4d8"
              fontSize={15}
            />
            <p className="erro">{erro}</p>
          </div>
        ) : null}
        {resultado ? (
          <>
            <Resumo resultado={resultado} />
            <ListaNotas titulo="Aceitas" linhas={aceitas} vazio="Nenhuma nota aceita." modo="aceitas" />
            <ListaNotas titulo="Recusadas" linhas={recusadas} vazio="Nenhuma nota recusada." modo="recusadas" />
          </>
        ) : null}
      </main>
    </>
  );
}
