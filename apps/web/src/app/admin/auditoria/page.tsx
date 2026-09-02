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
  Botao,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  Selo,
  Tabela,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { Perfil, RegistroDeAuditoria } from "@/lib/tipos";

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

  const nomePor = new Map(pessoas.map((pessoa) => [pessoa.id, pessoa.full_name]));

  return (
    <PaginaAutenticada
      titulo="Auditoria"
      descricao="Registro permanente de ações sensíveis. Não pode ser editado nem apagado."
    >
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
          <Tabela colunas={["Quando", "Quem fez", "Ação", "Detalhes"]}>
            {registros.map((registro) => (
              <Linha key={registro.id}>
                <Celula className="whitespace-nowrap text-muted-foreground">
                  {formatarDataHora(registro.created_at)}
                </Celula>
                <Celula className="font-medium">
                  {registro.actor_id
                    ? (nomePor.get(registro.actor_id) ?? "(removido)")
                    : "sistema"}
                </Celula>
                <Celula>
                  <Selo tom="neutro">
                    {ROTULO_DA_ACAO[registro.action] ?? registro.action}
                  </Selo>
                </Celula>
                <Celula className="text-xs text-muted-foreground">
                  {registro.details ? (
                    <code className="break-all">{JSON.stringify(registro.details)}</code>
                  ) : (
                    "—"
                  )}
                </Celula>
              </Linha>
            ))}
          </Tabela>
        )}
      </Cartao>
    </PaginaAutenticada>
  );
}
