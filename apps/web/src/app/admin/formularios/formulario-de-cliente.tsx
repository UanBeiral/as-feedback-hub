"use client";

/**
 * Editor dos formulários de cliente externo — a aba que faltava (#45 da conferência).
 *
 * São as perguntas que o cliente responde no wizard público. Até aqui elas só existiam
 * no banco: havia `GET/POST` de formulário e `POST` de pergunta, e nada para ler, editar,
 * remover ou reordenar. Na prática, mudar o questionário do escritório era abrir o
 * Postgres.
 *
 * Duas coisas diferenciam esta aba da dos 360, e as duas vêm do fato de o formulário ser
 * respondido por gente de fora:
 *
 * - **Os tipos são outros.** Estrelas 0–10, NPS e sim/não existem aqui e não lá, porque
 *   é o que o wizard público sabe desenhar.
 * - **Remover pode não apagar.** Pergunta já respondida é arquivada: sai dos formulários
 *   novos e continua explicando os relatórios antigos. Apagar destruiria a resposta de um
 *   cliente para limpar um formulário.
 */

import { useCallback, useEffect, useState } from "react";

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
import { ApiError, api } from "@/lib/api";
import type { FormularioDeCliente, PerguntaDeCliente } from "@/lib/tipos";

/** Os tipos que o wizard público sabe desenhar. `multiple_choice` fica fora: o contrato
 *  aceita, mas não há onde cadastrar as opções — oferecer daria uma pergunta sem
 *  resposta possível. */
const TIPOS = [
  { valor: "rating", rotulo: "Estrelas (0 a 10)" },
  { valor: "nps", rotulo: "Recomendação (NPS)" },
  { valor: "textarea", rotulo: "Texto livre" },
  { valor: "text", rotulo: "Texto curto" },
  { valor: "yes_no", rotulo: "Sim ou não" },
] as const;

const PERGUNTA_VAZIA = {
  question_text: "",
  question_type: "rating",
  is_required: true,
  placeholder: "",
};

export function FormulariosDeCliente() {
  const [formularios, setFormularios] = useState<FormularioDeCliente[] | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);
  const [perguntas, setPerguntas] = useState<PerguntaDeCliente[]>([]);
  const [verArquivadas, setVerArquivadas] = useState(false);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [novoNome, setNovoNome] = useState("");
  const [nova, setNova] = useState(PERGUNTA_VAZIA);
  const [editando, setEditando] = useState<PerguntaDeCliente | null>(null);

  const carregar = useCallback(async () => {
    setFormularios(await api<FormularioDeCliente[]>("/client-eval/forms"));
  }, []);

  const carregarPerguntas = useCallback(async (formId: string, arquivadas: boolean) => {
    setPerguntas(
      await api<PerguntaDeCliente[]>(`/client-eval/forms/${formId}/questions`, {
        query: { incluir_arquivadas: arquivadas },
      }),
    );
  }, []);

  useEffect(() => {
    carregar().catch(() => setFormularios([]));
  }, [carregar]);

  useEffect(() => {
    if (aberto) carregarPerguntas(aberto, verArquivadas).catch(() => setPerguntas([]));
  }, [aberto, verArquivadas, carregarPerguntas]);

  function relatar(falha: unknown, padrao: string) {
    setMensagem({ tom: "erro", texto: falha instanceof ApiError ? falha.message : padrao });
  }

  async function criarFormulario(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      const criado = await api<FormularioDeCliente>("/client-eval/forms", {
        method: "POST",
        body: { name: novoNome, is_default: (formularios ?? []).length === 0, is_active: true },
      });
      setNovoNome("");
      await carregar();
      setAberto(criado.id);
    } catch (falha) {
      relatar(falha, "Não foi possível criar o formulário.");
    }
  }

  async function salvarFormulario(form: FormularioDeCliente, mudanca: Partial<FormularioDeCliente>) {
    setMensagem(null);
    try {
      // PUT com o recurso inteiro: o servidor tira o padrão do anterior sozinho, porque
      // dois formulários padrão fariam o fluxo espontâneo sortear qual o cliente responde.
      await api(`/client-eval/forms/${form.id}`, {
        method: "PUT",
        body: {
          name: mudanca.name ?? form.name,
          is_default: mudanca.is_default ?? form.is_default,
          is_active: mudanca.is_active ?? form.is_active,
        },
      });
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível salvar o formulário.");
    }
  }

  async function adicionar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!aberto) return;
    setMensagem(null);
    try {
      await api(`/client-eval/forms/${aberto}/questions`, {
        method: "POST",
        body: { ...nova, placeholder: nova.placeholder.trim() || null },
      });
      setNova(PERGUNTA_VAZIA);
      await carregarPerguntas(aberto, verArquivadas);
    } catch (falha) {
      relatar(falha, "Não foi possível adicionar a pergunta.");
    }
  }

  async function salvarEdicao() {
    if (!aberto || !editando) return;
    setMensagem(null);
    try {
      await api(`/client-eval/forms/${aberto}/questions/${editando.id}`, {
        method: "PUT",
        body: {
          question_text: editando.question_text,
          question_type: editando.question_type,
          is_required: editando.is_required,
          placeholder: editando.placeholder?.trim() || null,
        },
      });
      setEditando(null);
      await carregarPerguntas(aberto, verArquivadas);
    } catch (falha) {
      relatar(falha, "Não foi possível salvar a pergunta.");
    }
  }

  async function remover(pergunta: PerguntaDeCliente) {
    if (!aberto) return;
    setMensagem(null);

    // O aviso é diferente conforme o desfecho, e a pessoa merece saber antes de clicar:
    // uma pergunta respondida não some de verdade, e isso muda o que ela deve esperar.
    const confirmacao = pergunta.tem_resposta
      ? `"${pergunta.question_text}" já foi respondida por clientes.\n\n` +
        "Ela vai ser arquivada: sai dos formulários novos e continua nos relatórios " +
        "antigos. As respostas não são apagadas."
      : `Remover "${pergunta.question_text}"?\n\nNinguém respondeu ainda, então ela some de vez.`;
    if (!window.confirm(confirmacao)) return;

    try {
      const resultado = await api<PerguntaDeCliente>(
        `/client-eval/forms/${aberto}/questions/${pergunta.id}`,
        { method: "DELETE" },
      );
      setMensagem({
        tom: "sucesso",
        texto: resultado.is_active
          ? "Pergunta removida."
          : "Pergunta arquivada — as respostas dos clientes seguem nos relatórios.",
      });
      await carregarPerguntas(aberto, verArquivadas);
    } catch (falha) {
      relatar(falha, "Não foi possível remover.");
    }
  }

  async function mover(indice: number, direcao: -1 | 1) {
    if (!aberto) return;
    const destino = indice + direcao;
    if (destino < 0 || destino >= perguntas.length) return;

    const ordem = perguntas.map((p) => p.id);
    [ordem[indice], ordem[destino]] = [ordem[destino], ordem[indice]];

    setMensagem(null);
    try {
      // A ordem inteira, e não "mover um": é o que torna a operação idempotente e sem
      // corrida entre dois administradores mexendo ao mesmo tempo (BR-MIGRAR-020).
      await api(`/client-eval/forms/${aberto}/questions/order`, {
        method: "PUT",
        body: { question_ids: ordem },
      });
      await carregarPerguntas(aberto, verArquivadas);
    } catch (falha) {
      relatar(falha, "Não foi possível reordenar.");
    }
  }

  const ativas = perguntas.filter((p) => p.is_active);

  return (
    <div className="space-y-6">
      {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

      <Cartao
        titulo="Novo formulário de cliente"
        descricao="É o questionário que o cliente responde pelo link do WhatsApp."
      >
        <form onSubmit={criarFormulario} className="flex flex-wrap items-end gap-3">
          <div className="min-w-64 flex-1">
            <Campo rotulo="Nome" obrigatorio>
              <Entrada
                required
                value={novoNome}
                onChange={(e) => setNovoNome(e.target.value)}
                placeholder="Atendimento Jurídico Geral"
              />
            </Campo>
          </div>
          <Botao tipo="submit">Criar</Botao>
        </form>
      </Cartao>

      <Cartao titulo="Formulários de cliente externo">
        {formularios === null ? (
          <Carregando />
        ) : formularios.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum formulário de cliente"
            descricao="Sem um formulário, o link de avaliação não tem o que perguntar."
          />
        ) : (
          <Tabela colunas={["Nome", "Situação", ""]}>
            {formularios.map((form) => (
              <Linha key={form.id}>
                <Celula className="font-medium">
                  <span className="flex items-center gap-2">
                    {form.name}
                    {form.is_default && <Selo tom="destaque">Padrão</Selo>}
                  </span>
                </Celula>
                <Celula>
                  <Selo tom={form.is_active ? "sucesso" : "neutro"}>
                    {form.is_active ? "ativo" : "inativo"}
                  </Selo>
                </Celula>
                <Celula className="text-right">
                  <span className="flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setAberto(aberto === form.id ? null : form.id)}
                      className="text-sm text-primary underline-offset-4 hover:underline"
                    >
                      {aberto === form.id ? "Fechar" : "Perguntas"}
                    </button>
                    {!form.is_default && (
                      <button
                        type="button"
                        onClick={() => void salvarFormulario(form, { is_default: true })}
                        className="text-sm text-primary underline-offset-4 hover:underline"
                      >
                        Tornar padrão
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => void salvarFormulario(form, { is_active: !form.is_active })}
                      className="text-sm text-destructive underline-offset-4 hover:underline"
                    >
                      {form.is_active ? "Desativar" : "Ativar"}
                    </button>
                  </span>
                </Celula>
              </Linha>
            ))}
          </Tabela>
        )}
      </Cartao>

      {aberto && (
        <Cartao
          titulo="Perguntas do cliente"
          descricao="Uma por etapa no wizard, na ordem em que aparecem."
          acao={
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                checked={verArquivadas}
                onChange={(e) => setVerArquivadas(e.target.checked)}
              />
              Ver arquivadas
            </label>
          }
        >
          {perguntas.length === 0 ? (
            <EstadoVazio titulo="Nenhuma pergunta ainda" />
          ) : (
            <ol className="mb-6 space-y-2">
              {perguntas.map((pergunta, indice) => (
                <li
                  key={pergunta.id}
                  className={
                    "rounded-md border border-border px-3 py-2 " +
                    (pergunta.is_active ? "" : "opacity-60")
                  }
                >
                  {editando?.id === pergunta.id ? (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <div className="lg:col-span-2">
                        <Campo rotulo="Pergunta" obrigatorio>
                          <Entrada
                            value={editando.question_text}
                            onChange={(e) =>
                              setEditando({ ...editando, question_text: e.target.value })
                            }
                          />
                        </Campo>
                      </div>
                      <Campo rotulo="Tipo">
                        <Selecao
                          value={editando.question_type}
                          onChange={(e) =>
                            setEditando({ ...editando, question_type: e.target.value })
                          }
                        >
                          {TIPOS.map((tipo) => (
                            <option key={tipo.valor} value={tipo.valor}>
                              {tipo.rotulo}
                            </option>
                          ))}
                        </Selecao>
                      </Campo>
                      <Campo rotulo="Obrigatória">
                        <Selecao
                          value={editando.is_required ? "sim" : "nao"}
                          onChange={(e) =>
                            setEditando({ ...editando, is_required: e.target.value === "sim" })
                          }
                        >
                          <option value="sim">Sim</option>
                          <option value="nao">Não</option>
                        </Selecao>
                      </Campo>
                      <div className="lg:col-span-3">
                        <Campo rotulo="Placeholder" dica="Só aparece nos tipos de texto.">
                          <Entrada
                            value={editando.placeholder ?? ""}
                            onChange={(e) =>
                              setEditando({ ...editando, placeholder: e.target.value })
                            }
                          />
                        </Campo>
                      </div>
                      <div className="flex items-end gap-2">
                        <Botao onClick={() => void salvarEdicao()}>Salvar</Botao>
                        <Botao variante="fantasma" onClick={() => setEditando(null)}>
                          Cancelar
                        </Botao>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-sm text-foreground">
                          {indice + 1}. {pergunta.question_text}
                          {pergunta.is_required && <span className="ml-1 text-destructive">*</span>}
                          {!pergunta.is_active && (
                            <Selo tom="neutro">
                              <span className="ml-2">arquivada</span>
                            </Selo>
                          )}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {TIPOS.find((t) => t.valor === pergunta.question_type)?.rotulo ??
                            pergunta.question_type}
                          {pergunta.placeholder ? ` · ${pergunta.placeholder}` : ""}
                          {pergunta.tem_resposta ? " · já respondida por clientes" : ""}
                        </p>
                      </div>
                      <span className="flex shrink-0 items-center gap-1">
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
                        <button
                          type="button"
                          onClick={() => setEditando(pergunta)}
                          className="ml-2 text-sm text-primary underline-offset-4 hover:underline"
                        >
                          Editar
                        </button>
                        {pergunta.is_active && (
                          <button
                            type="button"
                            onClick={() => void remover(pergunta)}
                            className="text-sm text-destructive underline-offset-4 hover:underline"
                          >
                            Remover
                          </button>
                        )}
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}

          <p className="mb-4 text-sm text-muted-foreground">
            {ativas.length === 0
              ? "Nenhuma pergunta ativa — o cliente veria um wizard vazio."
              : `${ativas.length} pergunta(s) ativa(s): é o que o cliente responde hoje.`}
          </p>

          <form
            onSubmit={adicionar}
            className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-4"
          >
            <div className="lg:col-span-2">
              <Campo rotulo="Pergunta" obrigatorio>
                <Entrada
                  required
                  value={nova.question_text}
                  onChange={(e) => setNova({ ...nova, question_text: e.target.value })}
                  placeholder="Como você avalia o atendimento recebido?"
                />
              </Campo>
            </div>
            <Campo rotulo="Tipo">
              <Selecao
                value={nova.question_type}
                onChange={(e) => setNova({ ...nova, question_type: e.target.value })}
              >
                {TIPOS.map((tipo) => (
                  <option key={tipo.valor} value={tipo.valor}>
                    {tipo.rotulo}
                  </option>
                ))}
              </Selecao>
            </Campo>
            <Campo rotulo="Obrigatória">
              <Selecao
                value={nova.is_required ? "sim" : "nao"}
                onChange={(e) => setNova({ ...nova, is_required: e.target.value === "sim" })}
              >
                <option value="sim">Sim</option>
                <option value="nao">Não</option>
              </Selecao>
            </Campo>
            <div className="lg:col-span-3">
              <Campo rotulo="Placeholder" dica="Só aparece nos tipos de texto.">
                <Entrada
                  value={nova.placeholder}
                  onChange={(e) => setNova({ ...nova, placeholder: e.target.value })}
                  placeholder="Ex: Foi muito atencioso, explicou tudo com clareza…"
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
  );
}
