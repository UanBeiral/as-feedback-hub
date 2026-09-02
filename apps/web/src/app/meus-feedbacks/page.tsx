"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Carregando, Cartao, Celula, EstadoVazio, Linha, Selo, Tabela } from "@/components/ui";
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

  return (
    <PaginaAutenticada
      titulo="Meus feedbacks"
      descricao="O que você precisa responder e o que já enviou neste ciclo."
    >
      <Cartao>
        {requisicoes === null ? (
          <Carregando />
        ) : requisicoes.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum feedback atribuído"
            descricao="Quando um ciclo abrir com você entre os avaliadores, os pedidos aparecem aqui."
          />
        ) : (
          <Tabela colunas={["Status", "Prazo", "Enviado em", ""]}>
            {requisicoes.map((requisicao) => {
              const atrasado =
                requisicao.due_date !== null &&
                requisicao.due_date < hoje &&
                ["pending", "draft"].includes(requisicao.status);

              return (
                <Linha key={requisicao.id}>
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
