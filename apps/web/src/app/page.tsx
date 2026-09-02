"use client";

/**
 * Início — a mesma rota para todos os papéis.
 *
 * No legado eram quatro telas quase idênticas (`/admin/inicio`, `/gestor/inicio`,
 * `/coordenador/inicio`, `/colaborador/inicio`), e o progresso do ciclo era calculado
 * de um jeito diferente em cada uma. Aqui a rota é uma, e o número vem do
 * `CycleProgressService` — o mesmo que alimenta relatório e dashboard (BR-MIGRAR-009).
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Carregando,
  Cartao,
  Estatistica,
  EstadoVazio,
  Progresso,
  Selo,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { useSessao } from "@/lib/sessao";
import type { Ciclo, Progresso as ProgressoDto, Requisicao } from "@/lib/tipos";

export default function PaginaInicial() {
  const { usuario } = useSessao();
  const [ciclo, setCiclo] = useState<Ciclo | null>(null);
  const [progresso, setProgresso] = useState<ProgressoDto | null>(null);
  const [pendencias, setPendencias] = useState<Requisicao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!usuario) return;
    let ativo = true;

    (async () => {
      try {
        const [ciclos, minhas] = await Promise.all([
          api<Ciclo[]>("/cycles", { query: { status: "open" } }),
          api<Requisicao[]>("/requests/mine"),
        ]);
        if (!ativo) return;

        const aberto = ciclos[0] ?? null;
        setCiclo(aberto);
        setPendencias(minhas);

        if (aberto) {
          const numeros = await api<ProgressoDto>(`/cycles/${aberto.id}/progress`);
          if (ativo) setProgresso(numeros);
        }
      } catch {
        if (ativo) setErro("Não foi possível carregar o painel agora.");
      } finally {
        if (ativo) setCarregando(false);
      }
    })();

    return () => {
      ativo = false;
    };
  }, [usuario]);

  return (
    <PaginaAutenticada
      titulo={`Olá, ${usuario?.full_name.split(" ")[0] ?? ""}`}
      descricao="Seu resumo do ciclo e o que ainda espera resposta."
    >
      {carregando ? (
        <Carregando />
      ) : erro ? (
        <Aviso tom="erro">{erro}</Aviso>
      ) : (
        <div className="space-y-6">
          {ciclo ? (
            <Cartao
              titulo={ciclo.name}
              descricao={`Período: ${formatarData(ciclo.start_date)} a ${formatarData(ciclo.end_date)}`}
              acao={<Selo tom="destaque">Ciclo aberto</Selo>}
            >
              {progresso && (
                <div className="space-y-4">
                  <Progresso valor={progresso.percentual} />
                  <div className="grid gap-3 sm:grid-cols-4">
                    <Estatistica rotulo="Concluídos" valor={progresso.concluidos} />
                    <Estatistica rotulo="Pendentes" valor={progresso.pendentes} />
                    <Estatistica
                      rotulo="Atrasados"
                      valor={progresso.atrasados}
                      detalhe="prazo vencido"
                    />
                    <Estatistica
                      rotulo="Fora da conta"
                      valor={progresso.excluidos}
                      detalhe="cancelados e abdicados"
                    />
                  </div>
                </div>
              )}
            </Cartao>
          ) : (
            <EstadoVazio
              titulo="Nenhum ciclo aberto"
              descricao="Quando a administração abrir um ciclo, ele aparece aqui."
            />
          )}

          <Cartao
            titulo="Seus feedbacks pendentes"
            descricao="O que está esperando você responder."
          >
            {pendencias.length === 0 ? (
              <EstadoVazio titulo="Nada pendente" descricao="Você está em dia." />
            ) : (
              <ul className="divide-y divide-border">
                {pendencias.map((pendencia) => (
                  <li key={pendencia.id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm text-foreground">
                        Feedback sobre um colega
                        {pendencia.due_date && (
                          <span className="ml-2 text-xs text-muted-foreground">
                            prazo {formatarData(pendencia.due_date)}
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {pendencia.status === "draft" ? "Rascunho salvo" : "Ainda não iniciado"}
                      </p>
                    </div>
                    <Link
                      href={`/meus-feedbacks/${pendencia.id}`}
                      className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                    >
                      {pendencia.status === "draft" ? "Continuar" : "Responder"}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>
        </div>
      )}
    </PaginaAutenticada>
  );
}
