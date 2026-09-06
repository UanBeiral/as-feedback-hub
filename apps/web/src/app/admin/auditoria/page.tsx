"use client";

/**
 * Auditoria — trilha append-only de ações sensíveis.
 *
 * Quem aparece na linha é o **ator**: quem fez, não quem sofreu (BR-MIGRAR-026). Era a
 * ambiguidade do legado, onde `user_id` numa remoção de membro não deixava claro se era
 * o gestor ou o removido.
 *
 * Não há como editar nem apagar daqui, e não é limitação de tela: a API só tem inserção.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  BarraDeFiltros,
  Botao,
  BotaoDeExportar,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
  EstadoVazio,
  Estatistica,
  FiltroSelecao,
  Linha,
  Selo,
  Tabela,
} from "@/components/ui";
import { api } from "@/lib/api";
import { exportarCsv } from "@/lib/exportar";
import { formatarDataHora } from "@/lib/formato";
import { useTabela } from "@/lib/tabela";
import type { Perfil, RegistroDeAuditoria, ResumoDeAuditoria } from "@/lib/tipos";

const POR_PAGINA = 50;

/** Ações conhecidas, com um rótulo legível. Desconhecida cai no nome cru. */
const ROTULO_DA_ACAO: Record<string, string> = {
  "user.registered": "Usuário criado",
  "user.password_reset": "Senha redefinida",
  "profile.role_changed": "Papel alterado",
  "profile.flags_changed": "Capacidades alteradas",
  "profile.soft_deleted": "Usuário removido",
  "profile.reactivated": "Usuário reativado",
  "request.cancelled": "Feedback cancelado",
  "team.member_removed": "Membro removido da equipe",
  "team.request_approved": "Pedido de equipe aprovado",
  "team.request_rejected": "Pedido de equipe recusado",
};

export default function AdminAuditoria() {
  const [registros, setRegistros] = useState<RegistroDeAuditoria[] | null>(null);
  const [pessoas, setPessoas] = useState<Perfil[]>([]);
  const [pagina, setPagina] = useState(0);
  const [resumo, setResumo] = useState<ResumoDeAuditoria | null>(null);

  const carregar = useCallback(async (offset: number) => {
    const [linhas, perfis] = await Promise.all([
      api<RegistroDeAuditoria[]>("/audit-logs", {
        query: { limit: POR_PAGINA, offset },
      }),
      api<Perfil[]>("/profiles"),
    ]);
    setRegistros(linhas);
    setPessoas(perfis);
  }, []);

  useEffect(() => {
    carregar(pagina * POR_PAGINA).catch(() => setRegistros([]));
  }, [carregar, pagina]);

  useEffect(() => {
    // Fora do `carregar`: o resumo é do todo e não muda ao virar de página. Recarregá-lo
    // a cada página seria recalcular os mesmos agregados por nada.
    api<ResumoDeAuditoria>("/audit-logs/summary")
      .then(setResumo)
      .catch(() => setResumo(null));
  }, []);

  const nomePor = new Map(pessoas.map((pessoa) => [pessoa.id, pessoa.full_name]));

  // Os últimos 14 dias, inclusive os vazios: a API só manda os dias com atividade, e é a
  // tela que preenche o silêncio. Gráfico com buracos mente sobre o ritmo.
  const catorzeDias = Array.from({ length: 14 }, (_, i) => {
    const data = new Date();
    data.setDate(data.getDate() - (13 - i));
    const dia = data.toISOString().slice(0, 10);
    const registro = resumo?.atividade.find((a) => a.dia === dia);
    return {
      dia,
      rotulo: `${dia.slice(8, 10)}/${dia.slice(5, 7)}`,
      normais: registro?.normais ?? 0,
      sensiveis: registro?.sensiveis ?? 0,
    };
  });
  const pico = Math.max(...catorzeDias.map((d) => d.normais + d.sensiveis), 1);

/**
 * Detalhe da auditoria em português, e não JSON cru.
 *
 * O JSON é o formato de quem grava; quem lê a tela quer saber o que mudou. Chave
 * desconhecida cai no nome cru em vez de sumir — a auditoria não pode esconder o que
 * registrou só porque a tela ainda não sabe nomear.
 */
  function legivel(detalhes: Record<string, unknown> | null): string {
    if (!detalhes || Object.keys(detalhes).length === 0) return "—";

    const rotulos: Record<string, string> = {
      de: "de",
      para: "para",
      campo: "campo",
      nome: "nome",
      motivo: "motivo",
      role: "papel",
      member_id: "membro",
      coordinator_id: "coordenador",
      por: "por",
      vinculo: "vínculo",
    };
    const valores: Record<string, string> = {
      true: "sim",
      false: "não",
      manager: "liderança direta",
      coordination: "coordenação",
    };

    return Object.entries(detalhes)
      .map(([chave, valor]) => {
        const texto = String(valor);
        // uuid não diz nada a quem lê: quando é gente, o nome; senão, o valor.
        const legivelValor = nomePor.get(texto) ?? valores[texto] ?? texto;
        return `${rotulos[chave] ?? chave}: ${legivelValor}`;
      })
      .join(" · ");
  }

  function quemFez(actorId: string | null): string {
    if (!actorId) return "sistema";
    return nomePor.get(actorId) ?? "(removido)";
  }

  const tabela = useTabela(registros ?? [], {
    busca: (r) => [
      quemFez(r.actor_id),
      ROTULO_DA_ACAO[r.action] ?? r.action,
      r.details ? JSON.stringify(r.details) : null,
    ],
    campos: {
      quando: (r) => r.created_at,
      quem: (r) => quemFez(r.actor_id),
      acao: (r) => ROTULO_DA_ACAO[r.action] ?? r.action,
    },
    // O mais recente primeiro: numa auditoria é sempre o que se procura antes.
    inicial: { campo: "quando", direcao: "desc" },
  });
  const porAcao = tabela.filtro("acao", (r, valor) => r.action === valor);
  const visiveis = tabela.visiveis([porAcao]);

  // O seletor lista só as ações presentes nesta página, e não o catálogo inteiro:
  // oferecer filtro que não devolve nada é pior que não oferecer filtro.
  const acoesPresentes = [...new Set((registros ?? []).map((r) => r.action))].sort();

  // O legado tem uma seção "Usuários Removidos" separada da trilha. Aqui ela sai da
  // própria trilha: quem foi removido tem uma linha `profile.soft_deleted`, e essa
  // linha já carrega quem removeu e quando. Uma consulta a mais daria a mesma resposta.
  const removidos = (registros ?? []).filter((r) => r.action === "profile.soft_deleted");

  function exportar() {
    exportarCsv(
      "auditoria",
      ["Quando", "Quem fez", "Ação", "Detalhes"],
      visiveis.map((r) => [
        formatarDataHora(r.created_at),
        quemFez(r.actor_id),
        ROTULO_DA_ACAO[r.action] ?? r.action,
        r.details ? JSON.stringify(r.details) : "",
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Auditoria"
      descricao="Registro completo de todas as ações realizadas no sistema. Não pode ser editado nem apagado."
    >
      {resumo && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Estatistica rotulo="Ações hoje" valor={resumo.hoje} />
            <Estatistica rotulo="Últimos 7 dias" valor={resumo.sete_dias} />
            <Estatistica
              rotulo="Ações sensíveis (7d)"
              valor={resumo.sensiveis_sete_dias}
              detalhe={
                resumo.sensiveis_sete_dias === 0
                  ? "nada a revisar"
                  : "mudaram poder ou apagaram trabalho"
              }
            />
            <Estatistica
              rotulo={resumo.mais_ativo_nome ?? "Ninguém agiu"}
              valor={resumo.mais_ativo_acoes}
              detalhe="ações nos últimos 7 dias"
            />
          </div>

          {removidos.length > 0 && (
        <Cartao
          titulo={`Usuários removidos (${removidos.length})`}
          descricao="O acesso caiu na hora; o histórico ficou (BR-MIGRAR-018)."
          className="mb-6"
        >
          <ul className="divide-y divide-border">
            {removidos.map((registro) => (
              <li key={registro.id} className="flex items-center justify-between py-2.5 text-sm">
                <span className="text-foreground">
                  {registro.record_id ? (nomePor.get(registro.record_id) ?? "(já sem perfil)") : "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  por {quemFez(registro.actor_id)} · {formatarDataHora(registro.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      <Cartao
            titulo="Atividade — últimos 14 dias"
            className="mb-6"
            acao={
              <span className="flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-primary" /> Normal
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-destructive" /> Sensível
                </span>
              </span>
            }
          >
            {/* `items-stretch` (o padrão) e `h-full` na coluna: sem altura definida no
                pai, a altura em porcentagem das barras resolve para zero e o gráfico
                aparece vazio mesmo com dados. */}
            <div className="flex h-40 gap-1.5">
              {catorzeDias.map((dia) => (
                <div key={dia.dia} className="flex h-full flex-1 flex-col items-center gap-1">
                  <span className="flex w-full flex-1 flex-col justify-end">
                    {/* Empilhado, e não lado a lado: a altura total é a atividade do dia,
                        e a fatia vermelha é a parte dela que pede olho. */}
                    <span
                      className="w-full rounded-t-sm bg-destructive"
                      style={{ height: `${(dia.sensiveis / pico) * 100}%` }}
                      title={`${dia.sensiveis} sensível(is)`}
                    />
                    <span
                      className="w-full bg-primary"
                      style={{ height: `${(dia.normais / pico) * 100}%` }}
                      title={`${dia.normais} normal(is)`}
                    />
                  </span>
                  <span className="text-[10px] text-muted-foreground">{dia.rotulo}</span>
                </div>
              ))}
            </div>
          </Cartao>
        </>
      )}

      {removidos.length > 0 && (
        <Cartao
          titulo={`Usuários removidos (${removidos.length})`}
          descricao="O acesso caiu na hora; o histórico ficou (BR-MIGRAR-018)."
          className="mb-6"
        >
          <ul className="divide-y divide-border">
            {removidos.map((registro) => (
              <li key={registro.id} className="flex items-center justify-between py-2.5 text-sm">
                <span className="text-foreground">
                  {registro.record_id ? (nomePor.get(registro.record_id) ?? "(já sem perfil)") : "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  por {quemFez(registro.actor_id)} · {formatarDataHora(registro.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      <Cartao
        acao={
          <span className="flex gap-2">
            <Botao
              variante="secundario"
              desabilitado={pagina === 0}
              onClick={() => setPagina((p) => Math.max(0, p - 1))}
            >
              Anterior
            </Botao>
            <Botao
              variante="secundario"
              desabilitado={(registros?.length ?? 0) < POR_PAGINA}
              onClick={() => setPagina((p) => p + 1)}
            >
              Próxima
            </Botao>
          </span>
        }
      >
        {registros === null ? (
          <Carregando />
        ) : registros.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum registro nesta página"
            descricao="Ações sensíveis aparecem aqui assim que acontecem."
          />
        ) : (
          <>
          <BarraDeFiltros
            busca={tabela.busca}
            aoBuscar={tabela.setBusca}
            placeholder="Buscar por pessoa, ação ou detalhe…"
            acoes={
              <>
                <ContadorDeResultados mostrando={visiveis.length} total={registros.length} />
                <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
              </>
            }
          >
            <FiltroSelecao
              rotuloDeTodos="Todas as ações"
              valor={porAcao.valor}
              aoMudar={porAcao.aoMudar}
              opcoes={acoesPresentes.map((acao) => ({
                valor: acao,
                rotulo: ROTULO_DA_ACAO[acao] ?? acao,
              }))}
            />
          </BarraDeFiltros>

          <Tabela
            ordenacao={tabela.ordenacao}
            vazio={visiveis.length === 0}
            vazioTexto="Nenhum registro com esses filtros nesta página."
            colunas={[
              { rotulo: "Quando", campo: "quando" },
              { rotulo: "Quem fez", campo: "quem" },
              { rotulo: "Ação", campo: "acao" },
              "Detalhes",
            ]}
          >
            {visiveis.map((registro) => (
              <Linha key={registro.id}>
                <Celula className="whitespace-nowrap text-muted-foreground">
                  {formatarDataHora(registro.created_at)}
                </Celula>
                <Celula className="font-medium">{quemFez(registro.actor_id)}</Celula>
                <Celula>
                  <Selo tom="neutro">
                    {ROTULO_DA_ACAO[registro.action] ?? registro.action}
                  </Selo>
                </Celula>
                <Celula className="text-xs text-muted-foreground">
                  {legivel(registro.details)}
                </Celula>
              </Linha>
            ))}
          </Tabela>
          </>
        )}
      </Cartao>
    </PaginaAutenticada>
  );
}
