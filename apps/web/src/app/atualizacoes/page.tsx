"use client";

/**
 * Novidades (SCR-0039) — os comunicados, para quem os recebe.
 *
 * Existia só `/admin/atualizacoes`, restrita a admin/RH: quem não administra não tinha
 * onde ler comunicado nenhum. Pior, o worker cria a notificação com `link="/atualizacoes"`
 * e essa rota não existia — publicar tocava o sino de todo mundo e levava a um 404.
 *
 * A rota se chama `/atualizacoes` por isso: é o caminho que já está gravado nas
 * notificações antigas. Escolher um nome mais bonito exigiria migração para consertar
 * linhas que o nome certo conserta de graça.
 *
 * Abrir a tela marca as notificações de comunicado como lidas. É o `marks_read` da spec,
 * e a razão é o sino: um contador que não zera depois de a pessoa ler é um contador que
 * ela aprende a ignorar.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Carregando, Cartao, EstadoVazio, Selo } from "@/components/ui";
import { api, apiVoid } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { Comunicado, FeedNotificacoes } from "@/lib/tipos";

export default function Novidades() {
  const [comunicados, setComunicados] = useState<Comunicado[] | null>(null);

  const marcarLidas = useCallback(async () => {
    const feed = await api<FeedNotificacoes>("/notifications", { query: { unread: true } });
    // Só as de comunicado: "marcar tudo como lido" ao abrir esta tela apagaria também o
    // aviso de feedback pendente, que a pessoa não veio ler aqui.
    await Promise.all(
      feed.items
        .filter((item) => item.type === "platform_update")
        .map((item) => apiVoid(`/notifications/${item.id}/read`, { method: "POST" })),
    );
  }, []);

  useEffect(() => {
    api<Comunicado[]>("/platform-updates")
      .then(setComunicados)
      .catch(() => setComunicados([]));
    // Falhar aqui não pode esconder o comunicado: a leitura é o que a pessoa veio fazer,
    // e o contador do sino é consequência.
    marcarLidas().catch(() => undefined);
  }, [marcarLidas]);

  // O endpoint devolve rascunho para admin/RH — aqui a tela é de leitura, e rascunho não
  // é comunicado ainda. Quem edita faz isso em `/admin/atualizacoes`.
  const publicados = (comunicados ?? []).filter((c) => !c.draft);

  return (
    <PaginaAutenticada
      titulo="Novidades"
      descricao="O que mudou no sistema e os avisos do escritório."
    >
      {comunicados === null ? (
        <Cartao>
          <Carregando />
        </Cartao>
      ) : publicados.length === 0 ? (
        <Cartao>
          <EstadoVazio
            titulo="Nenhuma novidade ainda"
            descricao="Quando a administração publicar um comunicado, ele aparece aqui."
          />
        </Cartao>
      ) : (
        <div className="space-y-4">
          {publicados.map((comunicado) => (
            <Cartao
              key={comunicado.id}
              titulo={comunicado.title}
              acao={
                <span className="text-xs text-muted-foreground">
                  {formatarDataHora(comunicado.published_at)}
                </span>
              }
            >
              <p className="whitespace-pre-wrap text-sm text-foreground">
                {comunicado.content}
              </p>
              {comunicado.notified_count > 0 && (
                <p className="mt-3">
                  <Selo tom="neutro">
                    {comunicado.notified_count} pessoa
                    {comunicado.notified_count === 1 ? "" : "s"} avisada
                    {comunicado.notified_count === 1 ? "" : "s"}
                  </Selo>
                </p>
              )}
            </Cartao>
          ))}
        </div>
      )}
    </PaginaAutenticada>
  );
}
