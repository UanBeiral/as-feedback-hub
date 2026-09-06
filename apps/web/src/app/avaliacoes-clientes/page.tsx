"use client";

/**
 * Avaliações de clientes — pedir link e acompanhar respostas.
 *
 * O WhatsApp aparece mascarado para quem não é admin/RH, e o mascaramento é do
 * servidor (BR-MIGRAR-022): a tela mostra o que recebeu, sem ter o número completo em
 * lugar nenhum. Não adianta abrir o DevTools.
 *
 * O token só existe na resposta da criação — é dele que sai o link para mandar ao
 * cliente. Nas listagens ele não vem, porque quem vê a lista não precisa poder
 * responder no lugar do cliente.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  BarraDeFiltros,
  Botao,
  BotaoDeExportar,
  Campo,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
  Entrada,
  EstadoVazio,
  Estatistica,
  FiltroSelecao,
  Linha,
  Selecao,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { contemTexto, exportarCsv } from "@/lib/exportar";
import { formatarDataHora } from "@/lib/formato";
import { useTabela } from "@/lib/tabela";
import { temCapacidade, useSessao } from "@/lib/sessao";
import type { AvaliacaoDeCliente, Perfil } from "@/lib/tipos";

export default function AvaliacoesDeClientes() {
  const { usuario } = useSessao();
  const [avaliacoes, setAvaliacoes] = useState<AvaliacaoDeCliente[] | null>(null);
  const [equipe, setEquipe] = useState<Perfil[]>([]);
  const [link, setLink] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [pedido, setPedido] = useState({ target_user_id: "", client_name: "", client_whatsapp: "" });
  const [buscaDePessoa, setBuscaDePessoa] = useState("");

  const podePedir = temCapacidade(usuario, "can_request_client_feedback");
  const equipeFiltrada = equipe.filter((membro) =>
    contemTexto(`${membro.full_name} ${membro.job_title ?? ""}`, buscaDePessoa),
  );

  const carregar = useCallback(async () => {
    const [lista, membros] = await Promise.all([
      api<AvaliacaoDeCliente[]>("/client-eval/evaluations"),
      api<Perfil[]>("/auth/my-team"),
    ]);
    setAvaliacoes(lista);
    setEquipe(membros);
  }, []);

  useEffect(() => {
    carregar().catch(() => setAvaliacoes([]));
  }, [carregar]);

  async function pedir(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    setLink(null);
    try {
      const resposta = await api<{ public_path: string }>("/client-eval/requests", {
        method: "POST",
        body: {
          target_user_id: pedido.target_user_id,
          client_name: pedido.client_name || null,
          client_whatsapp: pedido.client_whatsapp || null,
        },
      });
      setLink(`${window.location.origin}${resposta.public_path}`);
      setMensagem({ tom: "sucesso", texto: "Link gerado. Copie e mande para o cliente." });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError && falha.status === 403
            ? "Você não tem a capacidade de pedir avaliação de cliente."
            : "Não foi possível gerar o link.",
      });
    }
  }

  function nomeDoAvaliado(profileId: string): string {
    return equipe.find((p) => p.id === profileId)?.full_name ?? "—";
  }

  const tabela = useTabela(avaliacoes ?? [], {
    busca: (a) => [a.client_name, a.client_whatsapp, nomeDoAvaliado(a.target_user_id)],
    campos: {
      cliente: (a) => a.client_name,
      profissional: (a) => nomeDoAvaliado(a.target_user_id),
      status: (a) => a.status_exibicao,
      nota: (a) => a.overall_rating,
      enviada: (a) => a.submitted_at,
    },
    inicial: { campo: "enviada", direcao: "desc" },
  });
  const porProfissional = tabela.filtro(
    "profissional",
    (a, valor) => a.target_user_id === valor,
  );
  const porStatus = tabela.filtro("status", (a, valor) => a.status === valor);
  const visiveis = tabela.visiveis([porProfissional, porStatus]);

  const pendentes = (avaliacoes ?? []).filter(
    (a) => a.status === "pending" || a.status === "in_progress",
  ).length;
  const respondidas = (avaliacoes ?? []).filter((a) => a.status === "submitted").length;
  const negativas = (avaliacoes ?? []).filter((a) => a.has_negative).length;

  function exportar() {
    exportarCsv(
      "avaliacoes-de-clientes",
      ["Cliente", "Profissional", "WhatsApp", "Status", "Nota", "Recomendação", "Negativa", "Enviada em"],
      visiveis.map((a) => [
        a.client_name ?? "",
        nomeDoAvaliado(a.target_user_id),
        a.client_whatsapp ?? "",
        a.status_exibicao,
        a.overall_rating ?? "",
        a.recommendation_rating ?? "",
        a.has_negative ? "sim" : "não",
        formatarDataHora(a.submitted_at),
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Avaliações de clientes"
      descricao="Solicite avaliações de clientes externos para qualquer colaborador."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        {avaliacoes !== null && avaliacoes.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-3">
            <Estatistica
              rotulo="Pendentes"
              valor={pendentes}
              detalhe={pendentes === 0 ? "nenhum link em aberto" : "aguardando o cliente"}
            />
            <Estatistica rotulo="Respondidas" valor={respondidas} />
            {/* O terceiro cartão não está no oráculo, mas a sinalização de negativa é a
                razão de BR-MIGRAR-021 existir: alguém precisa ligar para esse cliente
                hoje, e o número tem que estar onde se olha primeiro. */}
            <Estatistica
              rotulo="Sinalizadas"
              valor={negativas}
              detalhe={negativas === 0 ? "nada a resolver" : "pedem retorno"}
            />
          </div>
        )}

        {podePedir && (
          <Cartao titulo="Pedir avaliação">
            <form onSubmit={pedir} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {/* Busca com filtro, e não um `select` puro: o legado tem uma caixa de
                  procura porque com quarenta pessoas a lista suspensa deixa de servir.
                  O `select` continua sendo o controle — é o que dá teclado e leitor de
                  tela de graça —, mas passa a mostrar só quem casa com a busca. */}
              <Campo rotulo="Quem será avaliado" obrigatorio>
                <Entrada
                  value={buscaDePessoa}
                  onChange={(e) => setBuscaDePessoa(e.target.value)}
                  placeholder="Buscar pelo nome…"
                  className="mb-2"
                />
                <Selecao
                  required
                  value={pedido.target_user_id}
                  onChange={(e) => setPedido({ ...pedido, target_user_id: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {equipeFiltrada.map((membro) => (
                    <option key={membro.id} value={membro.id}>
                      {membro.full_name}
                      {membro.job_title ? ` — ${membro.job_title}` : ""}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              <Campo rotulo="Nome do cliente">
                <Entrada
                  value={pedido.client_name}
                  onChange={(e) => setPedido({ ...pedido, client_name: e.target.value })}
                />
              </Campo>
              <Campo rotulo="WhatsApp do cliente">
                <Entrada
                  value={pedido.client_whatsapp}
                  onChange={(e) => setPedido({ ...pedido, client_whatsapp: e.target.value })}
                />
              </Campo>
              <div className="flex items-end">
                <Botao tipo="submit">Gerar link</Botao>
              </div>
            </form>

            {link && (
              <div className="mt-4 rounded-md border border-border bg-muted px-3 py-2">
                <p className="text-xs text-muted-foreground">Link do cliente (válido por 30 dias)</p>
                <code className="mt-1 block break-all text-sm text-foreground">{link}</code>
              </div>
            )}
          </Cartao>
        )}

        <Cartao titulo="Avaliações">
          {avaliacoes === null ? (
            <Carregando />
          ) : avaliacoes.length === 0 ? (
            <EstadoVazio titulo="Nenhuma avaliação ainda" />
          ) : (
            <>
            <BarraDeFiltros
              busca={tabela.busca}
              aoBuscar={tabela.setBusca}
              placeholder="Buscar por cliente, WhatsApp ou profissional…"
              acoes={
                <>
                  <ContadorDeResultados mostrando={visiveis.length} total={avaliacoes.length} />
                  <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                </>
              }
            >
              <FiltroSelecao
                rotuloDeTodos="Todos os profissionais"
                valor={porProfissional.valor}
                aoMudar={porProfissional.aoMudar}
                opcoes={equipe.map((p) => ({ valor: p.id, rotulo: p.full_name }))}
              />
              <FiltroSelecao
                rotuloDeTodos="Todos os status"
                valor={porStatus.valor}
                aoMudar={porStatus.aoMudar}
                opcoes={[
                  { valor: "pending", rotulo: "Pendentes" },
                  { valor: "in_progress", rotulo: "Em andamento" },
                  { valor: "submitted", rotulo: "Respondidas" },
                  { valor: "expired", rotulo: "Expiradas" },
                ]}
              />
            </BarraDeFiltros>

            <Tabela
              ordenacao={tabela.ordenacao}
              vazio={visiveis.length === 0}
              vazioTexto="Nenhuma avaliação com esses filtros."
              colunas={[
                { rotulo: "Cliente", campo: "cliente" },
                { rotulo: "Profissional", campo: "profissional" },
                "WhatsApp",
                { rotulo: "Status", campo: "status" },
                { rotulo: "Nota", campo: "nota" },
                { rotulo: "Enviada em", campo: "enviada" },
              ]}
            >
              {visiveis.map((avaliacao) => (
                <Linha key={avaliacao.id}>
                  <Celula className="font-medium">{avaliacao.client_name ?? "—"}</Celula>
                  {/* Sem esta coluna não dá para ler "quantas avaliações a Bruna
                      recebeu" sem abrir uma a uma. */}
                  <Celula>{nomeDoAvaliado(avaliacao.target_user_id)}</Celula>
                  <Celula className="font-mono text-xs">
                    {avaliacao.client_whatsapp ?? "—"}
                  </Celula>
                  <Celula>
                    <Selo
                      tom={
                        avaliacao.status === "submitted"
                          ? "sucesso"
                          : avaliacao.status === "expired"
                            ? "neutro"
                            : "alerta"
                      }
                    >
                      {avaliacao.status_exibicao}
                    </Selo>
                    {avaliacao.has_negative && (
                      <span className="ml-2">
                        <Selo tom="perigo">atenção</Selo>
                      </span>
                    )}
                  </Celula>
                  <Celula>{avaliacao.overall_rating ?? "—"}</Celula>
                  <Celula>{formatarDataHora(avaliacao.submitted_at)}</Celula>
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
