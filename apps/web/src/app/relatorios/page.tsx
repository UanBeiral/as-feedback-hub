"use client";

/**
 * Relatórios — 360, clientes e engajamento, mais as exportações.
 *
 * Os números vêm prontos do servidor. É a diferença central em relação ao legado, que
 * baixava as linhas e agregava no browser: três telas calculavam progresso de três
 * jeitos e discordavam entre si (BR-MIGRAR-009/028).
 *
 * CSV baixa na hora; PDF e XLSX viram job no worker e aparecem na lista de exportações
 * quando ficam prontos (AD-07). O download passa pelo client autenticado — link direto
 * não funcionaria, porque o arquivo exige Bearer e ser o dono do pedido.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  Progresso,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api, apiBlob } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type {
  JobDeExportacao,
  Linha360,
  LinhaDeCliente,
  LinhaDeEngajamento,
} from "@/lib/tipos";

type Aba = "360" | "clientes" | "engajamento";

export default function Relatorios() {
  const [aba, setAba] = useState<Aba>("360");
  const [linhas360, setLinhas360] = useState<Linha360[] | null>(null);
  const [clientes, setClientes] = useState<LinhaDeCliente[] | null>(null);
  const [engajamento, setEngajamento] = useState<LinhaDeEngajamento[] | null>(null);
  const [exportacoes, setExportacoes] = useState<JobDeExportacao[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregarExportacoes = useCallback(async () => {
    setExportacoes(await api<JobDeExportacao[]>("/reports/exports"));
  }, []);

  useEffect(() => {
    api<Linha360[]>("/reports/feedback-360").then(setLinhas360).catch(() => setLinhas360([]));
    api<LinhaDeEngajamento[]>("/reports/engagement")
      .then(setEngajamento)
      .catch(() => setEngajamento([]));
    api<LinhaDeCliente[]>("/reports/clients")
      .then(setClientes)
      .catch((falha) => {
        // 403 aqui é a capacidade `can_generate_reports` faltando — a aba fica visível
        // e explica, em vez de sumir e deixar a pessoa achando que é bug.
        setClientes([]);
        if (falha instanceof ApiError && falha.status === 403) {
          setMensagem({
            tom: "erro",
            texto: "Você não tem a capacidade de gerar relatórios de clientes.",
          });
        }
      });
    carregarExportacoes().catch(() => setExportacoes([]));
  }, [carregarExportacoes]);

  async function baixarCsv(caminho: string, nome: string) {
    const blob = await apiBlob(caminho);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function pedirExportacao(kind: string, format: "xlsx" | "pdf") {
    setMensagem(null);
    try {
      await api("/reports/exports", { method: "POST", body: { kind, format, filters: {} } });
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
      descricao="Os mesmos números que aparecem nos painéis — calculados uma vez, no servidor."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <nav className="flex gap-2">
          {(
            [
              ["360", "Feedback 360"],
              ["clientes", "Clientes"],
              ["engajamento", "Engajamento"],
            ] as const
          ).map(([chave, rotulo]) => (
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
          <Cartao
            titulo="Feedback 360 por pessoa"
            acao={
              <span className="flex gap-2">
                <Botao
                  variante="secundario"
                  onClick={() => void baixarCsv("/reports/feedback-360.csv", "feedback-360.csv")}
                >
                  Baixar CSV
                </Botao>
                <Botao variante="fantasma" onClick={() => void pedirExportacao("report_360", "xlsx")}>
                  Gerar XLSX
                </Botao>
              </span>
            }
          >
            {linhas360 === null ? (
              <Carregando />
            ) : linhas360.length === 0 ? (
              <EstadoVazio titulo="Sem dados de 360 ainda" />
            ) : (
              <Tabela colunas={["Pessoa", "Departamento", "Recebidos", "Conclusão", "Nota média"]}>
                {linhas360.map((linha) => (
                  <Linha key={linha.profile_id}>
                    <Celula className="font-medium">{linha.nome}</Celula>
                    <Celula>{linha.departamento ?? "—"}</Celula>
                    <Celula>
                      {linha.respondidos}/{linha.recebidos}
                    </Celula>
                    <Celula className="w-48">
                      <Progresso valor={linha.percentual} />
                    </Celula>
                    <Celula>{linha.media_nota ?? "—"}</Celula>
                  </Linha>
                ))}
              </Tabela>
            )}
          </Cartao>
        )}

        {aba === "clientes" && (
          <Cartao
            titulo="Avaliações de clientes"
            acao={
              <Botao variante="fantasma" onClick={() => void pedirExportacao("client", "xlsx")}>
                Gerar XLSX
              </Botao>
            }
          >
            {clientes === null ? (
              <Carregando />
            ) : clientes.length === 0 ? (
              <EstadoVazio titulo="Sem avaliações de clientes" />
            ) : (
              <Tabela colunas={["Pessoa", "Avaliações", "Respondidas", "Nota média", "Negativas"]}>
                {clientes.map((linha) => (
                  <Linha key={linha.profile_id}>
                    <Celula className="font-medium">{linha.nome}</Celula>
                    <Celula>{linha.avaliacoes}</Celula>
                    <Celula>{linha.respondidas}</Celula>
                    <Celula>{linha.media_geral ?? "—"}</Celula>
                    <Celula>
                      {linha.negativas > 0 ? (
                        <Selo tom="perigo">{linha.negativas}</Selo>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </Celula>
                  </Linha>
                ))}
              </Tabela>
            )}
          </Cartao>
        )}

        {aba === "engajamento" && (
          <Cartao
            titulo="Engajamento"
            descricao="Só ciclos fechados entram, e quem nunca teve pedido fica fora da conta."
            acao={
              <span className="flex gap-2">
                <Botao
                  variante="secundario"
                  onClick={() => void baixarCsv("/reports/engagement.csv", "engajamento.csv")}
                >
                  Baixar CSV
                </Botao>
                <Botao variante="fantasma" onClick={() => void pedirExportacao("engagement", "xlsx")}>
                  Gerar XLSX
                </Botao>
              </span>
            }
          >
            {engajamento === null ? (
              <Carregando />
            ) : engajamento.length === 0 ? (
              <EstadoVazio
                titulo="Nenhum ciclo fechado ainda"
                descricao="O engajamento só considera ciclos já encerrados."
              />
            ) : (
              <Tabela colunas={["Pessoa", "Solicitados", "Enviados", "Engajamento"]}>
                {engajamento.map((linha) => (
                  <Linha key={linha.profile_id}>
                    <Celula className="font-medium">{linha.nome}</Celula>
                    <Celula>{linha.solicitados}</Celula>
                    <Celula>{linha.enviados}</Celula>
                    <Celula className="w-48">
                      <Progresso valor={linha.percentual} />
                    </Celula>
                  </Linha>
                ))}
              </Tabela>
            )}
          </Cartao>
        )}

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
                          void baixarCsv(
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
