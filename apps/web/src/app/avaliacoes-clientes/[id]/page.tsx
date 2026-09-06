"use client";

/**
 * O que o cliente respondeu, pergunta por pergunta.
 *
 * Esta tela existe porque não existia: o wizard público gravava as nove respostas e
 * endpoint nenhum as lia de volta. O escritório via a nota, a recomendação e o
 * sinalizador de negativa — o texto que o cliente escreveu ficava no banco, que é
 * justamente o dado que o fluxo inteiro existe para coletar.
 *
 * A pergunta vem do servidor junto com a resposta, e não de uma lista fixa aqui: o
 * formulário é editável (SCR-0043), e rótulos no front mostrariam a pergunta de hoje ao
 * lado da resposta de seis meses atrás.
 *
 * Quem não pode ler recebe 404, não 403 — o erro não confirma que a avaliação existe nem
 * sobre quem ela é.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Carregando, Cartao, EstadoVazio, Estatistica, Selo } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { DetalheDaAvaliacao } from "@/lib/tipos";

/** Os rótulos do wizard. Motivação é catálogo fechado, ao contrário das perguntas. */
const ROTULO_DA_MOTIVACAO: Record<string, string> = {
  praise: "Quero elogiar",
  evaluate: "Quero avaliar o atendimento",
  problem: "Tive um problema",
  other: "Outro motivo",
};

export default function DetalheDaAvaliacaoDeCliente() {
  const { id } = useParams<{ id: string }>();
  const [detalhe, setDetalhe] = useState<DetalheDaAvaliacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api<DetalheDaAvaliacao>(`/client-eval/evaluations/${id}`)
      .then(setDetalhe)
      .catch((falha) =>
        setErro(
          falha instanceof ApiError && falha.status === 404
            ? "Avaliação não encontrada, ou fora do que você pode ver."
            : "Não foi possível carregar a avaliação.",
        ),
      );
  }, [id]);

  if (erro) {
    return (
      <PaginaAutenticada titulo="Avaliação de cliente">
        <Cartao>
          <EstadoVazio titulo={erro} />
          <Voltar />
        </Cartao>
      </PaginaAutenticada>
    );
  }

  if (detalhe === null) {
    return (
      <PaginaAutenticada titulo="Avaliação de cliente">
        <Cartao>
          <Carregando />
        </Cartao>
      </PaginaAutenticada>
    );
  }

  const { avaliacao } = detalhe;

  return (
    <PaginaAutenticada
      titulo={avaliacao.client_name ?? "Cliente sem nome"}
      descricao={`Sobre ${detalhe.avaliado_nome} · respondida em ${formatarDataHora(
        avaliacao.submitted_at,
      )}`}
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Estatistica
            rotulo="Nota geral"
            valor={avaliacao.overall_rating ?? "—"}
            detalhe={avaliacao.has_negative ? "sinalizada para atenção" : undefined}
          />
          <Estatistica rotulo="Recomendaria" valor={avaliacao.recommendation_rating ?? "—"} />
          <Estatistica
            rotulo="Serviços"
            valor={detalhe.servicos.length}
            detalhe={detalhe.servicos.join(", ") || "nenhum marcado"}
          />
        </div>

        <Cartao titulo="Contato">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Linha rotulo="Cliente" valor={avaliacao.client_name} />
            {/* Mascarado para quem não é admin/RH — o servidor decide, não esta tela
                (BR-MIGRAR-022). */}
            <Linha rotulo="WhatsApp" valor={avaliacao.client_whatsapp} mono />
            <Linha rotulo="E-mail" valor={avaliacao.client_email} />
            <Linha
              rotulo="Motivo do contato"
              valor={
                detalhe.motivacao
                  ? (ROTULO_DA_MOTIVACAO[detalhe.motivacao] ?? detalhe.motivacao)
                  : null
              }
            />
            {detalhe.motivacao_texto && (
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium text-muted-foreground">
                  O que o cliente contou
                </dt>
                <dd className="mt-1 whitespace-pre-wrap text-sm text-foreground">
                  {detalhe.motivacao_texto}
                </dd>
              </div>
            )}
          </dl>
        </Cartao>

        <Cartao
          titulo="Respostas"
          descricao="Na ordem em que o cliente as respondeu."
          acao={
            avaliacao.has_negative ? <Selo tom="perigo">Sinalizada para atenção</Selo> : undefined
          }
        >
          {detalhe.respostas.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma resposta gravada"
              descricao="A avaliação foi enviada sem responder às perguntas do formulário."
            />
          ) : (
            <ol className="divide-y divide-border">
              {detalhe.respostas.map((resposta) => (
                <li key={resposta.question_id} className="py-4 first:pt-0 last:pb-0">
                  <p className="text-sm font-medium text-foreground">{resposta.pergunta}</p>
                  <div className="mt-1.5">
                    {resposta.nota !== null && (
                      <Nota valor={resposta.nota} tipo={resposta.tipo} />
                    )}
                    {resposta.texto && (
                      <p className="whitespace-pre-wrap text-sm text-foreground">
                        {resposta.texto}
                      </p>
                    )}
                    {resposta.nota === null && !resposta.texto && (
                      <p className="text-sm text-muted-foreground">Sem resposta.</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Cartao>

        <Voltar />
      </div>
    </PaginaAutenticada>
  );
}

function Voltar() {
  return (
    <Link
      href="/avaliacoes-clientes"
      className="text-sm font-medium text-primary underline-offset-4 hover:underline"
    >
      ← Voltar para as avaliações
    </Link>
  );
}

function Linha({
  rotulo,
  valor,
  mono,
}: {
  rotulo: string;
  valor: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground">{rotulo}</dt>
      <dd className={"text-sm text-foreground " + (mono ? "font-mono" : "")}>{valor ?? "—"}</dd>
    </div>
  );
}

/**
 * A nota com a escala da própria pergunta.
 *
 * O denominador vem do `tipo` que o servidor manda, e não do valor: inferir "3 deve ser
 * de 0 a 5" transformaria um 3 de zero a dez num elogio. `yes_no` guarda 1 e 0 no mesmo
 * campo de nota, e "1 / 10" ali seria leitura errada de um "sim".
 */
function Nota({ valor, tipo }: { valor: number; tipo: string }) {
  if (tipo === "yes_no") {
    return <p className="text-sm font-semibold text-foreground">{valor ? "Sim" : "Não"}</p>;
  }
  return (
    <p className="text-sm text-foreground">
      <span className="font-semibold">{valor}</span>
      <span className="text-muted-foreground"> / 10</span>
    </p>
  );
}
