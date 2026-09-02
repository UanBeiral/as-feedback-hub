"use client";

/**
 * Notificações — "não lida" é `read_at IS NULL` (BR-MIGRAR-023).
 *
 * A tela nunca guarda um booleano próprio de lida: o estado vem do carimbo, que é a
 * única fonte. Duas fontes para o mesmo fato divergem, e o legado já provou isso com
 * `is_active` vs `status` em `profiles`.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Botao, Carregando, Cartao, EstadoVazio, Selo } from "@/components/ui";
import { api, apiVoid } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { FeedNotificacoes } from "@/lib/tipos";

export default function Notificacoes() {
  const [feed, setFeed] = useState<FeedNotificacoes | null>(null);

  const carregar = useCallback(async () => {
    setFeed(await api<FeedNotificacoes>("/notifications"));
  }, []);

  useEffect(() => {
    carregar().catch(() => setFeed({ items: [], unread_count: 0 }));
  }, [carregar]);

  async function marcar(id: string) {
    await apiVoid(`/notifications/${id}/read`, { method: "POST" });
    await carregar();
  }

  async function marcarTodas() {
    await apiVoid("/notifications/read-all", { method: "POST" });
    await carregar();
  }

  return (
    <PaginaAutenticada
      titulo="Notificações"
      descricao="Avisos de ciclo, feedback recebido e comunicados do escritório."
      acao={
        feed && feed.unread_count > 0 ? (
          <Botao variante="secundario" onClick={() => void marcarTodas()}>
            Marcar todas como lidas
          </Botao>
        ) : undefined
      }
    >
      <Cartao>
        {feed === null ? (
          <Carregando />
        ) : feed.items.length === 0 ? (
          <EstadoVazio
            titulo="Nenhuma notificação"
            descricao="Você é avisado aqui quando um ciclo abre ou alguém envia um feedback para você."
          />
        ) : (
          <ul className="divide-y divide-border">
            {feed.items.map((notificacao) => (
              <li key={notificacao.id} className="flex items-start justify-between gap-4 py-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                    {notificacao.title}
                    {notificacao.read_at === null && <Selo tom="destaque">nova</Selo>}
                  </p>
                  {notificacao.message && (
                    <p className="mt-1 text-sm text-muted-foreground">{notificacao.message}</p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatarDataHora(notificacao.created_at)}
                  </p>
                </div>
                {notificacao.read_at === null && (
                  <button
                    type="button"
                    onClick={() => void marcar(notificacao.id)}
                    className="shrink-0 text-sm text-primary underline-offset-4 hover:underline"
                  >
                    Marcar como lida
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Cartao>
    </PaginaAutenticada>
  );
}
