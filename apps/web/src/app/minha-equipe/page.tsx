"use client";

/**
 * Minha equipe — uma tela só para gestor, coordenador e administração.
 *
 * No legado eram três (`/gestor/minha-equipe`, `/coordenador/minha-equipe`,
 * `/admin/usuarios` parcial) com a mesma tabela e cálculos de progresso divergentes.
 * O escopo aqui vem inteiro de `/auth/my-team`, resolvido pelo `TeamScopeService`:
 * gestor vê `manager_id`, coordenador vê a união deduplicada, admin vê todos
 * (BR-MIGRAR-017).
 */

import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  SeloDePapel,
  Tabela,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { PedidoDeEquipe, Perfil } from "@/lib/tipos";
import { Aviso, Botao } from "@/components/ui";

export default function MinhaEquipe() {
  const [equipe, setEquipe] = useState<Perfil[] | null>(null);
  const [pedidos, setPedidos] = useState<PedidoDeEquipe[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);

  async function carregar() {
    const membros = await api<Perfil[]>("/auth/my-team");
    setEquipe(membros);
    try {
      setPedidos(await api<PedidoDeEquipe[]>("/team-requests"));
    } catch {
      // Colaborador comum não tem pedidos para decidir: 403 aqui é esperado e não
      // deve estragar a tela de equipe.
      setPedidos([]);
    }
  }

  useEffect(() => {
    carregar().catch(() => setEquipe([]));
  }, []);

  async function decidir(id: string, acao: "approve" | "reject") {
    setAviso(null);
    try {
      await api(`/team-requests/${id}/${acao}`, {
        method: "POST",
        body: acao === "reject" ? { motivo: null } : undefined,
      });
      await carregar();
    } catch {
      setAviso("Não foi possível concluir agora.");
    }
  }

  return (
    <PaginaAutenticada
      titulo="Minha equipe"
      descricao="Quem está no seu escopo — subordinados diretos e, se você coordena, também os membros coordenados."
    >
      <div className="space-y-6">
        {aviso && <Aviso tom="erro">{aviso}</Aviso>}

        {pedidos.length > 0 && (
          <Cartao
            titulo="Pedidos de inclusão"
            descricao="Aprovar move a pessoa para a sua equipe."
          >
            <ul className="divide-y divide-border">
              {pedidos.map((pedido) => (
                <li key={pedido.id} className="flex items-center justify-between py-3">
                  <span className="text-sm text-foreground">
                    Inclusão solicitada — aguardando sua decisão
                  </span>
                  <span className="flex gap-2">
                    <Botao onClick={() => void decidir(pedido.id, "approve")}>Aprovar</Botao>
                    <Botao variante="secundario" onClick={() => void decidir(pedido.id, "reject")}>
                      Recusar
                    </Botao>
                  </span>
                </li>
              ))}
            </ul>
          </Cartao>
        )}

        <Cartao titulo="Membros">
          {equipe === null ? (
            <Carregando />
          ) : equipe.length === 0 ? (
            <EstadoVazio
              titulo="Ninguém no seu escopo"
              descricao="Você aparece aqui assim que tiver subordinados ou membros coordenados."
            />
          ) : (
            <Tabela colunas={["Nome", "Cargo", "Papel", "Status"]}>
              {equipe.map((membro) => (
                <Linha key={membro.id}>
                  <Celula className="font-medium">{membro.full_name}</Celula>
                  <Celula>{membro.job_title ?? "—"}</Celula>
                  <Celula>
                    <SeloDePapel papel={membro.role} coordenador={membro.is_coordinator} />
                  </Celula>
                  <Celula className="text-muted-foreground">{membro.status}</Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
