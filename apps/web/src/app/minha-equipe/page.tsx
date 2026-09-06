"use client";

/**
 * Minha equipe — uma tela só para gestor, coordenador e administração.
 *
 * No legado eram três (`/gestor/minha-equipe`, `/coordenador/minha-equipe`,
 * `/admin/usuarios` parcial) com a mesma tabela e cálculos de progresso divergentes. O
 * escopo aqui vem inteiro do `TeamScopeService`: gestor vê `manager_id`, coordenador vê
 * a união deduplicada, admin vê todos (BR-MIGRAR-017).
 *
 * A tela é de **acompanhamento**, não de cadastro. Duas contagens diferentes convivem
 * na mesma linha e não devem ser somadas: "a enviar" é o que a pessoa ainda precisa
 * escrever; "a ler" é o que escreveram sobre ela e ela ainda não viu. Num número único,
 * quem já fez a parte dele e só não leu ficaria escondido atrás de quem não fez nada.
 *
 * Todos os números vêm de `/team/progress`, que divide o denominador com o progresso do
 * ciclo (BR-MIGRAR-009) — foi o legado ter três contas diferentes que motivou a regra.
 */

import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  Progresso,
  Selo,
  SeloDePapel,
  Tabela,
} from "@/components/ui";
import { api } from "@/lib/api";
import { ROTULO_DO_STATUS_DE_PESSOA } from "@/lib/formato";
import type { AcompanhamentoDaEquipe, PedidoDeEquipe } from "@/lib/tipos";

/** Estado usado quando a chamada falha: a tela diz "vazio", não fica carregando à toa. */
const SEM_EQUIPE: AcompanhamentoDaEquipe = {
  cycle_id: null,
  cycle_name: null,
  membros: [],
  total_membros: 0,
  enviados: 0,
  esperados: 0,
  percentual: 100,
};

export default function MinhaEquipe() {
  const [equipe, setEquipe] = useState<AcompanhamentoDaEquipe | null>(null);
  const [pedidos, setPedidos] = useState<PedidoDeEquipe[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);

  async function carregar() {
    setEquipe(await api<AcompanhamentoDaEquipe>("/team/progress"));
    try {
      setPedidos(await api<PedidoDeEquipe[]>("/team-requests"));
    } catch {
      // Colaborador comum não tem pedidos para decidir: 403 aqui é esperado e não
      // deve estragar a tela de equipe.
      setPedidos([]);
    }
  }

  useEffect(() => {
    carregar().catch(() => setEquipe(SEM_EQUIPE));
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
      descricao={
        equipe?.cycle_name
          ? `Como a sua equipe está indo no ciclo ${equipe.cycle_name}. Feedback livre e de clientes ficam no Histórico da equipe.`
          : "Quem está no seu escopo — subordinados diretos e, se você coordena, também os membros coordenados."
      }
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
          ) : equipe.membros.length === 0 ? (
            <EstadoVazio
              titulo="Ninguém no seu escopo"
              descricao="Você aparece aqui assim que tiver subordinados ou membros coordenados."
            />
          ) : (
            <>
              {equipe.cycle_id === null && (
                <p className="mb-4 text-sm text-muted-foreground">
                  Nenhum ciclo aberto — as contagens voltam quando o próximo abrir.
                </p>
              )}

              <Tabela
                colunas={["Nome", "Cargo", "Status", "A enviar", "Enviados", "A ler", "Progresso"]}
              >
                {equipe.membros.map((membro) => (
                  <Linha key={membro.profile_id}>
                    <Celula className="font-medium">
                      <span className="flex items-center gap-2">
                        {membro.full_name}
                        {membro.is_coordinator && <SeloDePapel papel={membro.role} coordenador />}
                      </span>
                    </Celula>
                    <Celula>{membro.job_title ?? "—"}</Celula>
                    <Celula>
                      <Selo tom={membro.status === "active" ? "sucesso" : "neutro"}>
                        {ROTULO_DO_STATUS_DE_PESSOA[membro.status] ?? membro.status}
                      </Selo>
                    </Celula>
                    {/* Zero é o caso bom: deixá-lo em cinza faz o olho parar só em quem
                        tem número a resolver. */}
                    <Celula className={membro.pendentes_de_enviar === 0 ? "text-muted-foreground" : ""}>
                      {membro.pendentes_de_enviar}
                    </Celula>
                    <Celula className="text-muted-foreground">{membro.enviados}</Celula>
                    <Celula
                      className={membro.pendentes_de_leitura === 0 ? "text-muted-foreground" : ""}
                    >
                      {membro.pendentes_de_leitura}
                    </Celula>
                    <Celula className="w-48">
                      {/* Quem não tem pedido no ciclo não ganha barra cheia. O serviço
                          trata "0 de 0" como 100% para não dividir por zero, mas na
                          tabela, ao lado de quem tem trabalho de verdade, a barra cheia
                          leria como "está ótimo" quando o caso é "está fora do ciclo". */}
                      {membro.enviados + membro.pendentes_de_enviar === 0 ? (
                        <span className="text-xs text-muted-foreground">fora do ciclo</span>
                      ) : (
                        <Progresso valor={membro.percentual} />
                      )}
                    </Celula>
                  </Linha>
                ))}
              </Tabela>

              <div className="mt-5 border-t border-border pt-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">
                    Progresso geral da equipe
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {equipe.enviados} de {equipe.esperados} feedbacks enviados (
                    {equipe.percentual}%)
                  </span>
                </div>
                <div className="mt-2">
                  <Progresso valor={equipe.percentual} />
                </div>
                <p className="mt-3 text-right text-sm text-muted-foreground">
                  Total de membros na equipe: <strong>{equipe.total_membros}</strong>
                </p>
              </div>
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
