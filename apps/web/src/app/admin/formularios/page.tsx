"use client";

/**
 * Formulários de feedback — perguntas e ordem.
 *
 * A ordem é o que a tela de resposta segue, então mexer nela muda o que a pessoa vê.
 * Reordenar manda a lista inteira: o servidor recusa uma ordem parcial, porque metade
 * da lista reordenada é pior que nenhuma.
 *
 * Arquivar é recusado enquanto houver ciclo em rascunho ou aberto usando o formulário —
 * o servidor decide isso, e a tela mostra o motivo.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Celula,
  Entrada,
  EstadoVazio,
  Linha,
  Selecao,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api, apiVoid } from "@/lib/api";
import type { Formulario, Pergunta } from "@/lib/tipos";

export default function AdminFormularios() {
  const [formularios, setFormularios] = useState<Formulario[] | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);
  const [perguntas, setPerguntas] = useState<Pergunta[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [novoNome, setNovoNome] = useState("");
  const [novaPergunta, setNovaPergunta] = useState({
    question_text: "",
    question_type: "textarea",
    required: true,
    help_text: "",
  });

  const carregar = useCallback(async () => {
    setFormularios(await api<Formulario[]>("/forms"));
  }, []);

  const carregarPerguntas = useCallback(async (formId: string) => {
    setPerguntas(await api<Pergunta[]>(`/forms/${formId}/questions`));
  }, []);

  useEffect(() => {
    carregar().catch(() => setFormularios([]));
  }, [carregar]);

  useEffect(() => {
    if (aberto) carregarPerguntas(aberto).catch(() => setPerguntas([]));
  }, [aberto, carregarPerguntas]);

  function relatar(falha: unknown, padrao: string) {
    setMensagem({ tom: "erro", texto: falha instanceof ApiError ? falha.message : padrao });
  }

  async function criarFormulario(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      const criado = await api<Formulario>("/forms", {
        method: "POST",
        body: { name: novoNome },
      });
      setNovoNome("");
      await carregar();
      setAberto(criado.id);
    } catch (falha) {
      relatar(falha, "Não foi possível criar o formulário.");
    }
  }

  async function adicionarPergunta(evento: React.FormEvent) {
    evento.preventDefault();
    if (!aberto) return;
    setMensagem(null);
    try {
      await api(`/forms/${aberto}/questions`, {
        method: "POST",
        body: { ...novaPergunta, help_text: novaPergunta.help_text || null },
      });
      setNovaPergunta({ ...novaPergunta, question_text: "", help_text: "" });
      await carregarPerguntas(aberto);
    } catch (falha) {
      relatar(falha, "Não foi possível adicionar a pergunta.");
    }
  }

  async function mover(indice: number, direcao: -1 | 1) {
    if (!aberto) return;
    const destino = indice + direcao;
    if (destino < 0 || destino >= perguntas.length) return;

    const ordem = perguntas.map((pergunta) => pergunta.id);
    [ordem[indice], ordem[destino]] = [ordem[destino], ordem[indice]];

    setMensagem(null);
    try {
      // A lista vai inteira: o servidor recusa ordem parcial de propósito.
      await apiVoid(`/forms/${aberto}/questions/order`, {
        method: "PUT",
        body: { question_ids: ordem },
      });
      await carregarPerguntas(aberto);
    } catch (falha) {
      relatar(falha, "Não foi possível reordenar.");
    }
  }

  async function arquivar(formulario: Formulario) {
    setMensagem(null);
    try {
      await api(`/forms/${formulario.id}/archive`, { method: "POST" });
      setMensagem({ tom: "sucesso", texto: `"${formulario.name}" arquivado.` });
      if (aberto === formulario.id) setAberto(null);
      await carregar();
    } catch (falha) {
      // 409 aqui é o guard de formulário em uso por ciclo vivo.
      relatar(falha, "Não foi possível arquivar.");
    }
  }

  return (
    <PaginaAutenticada
      titulo="Formulários de feedback"
      descricao="As perguntas que aparecem para quem responde, na ordem em que aparecem."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Novo formulário">
          <form onSubmit={criarFormulario} className="flex flex-wrap items-end gap-3">
            <div className="min-w-64 flex-1">
              <Campo rotulo="Nome" obrigatorio>
                <Entrada
                  required
                  value={novoNome}
                  onChange={(e) => setNovoNome(e.target.value)}
                  placeholder="Avaliação 360 — 2026"
                />
              </Campo>
            </div>
            <Botao tipo="submit">Criar</Botao>
          </form>
        </Cartao>

        <Cartao titulo="Formulários">
          {formularios === null ? (
            <Carregando />
          ) : formularios.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum formulário"
              descricao="Um ciclo precisa de formulário para ser criado."
            />
          ) : (
            <Tabela colunas={["Nome", "Situação", ""]}>
              {formularios.map((formulario) => (
                <Linha key={formulario.id}>
                  <Celula className="font-medium">{formulario.name}</Celula>
                  <Celula>
                    <Selo tom={formulario.archived_at ? "neutro" : "sucesso"}>
                      {formulario.archived_at ? "arquivado" : "ativo"}
                    </Selo>
                  </Celula>
                  <Celula className="text-right">
                    <span className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => setAberto(aberto === formulario.id ? null : formulario.id)}
                        className="text-sm text-primary underline-offset-4 hover:underline"
                      >
                        {aberto === formulario.id ? "Fechar" : "Perguntas"}
                      </button>
                      {!formulario.archived_at && (
                        <button
                          type="button"
                          onClick={() => void arquivar(formulario)}
                          className="text-sm text-destructive underline-offset-4 hover:underline"
                        >
                          Arquivar
                        </button>
                      )}
                    </span>
                  </Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>

        {aberto && (
          <Cartao
            titulo="Perguntas"
            descricao="A ordem aqui é a ordem em que aparecem para quem responde."
          >
            {perguntas.length === 0 ? (
              <EstadoVazio titulo="Nenhuma pergunta ainda" />
            ) : (
              <ol className="mb-6 space-y-2">
                {perguntas.map((pergunta, indice) => (
                  <li
                    key={pergunta.id}
                    className="flex items-start justify-between gap-4 rounded-md border border-border px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-foreground">
                        {indice + 1}. {pergunta.question_text}
                        {pergunta.required && <span className="ml-1 text-destructive">*</span>}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {pergunta.question_type === "rating" ? "Nota de 1 a 5" : "Texto livre"}
                        {pergunta.help_text ? ` · ${pergunta.help_text}` : ""}
                      </p>
                    </div>
                    <span className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        aria-label="Mover para cima"
                        onClick={() => void mover(indice, -1)}
                        disabled={indice === 0}
                        className="rounded px-2 py-1 text-sm text-foreground hover:bg-muted disabled:opacity-30"
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        aria-label="Mover para baixo"
                        onClick={() => void mover(indice, 1)}
                        disabled={indice === perguntas.length - 1}
                        className="rounded px-2 py-1 text-sm text-foreground hover:bg-muted disabled:opacity-30"
                      >
                        ↓
                      </button>
                    </span>
                  </li>
                ))}
              </ol>
            )}

            <form
              onSubmit={adicionarPergunta}
              className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <div className="lg:col-span-2">
                <Campo rotulo="Pergunta" obrigatorio>
                  <Entrada
                    required
                    value={novaPergunta.question_text}
                    onChange={(e) =>
                      setNovaPergunta({ ...novaPergunta, question_text: e.target.value })
                    }
                  />
                </Campo>
              </div>
              <Campo rotulo="Tipo">
                <Selecao
                  value={novaPergunta.question_type}
                  onChange={(e) =>
                    setNovaPergunta({ ...novaPergunta, question_type: e.target.value })
                  }
                >
                  <option value="textarea">Texto livre</option>
                  <option value="rating">Nota de 1 a 5</option>
                </Selecao>
              </Campo>
              <Campo rotulo="Obrigatória">
                <Selecao
                  value={novaPergunta.required ? "sim" : "nao"}
                  onChange={(e) =>
                    setNovaPergunta({ ...novaPergunta, required: e.target.value === "sim" })
                  }
                >
                  <option value="sim">Sim</option>
                  <option value="nao">Não</option>
                </Selecao>
              </Campo>
              <div className="lg:col-span-3">
                <Campo rotulo="Texto de ajuda" dica="Aparece abaixo da pergunta.">
                  <Entrada
                    value={novaPergunta.help_text}
                    onChange={(e) =>
                      setNovaPergunta({ ...novaPergunta, help_text: e.target.value })
                    }
                  />
                </Campo>
              </div>
              <div className="flex items-end">
                <Botao tipo="submit">Adicionar</Botao>
              </div>
            </form>
          </Cartao>
        )}
      </div>
    </PaginaAutenticada>
  );
}
