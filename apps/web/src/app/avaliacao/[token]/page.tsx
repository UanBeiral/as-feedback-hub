"use client";

/**
 * Página pública de avaliação de cliente (PAR-03).
 *
 * A única tela do sistema sem sessão. Três cuidados que ela carrega:
 *
 * - **Não fala com nada além do endpoint público.** Nenhuma chamada autenticada, nenhum
 *   dado do escritório além do nome de quem será avaliado.
 * - **Link inválido, expirado ou já respondido mostram a mesma mensagem.** Distinguir
 *   contaria a um estranho que aquele link um dia valeu — e ele circula por WhatsApp.
 * - **Enviar duas vezes mostra a mesma confirmação.** O servidor trata o duplo clique
 *   como sucesso; a tela não inventa um erro que ele não deu.
 */

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AreaDeTexto,
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Entrada,
  Selecao,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { FormularioPublico } from "@/lib/tipos";

type Resposta = { texto: string; nota: string };

export default function AvaliacaoPublica() {
  const parametros = useParams<{ token: string }>();
  const [formulario, setFormulario] = useState<FormularioPublico | null>(null);
  const [indisponivel, setIndisponivel] = useState(false);
  const [respostas, setRespostas] = useState<Record<string, Resposta>>({});
  const [contato, setContato] = useState({ nome: "", whatsapp: "", email: "" });
  const [notaGeral, setNotaGeral] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [enviado, setEnviado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<FormularioPublico>(`/public/evaluations/${parametros.token}`, { publico: true })
      .then(setFormulario)
      .catch(() => setIndisponivel(true));
  }, [parametros.token]);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await api(`/public/evaluations/${parametros.token}`, {
        publico: true,
        method: "POST",
        body: {
          answers: Object.entries(respostas)
            .map(([question_id, valor]) => ({
              question_id,
              text_value: valor.texto.trim() || null,
              rating_value: valor.nota === "" ? null : Number(valor.nota),
            }))
            .filter((item) => item.text_value !== null || item.rating_value !== null),
          client_name: contato.nome || null,
          client_whatsapp: contato.whatsapp || null,
          client_email: contato.email || null,
          overall_rating: notaGeral === "" ? null : Number(notaGeral),
          service_tag_ids: tags,
        },
      });
      setEnviado(true);
    } catch (falha) {
      setErro(
        falha instanceof ApiError && falha.status === 422
          ? "Responda as perguntas obrigatórias antes de enviar."
          : "Não foi possível enviar sua avaliação agora.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-xl">
        {indisponivel ? (
          <Cartao>
            <h1 className="text-lg font-semibold text-foreground">Link indisponível</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Este link de avaliação não é válido ou já foi utilizado. Se você recebeu o
              convite há pouco tempo, peça um novo ao escritório.
            </p>
          </Cartao>
        ) : enviado ? (
          <Cartao>
            <h1 className="text-lg font-semibold text-foreground">Avaliação recebida</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Obrigado pelo retorno. Sua opinião ajuda o escritório a melhorar o
              atendimento.
            </p>
          </Cartao>
        ) : formulario === null ? (
          <Carregando />
        ) : (
          <>
            <header className="mb-6 text-center">
              <h1 className="text-2xl font-semibold text-foreground">Como foi o atendimento?</h1>
              {formulario.target_name && (
                <p className="mt-1 text-sm text-muted-foreground">
                  Sua avaliação sobre <strong>{formulario.target_name}</strong>
                </p>
              )}
            </header>

            <form onSubmit={enviar} className="space-y-4">
              <Cartao>
                <div className="space-y-5">
                  {formulario.questions.map((pergunta) => (
                    <Campo
                      key={pergunta.id}
                      rotulo={pergunta.question_text}
                      obrigatorio={pergunta.is_required}
                    >
                      {pergunta.question_type === "rating" ||
                      pergunta.question_type === "nps" ? (
                        <Selecao
                          value={respostas[pergunta.id]?.nota ?? ""}
                          onChange={(e) =>
                            setRespostas((atual) => ({
                              ...atual,
                              [pergunta.id]: {
                                texto: atual[pergunta.id]?.texto ?? "",
                                nota: e.target.value,
                              },
                            }))
                          }
                        >
                          <option value="">Selecione</option>
                          {(pergunta.question_type === "nps"
                            ? [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                            : [1, 2, 3, 4, 5]
                          ).map((nota) => (
                            <option key={nota} value={nota}>
                              {nota}
                            </option>
                          ))}
                        </Selecao>
                      ) : pergunta.question_type === "yes_no" ? (
                        <Selecao
                          value={respostas[pergunta.id]?.texto ?? ""}
                          onChange={(e) =>
                            setRespostas((atual) => ({
                              ...atual,
                              [pergunta.id]: {
                                texto: e.target.value,
                                nota: atual[pergunta.id]?.nota ?? "",
                              },
                            }))
                          }
                        >
                          <option value="">Selecione</option>
                          <option value="sim">Sim</option>
                          <option value="nao">Não</option>
                        </Selecao>
                      ) : (
                        <AreaDeTexto
                          placeholder={pergunta.placeholder ?? ""}
                          value={respostas[pergunta.id]?.texto ?? ""}
                          onChange={(e) =>
                            setRespostas((atual) => ({
                              ...atual,
                              [pergunta.id]: {
                                texto: e.target.value,
                                nota: atual[pergunta.id]?.nota ?? "",
                              },
                            }))
                          }
                        />
                      )}
                    </Campo>
                  ))}

                  <Campo rotulo="Nota geral do atendimento">
                    <Selecao value={notaGeral} onChange={(e) => setNotaGeral(e.target.value)}>
                      <option value="">Selecione</option>
                      {[1, 2, 3, 4, 5].map((nota) => (
                        <option key={nota} value={nota}>
                          {nota}
                        </option>
                      ))}
                    </Selecao>
                  </Campo>

                  {formulario.service_tags.length > 0 && (
                    <fieldset>
                      <legend className="mb-1.5 text-sm font-medium text-foreground">
                        Sobre qual serviço?
                      </legend>
                      <div className="flex flex-wrap gap-2">
                        {formulario.service_tags.map((tag) => {
                          const marcada = tags.includes(tag.id);
                          return (
                            <button
                              key={tag.id}
                              type="button"
                              onClick={() =>
                                setTags((atual) =>
                                  marcada
                                    ? atual.filter((id) => id !== tag.id)
                                    : [...atual, tag.id],
                                )
                              }
                              className={
                                "rounded-full px-3 py-1 text-sm " +
                                (marcada
                                  ? "bg-primary text-primary-foreground"
                                  : "border border-border text-foreground hover:bg-muted")
                              }
                            >
                              {tag.name}
                            </button>
                          );
                        })}
                      </div>
                    </fieldset>
                  )}
                </div>
              </Cartao>

              <Cartao titulo="Seus dados" descricao="Opcional — ajuda o escritório a retornar.">
                <div className="grid gap-4 sm:grid-cols-3">
                  <Campo rotulo="Nome">
                    <Entrada
                      value={contato.nome}
                      onChange={(e) => setContato({ ...contato, nome: e.target.value })}
                    />
                  </Campo>
                  <Campo rotulo="WhatsApp">
                    <Entrada
                      value={contato.whatsapp}
                      onChange={(e) => setContato({ ...contato, whatsapp: e.target.value })}
                    />
                  </Campo>
                  <Campo rotulo="E-mail">
                    <Entrada
                      type="email"
                      value={contato.email}
                      onChange={(e) => setContato({ ...contato, email: e.target.value })}
                    />
                  </Campo>
                </div>
              </Cartao>

              {erro && <Aviso tom="erro">{erro}</Aviso>}

              <Botao tipo="submit" desabilitado={enviando} className="w-full">
                {enviando ? "Enviando…" : "Enviar avaliação"}
              </Botao>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
