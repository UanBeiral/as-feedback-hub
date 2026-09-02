"use client";

/**
 * Permissões — a matriz de quem avalia quem.
 *
 * É a tela que alimenta a geração de pedidos: abrir um ciclo lê daqui. Sem ela, o
 * sistema tinha um buraco embaraçoso — dava para abrir o ciclo pela interface, mas
 * não para configurar o que ele geraria.
 *
 * `peer_to_peer` cria a recíproca sozinho, no servidor, dentro da mesma transação
 * (BR-MIGRAR-002). A tela não simula isso: ela salva e recarrega, e a recíproca
 * aparece. Foi por duplicar essa lógica no front que o legado ficava com meia relação
 * quando alguém salvava por outro caminho.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Linha,
  Selecao,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Ciclo, Perfil, PermissaoDeFeedback } from "@/lib/tipos";

const TIPOS: { valor: string; rotulo: string; explicacao: string }[] = [
  {
    valor: "peer_to_peer",
    rotulo: "Par (recíproco)",
    explicacao: "Cria também a permissão inversa automaticamente.",
  },
  { valor: "peer", rotulo: "Par (só esta direção)", explicacao: "Sem recíproca." },
  { valor: "manager", rotulo: "Gestor avalia liderado", explicacao: "" },
  { valor: "manager_to_report", rotulo: "Gestor → liderado", explicacao: "" },
  { valor: "upward", rotulo: "Liderado avalia gestor", explicacao: "" },
  { valor: "subordinate", rotulo: "Subordinado", explicacao: "" },
  { valor: "self", rotulo: "Autoavaliação", explicacao: "Único tipo com avaliador = avaliado." },
  { valor: "custom", rotulo: "Personalizada", explicacao: "" },
];

export default function AdminPermissoes() {
  const [permissoes, setPermissoes] = useState<PermissaoDeFeedback[] | null>(null);
  const [pessoas, setPessoas] = useState<Perfil[]>([]);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [filtro, setFiltro] = useState("");
  const [nova, setNova] = useState({
    reviewer_id: "",
    reviewee_id: "",
    permission_type: "peer_to_peer",
    cycle_id: "",
  });

  const carregar = useCallback(async () => {
    const [regras, perfis, listaDeCiclos] = await Promise.all([
      api<PermissaoDeFeedback[]>("/permissions"),
      api<Perfil[]>("/profiles"),
      api<Ciclo[]>("/cycles"),
    ]);
    setPermissoes(regras);
    setPessoas(perfis);
    setCiclos(listaDeCiclos);
  }, []);

  useEffect(() => {
    carregar().catch(() => setPermissoes([]));
  }, [carregar]);

  const nomePor = useMemo(
    () => new Map(pessoas.map((pessoa) => [pessoa.id, pessoa.full_name])),
    [pessoas],
  );

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/permissions", {
        method: "POST",
        body: { ...nova, cycle_id: nova.cycle_id || null },
      });
      setMensagem({
        tom: "sucesso",
        texto:
          nova.permission_type === "peer_to_peer"
            ? "Permissão salva — a recíproca foi criada junto."
            : "Permissão salva.",
      });
      setNova({ ...nova, reviewer_id: "", reviewee_id: "" });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível salvar.",
      });
    }
  }

  async function alternar(regra: PermissaoDeFeedback) {
    setMensagem(null);
    try {
      await api("/permissions", {
        method: "POST",
        body: {
          reviewer_id: regra.reviewer_id,
          reviewee_id: regra.reviewee_id,
          permission_type: regra.permission_type,
          cycle_id: regra.cycle_id,
          active: !regra.active,
        },
      });
      await carregar();
    } catch {
      setMensagem({ tom: "erro", texto: "Não foi possível alterar." });
    }
  }

  const visiveis = (permissoes ?? []).filter((regra) => {
    if (!filtro.trim()) return true;
    const alvo = `${nomePor.get(regra.reviewer_id) ?? ""} ${nomePor.get(regra.reviewee_id) ?? ""}`;
    return alvo.toLowerCase().includes(filtro.toLowerCase());
  });

  const ativas = (permissoes ?? []).filter((regra) => regra.active).length;

  return (
    <PaginaAutenticada
      titulo="Permissões de feedback"
      descricao="Quem avalia quem. É esta matriz que a abertura de ciclo lê para gerar os pedidos."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Nova permissão">
          <form onSubmit={salvar} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Campo rotulo="Avaliador" obrigatorio>
              <Selecao
                required
                value={nova.reviewer_id}
                onChange={(e) => setNova({ ...nova, reviewer_id: e.target.value })}
              >
                <option value="">Selecione</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo rotulo="Avaliado" obrigatorio>
              <Selecao
                required
                value={nova.reviewee_id}
                onChange={(e) => setNova({ ...nova, reviewee_id: e.target.value })}
              >
                <option value="">Selecione</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo
              rotulo="Tipo"
              dica={TIPOS.find((t) => t.valor === nova.permission_type)?.explicacao}
            >
              <Selecao
                value={nova.permission_type}
                onChange={(e) => setNova({ ...nova, permission_type: e.target.value })}
              >
                {TIPOS.map((tipo) => (
                  <option key={tipo.valor} value={tipo.valor}>
                    {tipo.rotulo}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo rotulo="Ciclo" dica="Em branco vale para todos os ciclos.">
              <Selecao
                value={nova.cycle_id}
                onChange={(e) => setNova({ ...nova, cycle_id: e.target.value })}
              >
                <option value="">Permanente</option>
                {ciclos.map((ciclo) => (
                  <option key={ciclo.id} value={ciclo.id}>
                    {ciclo.name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <div className="flex items-end">
              <Botao tipo="submit">Salvar</Botao>
            </div>
          </form>
        </Cartao>

        <Cartao
          titulo={`Matriz (${ativas} ativa${ativas === 1 ? "" : "s"})`}
          acao={
            <input
              type="search"
              placeholder="Filtrar por nome"
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              className="h-9 rounded-md border border-input bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground"
            />
          }
        >
          {permissoes === null ? (
            <Carregando />
          ) : visiveis.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma permissão"
              descricao="Sem permissões ativas, abrir um ciclo não gera pedido nenhum."
            />
          ) : (
            <Tabela colunas={["Avaliador", "Avaliado", "Tipo", "Alcance", "Situação", ""]}>
              {visiveis.map((regra) => (
                <Linha key={regra.id}>
                  <Celula className="font-medium">
                    {nomePor.get(regra.reviewer_id) ?? "—"}
                  </Celula>
                  <Celula>{nomePor.get(regra.reviewee_id) ?? "—"}</Celula>
                  <Celula>
                    {TIPOS.find((t) => t.valor === regra.permission_type)?.rotulo ??
                      regra.permission_type}
                  </Celula>
                  <Celula className="text-muted-foreground">
                    {regra.cycle_id
                      ? (ciclos.find((c) => c.id === regra.cycle_id)?.name ?? "ciclo específico")
                      : "permanente"}
                  </Celula>
                  <Celula>
                    <Selo tom={regra.active ? "sucesso" : "neutro"}>
                      {regra.active ? "ativa" : "inativa"}
                    </Selo>
                  </Celula>
                  <Celula className="text-right">
                    <button
                      type="button"
                      onClick={() => void alternar(regra)}
                      className="text-sm text-primary underline-offset-4 hover:underline"
                    >
                      {regra.active ? "Desativar" : "Ativar"}
                    </button>
                  </Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
