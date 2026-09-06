"use client";

/**
 * Feedbacks pendentes da equipe (SCR-0027 / SCR-0031).
 *
 * Tela própria, e não uma coluna de Minha equipe, porque a pergunta é outra. Lá se vê
 * "Diego deve 1"; aqui se vê "Diego deve o feedback sobre a Bruna, com prazo 13/09". Com
 * quatro pessoas dá no mesmo; com trinta, é a lista de pedidos que permite cobrar item a
 * item — que é para isso que o gestor abre a tela.
 *
 * O que **você** deve fica em Meus feedbacks. Misturar as duas coisas faria o gestor
 * cobrar a si mesmo no meio da lista da equipe, e o servidor já tira quem está olhando.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  BarraDeFiltros,
  BotaoDeExportar,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
  EstadoVazio,
  FiltroSelecao,
  Linha,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { exportarCsv } from "@/lib/exportar";
import { formatarData, ROTULO_DO_REQUEST } from "@/lib/formato";
import { useTabela } from "@/lib/tabela";
import type { PendentesDaEquipe } from "@/lib/tipos";

type Pendente = PendentesDaEquipe["pendentes"][number];

export default function FeedbacksPendentes() {
  const [dados, setDados] = useState<PendentesDaEquipe | null>(null);
  const [aviso, setAviso] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [lembrando, setLembrando] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setDados(await api<PendentesDaEquipe>("/team/pending"));
  }, []);

  useEffect(() => {
    carregar().catch(() =>
      setDados({ cycle_id: null, cycle_name: null, pendentes: [] }),
    );
  }, [carregar]);

  const pendentes = dados?.pendentes ?? [];

  const tabela = useTabela(pendentes, {
    busca: (p) => [p.giver_name, p.receiver_name],
    campos: {
      avaliador: (p) => p.giver_name,
      avaliado: (p) => p.receiver_name,
      status: (p) => ROTULO_DO_REQUEST[p.status] ?? p.status,
      prazo: (p) => p.due_date,
    },
    // Prazo primeiro: quem está atrasado sobe, que é a ordem em que se cobra.
    inicial: { campo: "prazo" },
  });
  const porSituacao = tabela.filtro("situacao", (p, valor) =>
    valor === "atrasado" ? p.atrasado : !p.atrasado,
  );
  const visiveis = tabela.visiveis([porSituacao]);
  const atrasados = pendentes.filter((p) => p.atrasado).length;

  async function lembrar(pendente: Pendente) {
    setAviso(null);
    setLembrando(pendente.request_id);
    try {
      // O lembrete é por pessoa, não por pedido: ela recebe um aviso com a contagem do
      // que deve. Mandar um por linha encheria o sino de quem já sabe que está devendo.
      const resposta = await api<{ pendentes: number; mensagem: string }>(
        `/team/${pendente.giver_id}/reminder`,
        { method: "POST" },
      );
      setAviso({
        tom: resposta.pendentes > 0 ? "sucesso" : "erro",
        texto:
          resposta.pendentes > 0
            ? `${pendente.giver_name} foi lembrado(a) dos ${resposta.pendentes} feedback(s) que deve.`
            : `${pendente.giver_name} está em dia. ${resposta.mensagem}`,
      });
    } catch (falha) {
      setAviso({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível lembrar agora.",
      });
    } finally {
      setLembrando(null);
    }
  }

  function exportar() {
    exportarCsv(
      "feedbacks-pendentes",
      ["Avaliador", "Avaliado", "Status", "Prazo", "Atrasado"],
      visiveis.map((p) => [
        p.giver_name,
        p.receiver_name,
        ROTULO_DO_REQUEST[p.status] ?? p.status,
        formatarData(p.due_date),
        p.atrasado ? "sim" : "não",
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Feedbacks pendentes"
      descricao={
        dados?.cycle_name
          ? `O que a sua equipe ainda precisa enviar no ciclo ${dados.cycle_name}.`
          : "O que a sua equipe ainda precisa enviar no ciclo atual."
      }
    >
      <div className="space-y-4">
        {aviso && <Aviso tom={aviso.tom}>{aviso.texto}</Aviso>}

        {atrasados > 0 && (
          <Aviso tom="erro">
            {atrasados === 1
              ? "1 feedback já passou do prazo."
              : `${atrasados} feedbacks já passaram do prazo.`}
          </Aviso>
        )}

        <Cartao>
          {dados === null ? (
            <Carregando />
          ) : pendentes.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum feedback pendente"
              descricao={
                dados.cycle_id === null
                  ? "Não há ciclo aberto. Quando a administração abrir um, os pedidos da sua equipe aparecem aqui."
                  : "Sua equipe está em dia neste ciclo."
              }
            />
          ) : (
            <>
              <BarraDeFiltros
                busca={tabela.busca}
                aoBuscar={tabela.setBusca}
                placeholder="Buscar por nome…"
                acoes={
                  <>
                    <ContadorDeResultados mostrando={visiveis.length} total={pendentes.length} />
                    <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                  </>
                }
              >
                <FiltroSelecao
                  rotuloDeTodos="Todos os prazos"
                  valor={porSituacao.valor}
                  aoMudar={porSituacao.aoMudar}
                  opcoes={[
                    { valor: "atrasado", rotulo: "Atrasados" },
                    { valor: "no-prazo", rotulo: "No prazo" },
                  ]}
                />
              </BarraDeFiltros>

              <Tabela
                ordenacao={tabela.ordenacao}
                vazio={visiveis.length === 0}
                vazioTexto="Nenhum feedback com esses filtros."
                colunas={[
                  { rotulo: "Quem deve", campo: "avaliador" },
                  { rotulo: "Sobre quem", campo: "avaliado" },
                  { rotulo: "Status", campo: "status" },
                  { rotulo: "Prazo", campo: "prazo" },
                  "",
                ]}
              >
                {visiveis.map((pendente) => (
                  <Linha key={pendente.request_id}>
                    <Celula className="font-medium">{pendente.giver_name}</Celula>
                    <Celula>{pendente.receiver_name}</Celula>
                    <Celula>
                      <Selo tom={pendente.status === "draft" ? "neutro" : "alerta"}>
                        {ROTULO_DO_REQUEST[pendente.status] ?? pendente.status}
                      </Selo>
                    </Celula>
                    <Celula>
                      {formatarData(pendente.due_date)}
                      {/* O atraso vem do servidor (BR-MIGRAR-007); aqui só se marca. */}
                      {pendente.atrasado && (
                        <span className="ml-2 text-xs font-medium text-destructive">atrasado</span>
                      )}
                    </Celula>
                    <Celula className="text-right">
                      <button
                        type="button"
                        onClick={() => void lembrar(pendente)}
                        disabled={lembrando === pendente.request_id}
                        className="text-sm text-primary underline-offset-4 hover:underline disabled:opacity-50"
                      >
                        {lembrando === pendente.request_id ? "Lembrando…" : "Lembrar"}
                      </button>
                    </Celula>
                  </Linha>
                ))}
              </Tabela>
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
