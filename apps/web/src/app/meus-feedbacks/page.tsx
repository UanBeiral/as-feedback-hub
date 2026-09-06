"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Estatistica,
  Linha,
  Selo,
  Tabela,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatarData, ROTULO_DO_REQUEST } from "@/lib/formato";
import type { Requisicao } from "@/lib/tipos";

const TOM_DO_STATUS = {
  pending: "alerta",
  draft: "neutro",
  submitted: "sucesso",
  expired: "perigo",
  waived: "neutro",
  cancelled: "neutro",
} as const;

export default function MeusFeedbacks() {
  const [requisicoes, setRequisicoes] = useState<Requisicao[] | null>(null);

  useEffect(() => {
    api<Requisicao[]>("/requests/mine", { query: { incluir_enviados: true } })
      .then(setRequisicoes)
      .catch(() => setRequisicoes([]));
  }, []);

  const hoje = new Date().toISOString().slice(0, 10);

  /**
   * Os três números do topo, com o mesmo recorte do progresso do ciclo
   * (BR-MIGRAR-009): `cancelled` e `waived` saem do que se espera de você, e abdicado
   * ganha contador próprio em vez de sumir. Contar aqui, e não no servidor, é seguro
   * porque a lista já veio inteira — o que a tela mostra e o que ela soma são a mesma
   * coisa, e não duas verdades que podem divergir.
   */
  const resumo = {
    atencao: (requisicoes ?? []).filter((r) => ["pending", "draft"].includes(r.status)).length,
    enviados: (requisicoes ?? []).filter((r) => r.status === "submitted").length,
    abdicados: (requisicoes ?? []).filter((r) => ["waived", "cancelled"].includes(r.status))
      .length,
  };

  return (
    <PaginaAutenticada
      titulo="Meus feedbacks"
      descricao="O que você precisa responder, o que já enviou e o que saiu da sua conta."
    >
      {requisicoes !== null && requisicoes.length > 0 && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <Estatistica
            rotulo="Precisam da sua atenção"
            valor={resumo.atencao}
            detalhe={resumo.atencao === 0 ? "Você está em dia." : "Pendentes e rascunhos."}
          />
          <Estatistica rotulo="Enviados com sucesso" valor={resumo.enviados} />
          <Estatistica
            rotulo="Abdicados"
            valor={resumo.abdicados}
            detalhe="Não contam contra você."
          />
        </div>
      )}

      <Cartao>
        {requisicoes === null ? (
          <Carregando />
        ) : requisicoes.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum feedback atribuído"
            descricao="Quando um ciclo abrir com você entre os avaliadores, os pedidos aparecem aqui."
          />
        ) : (
          <Tabela colunas={["Avaliado", "Status", "Prazo", "Enviado em", ""]}>
            {requisicoes.map((requisicao) => {
              const atrasado =
                requisicao.due_date !== null &&
                requisicao.due_date < hoje &&
                ["pending", "draft"].includes(requisicao.status);

              return (
                <Linha key={requisicao.id}>
                  {/* Primeira coluna, e não a última: sem o nome de quem será avaliado a
                      lista vira um punhado de linhas idênticas — mesmo status, mesmo
                      prazo — e a pessoa não descobre qual pedido responder. */}
                  <Celula className="font-medium">
                    {requisicao.receiver_name ?? "—"}
                  </Celula>
                  <Celula>
                    <Selo tom={TOM_DO_STATUS[requisicao.status as keyof typeof TOM_DO_STATUS]}>
                      {ROTULO_DO_REQUEST[requisicao.status] ?? requisicao.status}
                    </Selo>
                  </Celula>
                  <Celula>
                    {formatarData(requisicao.due_date)}
                    {/* Atraso é derivação server-side (BR-MIGRAR-007); aqui só marcamos
                        visualmente o que o prazo já diz. */}
                    {atrasado && (
                      <span className="ml-2 text-xs font-medium text-destructive">atrasado</span>
                    )}
                  </Celula>
                  <Celula>{formatarData(requisicao.submitted_at?.slice(0, 10) ?? null)}</Celula>
                  <Celula className="text-right">
                    {["pending", "draft"].includes(requisicao.status) ? (
                      <Link
                        href={`/meus-feedbacks/${requisicao.id}`}
                        className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                      >
                        {requisicao.status === "draft" ? "Continuar" : "Responder"}
                      </Link>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </Celula>
                </Linha>
              );
            })}
          </Tabela>
        )}
      </Cartao>
    </PaginaAutenticada>
  );
}
