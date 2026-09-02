"use client";

/**
 * Formulário de resposta — a tela onde a máquina de estados de BR-MIGRAR-003 aparece.
 *
 * Duas validações diferentes, como o service (PAR-02):
 * - **Rascunho** aceita o que estiver pela metade. Cobrar obrigatória aqui faria a
 *   pessoa perder o que já escreveu, que é justamente o que a regra quer evitar.
 * - **Enviar** é estrito, e o servidor recusa o pedido inteiro se faltar algo. A tela
 *   não replica a validação: ela mostra o que o servidor recusou. Duplicar a regra no
 *   front é como as duas versões passam a discordar.
 */

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  AreaDeTexto,
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Selecao,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { RequisicaoDetalhada } from "@/lib/tipos";

type Resposta = { texto: string; nota: string };

export default function ResponderFeedback() {
  const parametros = useParams<{ id: string }>();
  const router = useRouter();
  const [detalhe, setDetalhe] = useState<RequisicaoDetalhada | null>(null);
  const [respostas, setRespostas] = useState<Record<string, Resposta>>({});
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    api<RequisicaoDetalhada>(`/requests/${parametros.id}`)
      .then((dados) => {
        setDetalhe(dados);
        // O rascunho volta preenchido: é o cenário "retomar sem perda" de PAR-02.
        setRespostas(
          Object.fromEntries(
            dados.answers.map((resposta) => [
              resposta.question_id,
              {
                texto: resposta.answer_text ?? "",
                nota: resposta.answer_score === null ? "" : String(resposta.answer_score),
              },
            ]),
          ),
        );
      })
      .catch(() => setMensagem({ tom: "erro", texto: "Feedback não encontrado." }));
  }, [parametros.id]);

  const corpo = useCallback(() => {
    const itens = Object.entries(respostas)
      .map(([question_id, valor]) => ({
        question_id,
        answer_text: valor.texto.trim() || null,
        answer_score: valor.nota === "" ? null : Number(valor.nota),
      }))
      .filter((item) => item.answer_text !== null || item.answer_score !== null);
    return { answers: itens };
  }, [respostas]);

  async function agir(acao: "draft" | "submit" | "waive") {
    setMensagem(null);
    setSalvando(true);
    try {
      if (acao === "draft") {
        await api(`/requests/${parametros.id}/draft`, { method: "PUT", body: corpo() });
        setMensagem({ tom: "sucesso", texto: "Rascunho salvo. Você pode continuar depois." });
      } else if (acao === "submit") {
        await api(`/requests/${parametros.id}/submit`, { method: "POST", body: corpo() });
        router.push("/meus-feedbacks");
      } else {
        await api(`/requests/${parametros.id}/waive`, { method: "POST" });
        router.push("/meus-feedbacks");
      }
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError
            ? falha.status === 422
              ? "Responda todas as perguntas obrigatórias antes de enviar."
              : falha.message
            : "Não foi possível salvar agora.",
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <PaginaAutenticada
      titulo="Responder feedback"
      descricao="Suas respostas ficam visíveis para quem recebe o feedback."
    >
      {detalhe === null ? (
        <Carregando />
      ) : (
        <div className="space-y-4">
          {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

          <Cartao>
            <div className="space-y-5">
              {detalhe.questions.map((pergunta) => (
                <Campo
                  key={pergunta.id}
                  rotulo={pergunta.question_text}
                  dica={pergunta.help_text ?? undefined}
                  obrigatorio={pergunta.required}
                >
                  {pergunta.question_type === "rating" ? (
                    <Selecao
                      value={respostas[pergunta.id]?.nota ?? ""}
                      onChange={(evento) =>
                        setRespostas((atual) => ({
                          ...atual,
                          [pergunta.id]: {
                            texto: atual[pergunta.id]?.texto ?? "",
                            nota: evento.target.value,
                          },
                        }))
                      }
                    >
                      <option value="">Selecione uma nota</option>
                      {[1, 2, 3, 4, 5].map((nota) => (
                        <option key={nota} value={nota}>
                          {nota}
                        </option>
                      ))}
                    </Selecao>
                  ) : (
                    <AreaDeTexto
                      value={respostas[pergunta.id]?.texto ?? ""}
                      onChange={(evento) =>
                        setRespostas((atual) => ({
                          ...atual,
                          [pergunta.id]: {
                            texto: evento.target.value,
                            nota: atual[pergunta.id]?.nota ?? "",
                          },
                        }))
                      }
                    />
                  )}
                </Campo>
              ))}
            </div>
          </Cartao>

          <div className="flex flex-wrap gap-2">
            <Botao onClick={() => void agir("submit")} desabilitado={salvando}>
              Enviar feedback
            </Botao>
            <Botao
              variante="secundario"
              onClick={() => void agir("draft")}
              desabilitado={salvando}
            >
              Salvar rascunho
            </Botao>
            <Botao
              variante="fantasma"
              onClick={() => void agir("waive")}
              desabilitado={salvando}
            >
              Abdicar deste feedback
            </Botao>
          </div>

          <p className="text-xs text-muted-foreground">
            Abdicar tira este pedido da conta do ciclo — ele não conta como pendência nem
            como atraso.
          </p>
        </div>
      )}
    </PaginaAutenticada>
  );
}
