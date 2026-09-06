"use client";

/**
 * Início — a mesma rota para todos os papéis.
 *
 * No legado eram quatro telas quase idênticas (`/admin/inicio`, `/gestor/inicio`,
 * `/coordenador/inicio`, `/colaborador/inicio`), e o progresso do ciclo era calculado de
 * um jeito diferente em cada uma. Aqui a rota é uma, e o número vem do
 * `CycleProgressService` — o mesmo que alimenta relatório e dashboard (BR-MIGRAR-009).
 *
 * A tela tem três camadas, e a ordem importa: primeiro o retrato do escritório (os
 * quatro cartões), depois o que **você** deve, e só então os agregados. Quem abre o
 * sistema quer saber se tem trabalho parado antes de olhar gráfico.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  BarrasHorizontais,
  Carregando,
  Cartao,
  Estatistica,
  EstadoVazio,
  Progresso,
  Selo,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatarData, formatarDataHora } from "@/lib/formato";
import { useSessao } from "@/lib/sessao";
import type { AnotacaoDeCiclo, Painel, Requisicao } from "@/lib/tipos";

/** "sexta-feira, 4 de setembro de 2026" — a data por extenso do cabeçalho do legado. */
function dataPorExtenso(): string {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function PaginaInicial() {
  const { usuario } = useSessao();
  const [painel, setPainel] = useState<Painel | null>(null);
  const [pendencias, setPendencias] = useState<Requisicao[]>([]);
  const [anotacoes, setAnotacoes] = useState<AnotacaoDeCiclo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!usuario) return;
    let ativo = true;

    (async () => {
      try {
        const [agregados, minhas] = await Promise.all([
          api<Painel>("/dashboard"),
          api<Requisicao[]>("/requests/mine"),
        ]);
        if (!ativo) return;
        setPainel(agregados);
        setPendencias(minhas);
      } catch {
        if (ativo) setErro("Não foi possível carregar o painel agora.");
      } finally {
        if (ativo) setCarregando(false);
      }

      // As anotações são acessório do painel: quem não puder vê-las não perde a tela
      // inteira por causa disso.
      try {
        const notas = await api<AnotacaoDeCiclo[]>("/cycle-notes");
        if (ativo) setAnotacoes(notas);
      } catch {
        if (ativo) setAnotacoes([]);
      }
    })();

    return () => {
      ativo = false;
    };
  }, [usuario]);

  const progresso = painel?.progresso ?? null;
  const pessoasAnotadas = new Set(anotacoes.map((a) => a.about_user_id)).size;
  const departamentos = painel?.por_departamento ?? [];

  return (
    <PaginaAutenticada
      titulo={`Olá, ${usuario?.full_name.split(" ")[0] ?? ""}`}
      descricao={dataPorExtenso()}
    >
      {carregando ? (
        <Carregando />
      ) : erro ? (
        <Aviso tom="erro">{erro}</Aviso>
      ) : (
        <div className="space-y-6">
          {/* O retrato do escritório, antes de qualquer detalhe. */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Estatistica
              rotulo="Pessoas ativas"
              valor={painel?.pessoas_ativas ?? 0}
              detalhe={
                painel && painel.pessoas_inativas > 0
                  ? `${painel.pessoas_inativas} fora do escritório`
                  : undefined
              }
            />
            <Estatistica
              rotulo="Ciclo atual"
              valor={painel?.cycle_name ?? "Nenhum aberto"}
              detalhe={
                painel?.cycle_end_date
                  ? `até ${formatarData(painel.cycle_end_date)}`
                  : "nenhum ciclo ativo"
              }
            />
            <Estatistica
              rotulo="Taxa de conclusão"
              valor={`${progresso?.percentual ?? 0}%`}
              detalhe={(progresso?.percentual ?? 0) >= 80 ? "no caminho" : "precisa de atenção"}
            />
            <Estatistica
              rotulo="Pendências"
              valor={progresso?.pendentes ?? 0}
              detalhe={progresso?.pendentes === 0 ? "tudo em dia!" : "aguardando resposta"}
            />
          </div>

          {painel?.cycle_id ? (
            <Cartao
              titulo={painel.cycle_name ?? "Ciclo aberto"}
              descricao={`Encerra em ${formatarData(painel.cycle_end_date)}`}
              acao={<Selo tom="destaque">Ciclo aberto</Selo>}
            >
              <div className="space-y-4">
                <Progresso valor={progresso?.percentual ?? 0} />
                <div className="grid gap-3 sm:grid-cols-4">
                  <Estatistica rotulo="Concluídos" valor={progresso?.concluidos ?? 0} />
                  <Estatistica rotulo="Pendentes" valor={progresso?.pendentes ?? 0} />
                  <Estatistica
                    rotulo="Atrasados"
                    valor={progresso?.atrasados ?? 0}
                    detalhe="prazo vencido"
                  />
                  <Estatistica
                    rotulo="Fora da conta"
                    valor={progresso?.excluidos ?? 0}
                    detalhe="cancelados e abdicados"
                  />
                </div>
              </div>
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
                        {/* O nome vem do contrato (`receiver_name`). "Um colega" era
                            texto de espera de quando ele não vinha, e deixava a lista
                            sem dizer qual pedido é qual. */}
                        Feedback sobre {pendencia.receiver_name ?? "um colega"}
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

          <Cartao
            titulo="Minhas anotações"
            descricao="Notas suas sobre a equipe durante o ciclo. Ninguém mais as vê."
            acao={
              <Link
                href="/anotacoes"
                className="text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                Anotar
              </Link>
            }
          >
            {anotacoes.length === 0 ? (
              <EstadoVazio
                titulo="Nenhuma anotação ainda"
                descricao="Anote agora o que você não vai lembrar na conversa de fechamento."
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <Estatistica rotulo="Total de anotações" valor={anotacoes.length} />
                <Estatistica rotulo="Pessoas anotadas" valor={pessoasAnotadas} />
              </div>
            )}
          </Cartao>

          <div className="grid gap-6 lg:grid-cols-2">
            <Cartao
              titulo="Conclusão por departamento"
              descricao="Quantos feedbacks cada área já enviou no ciclo."
            >
              <BarrasHorizontais
                tom="primary"
                itens={departamentos.map((d) => ({
                  rotulo: d.nome,
                  valor: d.enviados,
                  detalhe: `${d.enviados}/${d.esperados} · ${d.percentual}%`,
                }))}
                total={Math.max(...departamentos.map((d) => d.esperados), 1)}
              />
            </Cartao>

            <Cartao titulo="Atividade no ciclo atual" descricao="Os últimos feedbacks enviados.">
              {(painel?.atividade ?? []).length === 0 ? (
                <EstadoVazio titulo="Nenhum feedback enviado neste ciclo" />
              ) : (
                <ul className="divide-y divide-border">
                  {painel?.atividade.map((item, indice) => (
                    <li key={indice} className="py-2.5">
                      <p className="text-sm text-foreground">
                        <strong className="font-medium">{item.avaliador}</strong> avaliou{" "}
                        <strong className="font-medium">{item.avaliado}</strong>
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatarDataHora(item.quando)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Cartao>

            <Cartao titulo="Status das pessoas" descricao="Quem está no escritório hoje.">
              <BarrasHorizontais
                tom="success"
                itens={[
                  { rotulo: "Ativas", valor: painel?.pessoas_ativas ?? 0 },
                  { rotulo: "Inativas ou removidas", valor: painel?.pessoas_inativas ?? 0 },
                ]}
              />
            </Cartao>

            <Cartao titulo="Resumo geral" descricao="Todos os ciclos, desde o começo.">
              <dl className="divide-y divide-border text-sm">
                <div className="flex items-baseline justify-between py-2.5">
                  <dt className="text-muted-foreground">Total de feedbacks</dt>
                  <dd className="text-lg font-semibold text-foreground">
                    {painel?.total_de_feedbacks ?? 0}
                  </dd>
                </div>
                <div className="flex items-baseline justify-between py-2.5">
                  <dt className="text-muted-foreground">Enviados</dt>
                  <dd className="text-lg font-semibold text-success">
                    {painel?.total_enviados ?? 0}
                  </dd>
                </div>
              </dl>
            </Cartao>
          </div>
        </div>
      )}
    </PaginaAutenticada>
  );
}
