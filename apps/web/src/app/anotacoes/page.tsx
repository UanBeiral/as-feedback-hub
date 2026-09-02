"use client";

/**
 * Anotações — o caderno do ciclo.
 *
 * São notas privadas do autor sobre pessoas da equipe, feitas ao longo do ciclo para
 * que a avaliação não dependa de memória de última hora. **Privadas mesmo**: a API só
 * devolve as do próprio autor, e nem a administração lê as de outra pessoa. Por isso
 * apagar também é só do autor.
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
  EstadoVazio,
  Selecao,
} from "@/components/ui";
import { ApiError, api, apiVoid } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { AnotacaoDeCiclo, Ciclo, Perfil } from "@/lib/tipos";

export default function Anotacoes() {
  const [anotacoes, setAnotacoes] = useState<AnotacaoDeCiclo[] | null>(null);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [equipe, setEquipe] = useState<Perfil[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [nova, setNova] = useState({ cycle_id: "", about_user_id: "", content: "" });

  const carregar = useCallback(async () => {
    const [notas, listaDeCiclos, membros] = await Promise.all([
      api<AnotacaoDeCiclo[]>("/cycle-notes"),
      api<Ciclo[]>("/cycles"),
      api<Perfil[]>("/auth/my-team"),
    ]);
    setAnotacoes(notas);
    setCiclos(listaDeCiclos);
    setEquipe(membros);
  }, []);

  useEffect(() => {
    carregar().catch(() => setAnotacoes([]));
  }, [carregar]);

  async function escrever(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/cycle-notes", { method: "POST", body: nova });
      setNova({ ...nova, content: "" });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível salvar a anotação.",
      });
    }
  }

  async function apagar(id: string) {
    setMensagem(null);
    try {
      await apiVoid(`/cycle-notes/${id}`, { method: "DELETE" });
      await carregar();
    } catch {
      setMensagem({ tom: "erro", texto: "Não foi possível apagar." });
    }
  }

  const nomePor = new Map(equipe.map((membro) => [membro.id, membro.full_name]));
  const nomeDoCiclo = new Map(ciclos.map((ciclo) => [ciclo.id, ciclo.name]));

  return (
    <PaginaAutenticada
      titulo="Minhas anotações"
      descricao="Notas suas sobre a equipe durante o ciclo. Ninguém mais as vê."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Nova anotação">
          <form onSubmit={escrever} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo rotulo="Ciclo" obrigatorio>
                <Selecao
                  required
                  value={nova.cycle_id}
                  onChange={(e) => setNova({ ...nova, cycle_id: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {ciclos.map((ciclo) => (
                    <option key={ciclo.id} value={ciclo.id}>
                      {ciclo.name}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              <Campo rotulo="Sobre quem" obrigatorio>
                <Selecao
                  required
                  value={nova.about_user_id}
                  onChange={(e) => setNova({ ...nova, about_user_id: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {equipe.map((membro) => (
                    <option key={membro.id} value={membro.id}>
                      {membro.full_name}
                    </option>
                  ))}
                </Selecao>
              </Campo>
            </div>

            <Campo rotulo="Anotação" obrigatorio>
              <AreaDeTexto
                required
                value={nova.content}
                onChange={(e) => setNova({ ...nova, content: e.target.value })}
                placeholder="Conduziu bem a audiência de conciliação…"
              />
            </Campo>

            <Botao tipo="submit">Salvar anotação</Botao>
          </form>
        </Cartao>

        <Cartao titulo="Anotações realizadas">
          {anotacoes === null ? (
            <Carregando />
          ) : anotacoes.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma anotação ainda"
              descricao="Anotar durante o ciclo evita depender da memória na hora de avaliar."
            />
          ) : (
            <ul className="divide-y divide-border">
              {anotacoes.map((anotacao) => (
                <li key={anotacao.id} className="flex items-start justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      {nomePor.get(anotacao.about_user_id) ?? "—"}
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {nomeDoCiclo.get(anotacao.cycle_id) ?? "ciclo removido"}
                      </span>
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
                      {anotacao.content}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatarDataHora(anotacao.created_at)}
                      {anotacao.is_audio_transcription && " · ditada"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void apagar(anotacao.id)}
                    className="shrink-0 text-sm text-destructive underline-offset-4 hover:underline"
                  >
                    Apagar
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
