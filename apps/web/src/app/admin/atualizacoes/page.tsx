"use client";

/**
 * Atualizações — comunicados do escritório.
 *
 * Publicar enfileira uma mensagem por destinatário, com chave `update_id:user_id`
 * (BR-MIGRAR-024). Republicar por engano não gera segunda notificação para ninguém, e
 * é por isso que `notified_count` conta o que foi realmente enfileirado, não o tamanho
 * da lista.
 *
 * Rascunho e publicado são estados distintos: só o publicado aparece para o time.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  AreaDeTexto,
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Entrada,
  EstadoVazio,
  Selo,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { Comunicado } from "@/lib/tipos";

export default function AdminAtualizacoes() {
  const [comunicados, setComunicados] = useState<Comunicado[] | null>(null);
  const [novo, setNovo] = useState({ title: "", content: "" });
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    setComunicados(await api<Comunicado[]>("/platform-updates"));
  }, []);

  useEffect(() => {
    carregar().catch(() => setComunicados([]));
  }, [carregar]);

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/platform-updates", { method: "POST", body: novo });
      setNovo({ title: "", content: "" });
      setMensagem({ tom: "sucesso", texto: "Rascunho salvo. Ninguém foi avisado ainda." });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível criar.",
      });
    }
  }

  async function publicar(comunicado: Comunicado) {
    setMensagem(null);
    try {
      const publicado = await api<Comunicado>(
        `/platform-updates/${comunicado.id}/publish`,
        { method: "POST" },
      );
      setMensagem({
        tom: "sucesso",
        texto: `Publicado. ${publicado.notified_count} pessoa(s) serão notificadas.`,
      });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível publicar.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Atualizações"
      descricao="Comunicados para todo o escritório. Publicar notifica cada pessoa uma vez."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Novo comunicado">
          <form onSubmit={criar} className="space-y-4">
            <Campo rotulo="Título" obrigatorio>
              <Entrada
                required
                value={novo.title}
                onChange={(e) => setNovo({ ...novo, title: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Conteúdo" obrigatorio>
              <AreaDeTexto
                required
                value={novo.content}
                onChange={(e) => setNovo({ ...novo, content: e.target.value })}
              />
            </Campo>
            <Botao tipo="submit">Salvar rascunho</Botao>
          </form>
        </Cartao>

        <Cartao titulo="Comunicados">
          {comunicados === null ? (
            <Carregando />
          ) : comunicados.length === 0 ? (
            <EstadoVazio titulo="Nenhum comunicado" />
          ) : (
            <ul className="divide-y divide-border">
              {comunicados.map((comunicado) => (
                <li key={comunicado.id} className="py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                        {comunicado.title}
                        <Selo tom={comunicado.draft ? "neutro" : "sucesso"}>
                          {comunicado.draft ? "rascunho" : "publicado"}
                        </Selo>
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                        {comunicado.content}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {comunicado.draft
                          ? "Ainda não notificou ninguém"
                          : `${comunicado.notified_count} notificada(s) · ${formatarDataHora(comunicado.published_at)}`}
                      </p>
                    </div>
                    {comunicado.draft && (
                      <Botao onClick={() => void publicar(comunicado)}>Publicar</Botao>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
