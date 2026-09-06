"use client";

/**
 * Relatórios — 360, clientes, feedback livre e engajamento, mais as exportações.
 *
 * Os números vêm prontos do servidor. É a diferença central em relação ao legado, que
 * baixava as linhas e agregava no browser: três telas calculavam progresso de três
 * jeitos e discordavam entre si (BR-MIGRAR-009/028).
 *
 * Há dois tipos de filtro na tela, e a divisão não é arbitrária. Ciclo, departamento e
 * período mudam **o que o servidor agrega** — filtrar depois daria média de gente que o
 * filtro devia ter tirado da conta. Busca e ordenação mexem só na apresentação das
 * linhas já agregadas, e por isso ficam no navegador, sem ida ao servidor a cada tecla.
 *
 * CSV baixa na hora com o que está na tela; PDF e XLSX viram job no worker e aparecem na
 * lista de exportações quando ficam prontos (AD-07). O download passa pelo client
 * autenticado — link direto não funcionaria, porque o arquivo exige Bearer e ser o dono
 * do pedido.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Cartao,
  Celula,
  EstadoVazio,
  FiltroDeData,
  FiltroSelecao,
  Linha,
  Progresso,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api, apiBlob } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type {
  Ciclo,
  Colega,
  Departamento,
  JobDeExportacao,
  Linha360,
  LinhaDeCliente,
  LinhaDeEngajamento,
  LinhaDeFeedbackLivre,
} from "@/lib/tipos";

import { AbaDeRelatorio, type ColunaDeRelatorio } from "./aba";
import { EmitirRelatorio } from "./executivo";

type Aba = "360" | "clientes" | "livres" | "engajamento";

const ABAS: [Aba, string][] = [
  ["360", "Feedback 360"],
  ["clientes", "Clientes"],
  ["livres", "Livres"],
  ["engajamento", "Engajamento"],
];

const COLUNAS_360: ColunaDeRelatorio<Linha360>[] = [
  { chave: "nome", rotulo: "Pessoa", valor: (l) => l.nome, className: "font-medium", fixa: true },
  { chave: "departamento", rotulo: "Departamento", valor: (l) => l.departamento },
  { chave: "recebidos", rotulo: "Recebidos", valor: (l) => l.recebidos },
  { chave: "respondidos", rotulo: "Respondidos", valor: (l) => l.respondidos },
  {
    chave: "percentual",
    rotulo: "Conclusão",
    valor: (l) => l.percentual,
    celula: (l) => <Progresso valor={l.percentual} />,
    className: "w-48",
  },
  { chave: "media", rotulo: "Nota média", valor: (l) => l.media_nota },
];

const COLUNAS_CLIENTES: ColunaDeRelatorio<LinhaDeCliente>[] = [
  { chave: "nome", rotulo: "Pessoa", valor: (l) => l.nome, className: "font-medium", fixa: true },
  { chave: "avaliacoes", rotulo: "Avaliações", valor: (l) => l.avaliacoes },
  { chave: "respondidas", rotulo: "Respondidas", valor: (l) => l.respondidas },
  { chave: "media", rotulo: "Nota média", valor: (l) => l.media_geral },
  {
    chave: "negativas",
    rotulo: "Negativas",
    valor: (l) => l.negativas,
    celula: (l) =>
      l.negativas > 0 ? (
        <Selo tom="perigo">{l.negativas}</Selo>
      ) : (
        <span className="text-muted-foreground">0</span>
      ),
  },
];

const COLUNAS_LIVRES: ColunaDeRelatorio<LinhaDeFeedbackLivre>[] = [
  { chave: "nome", rotulo: "Pessoa", valor: (l) => l.nome, className: "font-medium", fixa: true },
  { chave: "recebidos", rotulo: "Recebidos", valor: (l) => l.recebidos },
  { chave: "enviados", rotulo: "Enviados", valor: (l) => l.enviados },
  {
    chave: "anonimos",
    rotulo: "Anônimos",
    valor: (l) => l.anonimos,
    // Anônimo não tem autor no banco (AMB-001): conta para quem recebeu e para ninguém
    // como remetente.
    className: "text-muted-foreground",
  },
  {
    chave: "sensiveis",
    rotulo: "Sensíveis",
    valor: (l) => l.sensiveis,
    celula: (l) =>
      l.sensiveis > 0 ? (
        <Selo tom="alerta">{l.sensiveis}</Selo>
      ) : (
        <span className="text-muted-foreground">0</span>
      ),
  },
];

const COLUNAS_ENGAJAMENTO: ColunaDeRelatorio<LinhaDeEngajamento>[] = [
  { chave: "nome", rotulo: "Pessoa", valor: (l) => l.nome, className: "font-medium", fixa: true },
  { chave: "solicitados", rotulo: "Solicitados", valor: (l) => l.solicitados },
  { chave: "enviados", rotulo: "Enviados", valor: (l) => l.enviados },
  {
    chave: "percentual",
    rotulo: "Engajamento",
    valor: (l) => l.percentual,
    celula: (l) => <Progresso valor={l.percentual} />,
    className: "w-48",
  },
];

export default function Relatorios() {
  const [aba, setAba] = useState<Aba>("360");
  const [linhas360, setLinhas360] = useState<Linha360[] | null>(null);
  const [clientes, setClientes] = useState<LinhaDeCliente[] | null>(null);
  const [engajamento, setEngajamento] = useState<LinhaDeEngajamento[] | null>(null);
  const [livres, setLivres] = useState<LinhaDeFeedbackLivre[] | null>(null);
  const [exportacoes, setExportacoes] = useState<JobDeExportacao[]>([]);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [departamentos, setDepartamentos] = useState<Departamento[]>([]);
  const [pessoas, setPessoas] = useState<Colega[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const [ciclo, setCiclo] = useState("");
  const [departamento, setDepartamento] = useState("");
  const [desde, setDesde] = useState("");
  const [ate, setAte] = useState("");
  const [soNegativas, setSoNegativas] = useState(false);

  const carregarExportacoes = useCallback(async () => {
    setExportacoes(await api<JobDeExportacao[]>("/reports/exports"));
  }, []);

  useEffect(() => {
    api<Ciclo[]>("/cycles")
      .then(setCiclos)
      .catch(() => setCiclos([]));
    api<Departamento[]>("/departments")
      .then(setDepartamentos)
      .catch(() => setDepartamentos([]));
    // `/colleagues` e não `/profiles`: a lista de nomes basta para o seletor, e a rota de
    // admin recusaria quem tem `can_generate_reports` sem ser admin.
    api<Colega[]>("/colleagues")
      .then(setPessoas)
      .catch(() => setPessoas([]));
    api<LinhaDeEngajamento[]>("/reports/engagement")
      .then(setEngajamento)
      .catch(() => setEngajamento([]));
    api<LinhaDeFeedbackLivre[]>("/reports/free-feedbacks")
      .then(setLivres)
      .catch(() => setLivres([]));
    carregarExportacoes().catch(() => setExportacoes([]));
  }, [carregarExportacoes]);

  useEffect(() => {
    setLinhas360(null);
    api<Linha360[]>("/reports/feedback-360", {
      query: { cycle_id: ciclo, department_id: departamento },
    })
      .then(setLinhas360)
      .catch(() => setLinhas360([]));
  }, [ciclo, departamento]);

  useEffect(() => {
    setClientes(null);
    api<LinhaDeCliente[]>("/reports/clients", {
      query: { desde, ate, apenas_negativas: soNegativas || undefined },
    })
      .then(setClientes)
      .catch((falha) => {
        // 403 aqui é a capacidade `can_generate_reports` faltando — a aba fica visível e
        // explica, em vez de sumir e deixar a pessoa achando que é bug.
        setClientes([]);
        if (falha instanceof ApiError && falha.status === 403) {
          setMensagem({
            tom: "erro",
            texto: "Você não tem a capacidade de gerar relatórios de clientes.",
          });
        }
      });
  }, [desde, ate, soNegativas]);

  async function baixarArquivo(caminho: string, nome: string) {
    const blob = await apiBlob(caminho);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function pedirExportacao(
    kind: string,
    format: "xlsx" | "pdf",
    filters: Record<string, string | boolean> = {},
  ) {
    setMensagem(null);
    try {
      // Os filtros vão junto: o worker refaz a consulta do zero, então sem eles o
      // arquivo sairia com o relatório inteiro e não com o que a pessoa viu na tela.
      await api("/reports/exports", { method: "POST", body: { kind, format, filters } });
      setMensagem({
        tom: "sucesso",
        texto: "Pedido registrado. O arquivo aparece aqui quando o worker terminar.",
      });
      await carregarExportacoes();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível pedir a exportação.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Relatórios"
      descricao="Gere relatórios personalizados com filtros, escolha de colunas e exportação em CSV."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <nav className="flex gap-2">
          {ABAS.map(([chave, rotulo]) => (
            <button
              key={chave}
              type="button"
              onClick={() => setAba(chave)}
              className={
                "rounded-md px-3 py-1.5 text-sm " +
                (aba === chave
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-muted")
              }
            >
              {rotulo}
            </button>
          ))}
        </nav>

        {aba === "360" && (
          <AbaDeRelatorio
            titulo="Feedback 360 por pessoa"
            itens={linhas360}
            chaveDe={(l) => l.profile_id}
            colunas={COLUNAS_360}
            buscaPor={(l) => [l.nome, l.departamento]}
            arquivo="feedback-360"
            vazio={{
              titulo: "Sem dados de 360 aqui",
              descricao: "Ninguém com pedidos de feedback nesse ciclo ou departamento.",
            }}
            filtros={
              <>
                <FiltroSelecao
                  valor={ciclo}
                  aoMudar={setCiclo}
                  rotuloDeTodos="Todos os ciclos"
                  opcoes={ciclos.map((c) => ({ valor: c.id, rotulo: c.name }))}
                />
                <FiltroSelecao
                  valor={departamento}
                  aoMudar={setDepartamento}
                  rotuloDeTodos="Todos os departamentos"
                  opcoes={departamentos.map((d) => ({ valor: d.id, rotulo: d.name }))}
                />
              </>
            }
            formatos={[
              {
                rotulo: "Gerar XLSX",
                aoConfirmar: () =>
                  pedirExportacao("report_360", "xlsx", {
                    ...(ciclo && { cycle_id: ciclo }),
                    ...(departamento && { department_id: departamento }),
                  }),
              },
            ]}
          />
        )}

        {aba === "clientes" && (
          <AbaDeRelatorio
            titulo="Avaliações de clientes"
            itens={clientes}
            chaveDe={(l) => l.profile_id}
            colunas={COLUNAS_CLIENTES}
            buscaPor={(l) => [l.nome]}
            arquivo="avaliacoes-de-clientes"
            vazio={{
              titulo: "Sem avaliações de clientes",
              descricao: "Nenhuma avaliação no período escolhido.",
            }}
            filtros={
              <>
                <FiltroDeData rotulo="De" valor={desde} aoMudar={setDesde} />
                <FiltroDeData rotulo="Até" valor={ate} aoMudar={setAte} />
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    checked={soNegativas}
                    onChange={(e) => setSoNegativas(e.target.checked)}
                    className="h-4 w-4 rounded border-input"
                  />
                  Só negativas
                </label>
              </>
            }
            formatos={[
              {
                rotulo: "Gerar XLSX",
                aoConfirmar: () =>
                  pedirExportacao("client", "xlsx", {
                    ...(desde && { desde }),
                    ...(ate && { ate }),
                    ...(soNegativas && { apenas_negativas: true }),
                  }),
              },
            ]}
          />
        )}

        {aba === "livres" && (
          <AbaDeRelatorio
            titulo="Feedback livre por pessoa"
            descricao="Recebidos e enviados lado a lado: é a reciprocidade que o relatório mostra."
            itens={livres}
            chaveDe={(l) => l.profile_id}
            colunas={COLUNAS_LIVRES}
            buscaPor={(l) => [l.nome]}
            arquivo="feedback-livre"
            vazio={{
              titulo: "Nenhum feedback livre ainda",
              descricao: "Feedback fora do ciclo aparece aqui assim que alguém enviar o primeiro.",
            }}
          />
        )}

        {aba === "engajamento" && (
          <AbaDeRelatorio
            titulo="Engajamento"
            descricao="Só ciclos fechados entram, e quem nunca teve pedido fica fora da conta."
            itens={engajamento}
            chaveDe={(l) => l.profile_id}
            colunas={COLUNAS_ENGAJAMENTO}
            buscaPor={(l) => [l.nome]}
            arquivo="engajamento"
            vazio={{
              titulo: "Nenhum ciclo fechado ainda",
              descricao: "O engajamento só considera ciclos já encerrados.",
            }}
            formatos={[
              { rotulo: "Gerar XLSX", aoConfirmar: () => pedirExportacao("engagement", "xlsx") },
            ]}
          />
        )}

        <EmitirRelatorio ciclos={ciclos} pessoas={pessoas} />

        <Cartao
          titulo="Minhas exportações"
          descricao="Arquivos pesados são gerados pelo worker e ficam disponíveis aqui."
        >
          {exportacoes.length === 0 ? (
            <EstadoVazio titulo="Nenhuma exportação pedida" />
          ) : (
            <Tabela colunas={["Tipo", "Formato", "Status", "Concluída em", ""]}>
              {exportacoes.map((job) => (
                <Linha key={job.id}>
                  <Celula>{job.kind}</Celula>
                  <Celula className="uppercase">{job.format}</Celula>
                  <Celula>
                    <Selo
                      tom={
                        job.status === "done"
                          ? "sucesso"
                          : job.status === "failed"
                            ? "perigo"
                            : "neutro"
                      }
                    >
                      {job.status}
                    </Selo>
                    {job.error && (
                      <span className="ml-2 text-xs text-destructive">{job.error}</span>
                    )}
                  </Celula>
                  <Celula>{formatarDataHora(job.completed_at)}</Celula>
                  <Celula className="text-right">
                    {job.download_path && (
                      <button
                        type="button"
                        onClick={() =>
                          void baixarArquivo(
                            `/reports/exports/${job.id}/download`,
                            `${job.kind}.${job.format}`,
                          )
                        }
                        className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                      >
                        Baixar
                      </button>
                    )}
                  </Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
