"use client";

/**
 * Histórico da Equipe — três tipos de feedback, um escopo só.
 *
 * As seções são as mesmas do legado (livre, clientes, 360) e o escopo é o resolvido
 * pelo servidor: gestor vê os liderados, coordenador vê a união, admin vê todos. Nenhum
 * filtro desta tela amplia isso — no máximo restringe o que já veio.
 *
 * O 360 não mostra quem escreveu. Não é omissão de tela: o autor não sai da API, porque
 * o anonimato relativo é o que faz as pessoas escreverem o que pensam.
 */

import { useEffect, useMemo, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Carregando, Cartao, EstadoVazio, Selo } from "@/components/ui";
import { api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { HistoricoDaEquipe, ItemDeHistorico } from "@/lib/tipos";

type Aba = "todos" | "livre" | "cliente" | "ciclo";

export default function HistoricoDaEquipePagina() {
  const [historico, setHistorico] = useState<HistoricoDaEquipe | null>(null);
  const [aba, setAba] = useState<Aba>("todos");
  const [busca, setBusca] = useState("");

  useEffect(() => {
    api<HistoricoDaEquipe>("/reports/team-history")
      .then(setHistorico)
      .catch(() => setHistorico({ livre: [], clientes: [], ciclos: [] }));
  }, []);

  const itens = useMemo(() => {
    if (!historico) return [];
    const todos =
      aba === "livre"
        ? historico.livre
        : aba === "cliente"
          ? historico.clientes
          : aba === "ciclo"
            ? historico.ciclos
            : [...historico.livre, ...historico.clientes, ...historico.ciclos];

    const filtrados = busca.trim()
      ? todos.filter((item) =>
          `${item.sobre_nome} ${item.titulo} ${item.detalhe ?? ""}`
            .toLowerCase()
            .includes(busca.toLowerCase()),
        )
      : todos;

    // Ordena do mais recente para o mais antigo, com os sem data no fim.
    return [...filtrados].sort((a, b) => (b.quando ?? "").localeCompare(a.quando ?? ""));
  }, [historico, aba, busca]);

  const contagem = historico
    ? {
        todos: historico.livre.length + historico.clientes.length + historico.ciclos.length,
        livre: historico.livre.length,
        cliente: historico.clientes.length,
        ciclo: historico.ciclos.length,
      }
    : { todos: 0, livre: 0, cliente: 0, ciclo: 0 };

  return (
    <PaginaAutenticada
      titulo="Histórico da equipe"
      descricao="Feedback livre, avaliações de clientes e ciclos 360 — dentro do seu escopo."
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex gap-2">
            {(
              [
                ["todos", "Todos"],
                ["livre", "Feedback livre"],
                ["cliente", "Clientes"],
                ["ciclo", "360"],
              ] as const
            ).map(([chave, rotulo]) => (
              <button
                key={chave}
                type="button"
                onClick={() => setAba(chave)}
                className={
                  "rounded-md px-3 py-1.5 text-sm " +
                  (aba === chave
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-muted")
                }
              >
                {rotulo} ({contagem[chave]})
              </button>
            ))}
          </nav>

          <input
            type="search"
            placeholder="Buscar por pessoa ou conteúdo"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            className="h-9 w-64 rounded-md border border-input bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground"
          />
        </div>

        <Cartao>
          {historico === null ? (
            <Carregando />
          ) : itens.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum histórico encontrado"
              descricao="Feedbacks aparecem aqui conforme forem enviados para a sua equipe."
            />
          ) : (
            <ul className="divide-y divide-border">
              {itens.map((item, indice) => (
                <ItemDoHistorico key={`${item.tipo}-${item.sobre_id}-${indice}`} item={item} />
              ))}
            </ul>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}

const TOM_DO_TIPO = {
  livre: "neutro",
  cliente: "destaque",
  ciclo: "sucesso",
} as const;

const ROTULO_DO_TIPO = {
  livre: "Livre",
  cliente: "Cliente",
  ciclo: "360",
} as const;

function ItemDoHistorico({ item }: { item: ItemDeHistorico }) {
  const tipo = item.tipo as keyof typeof TOM_DO_TIPO;
  return (
    <li className="flex items-start justify-between gap-4 py-3">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
          <Selo tom={TOM_DO_TIPO[tipo] ?? "neutro"}>{ROTULO_DO_TIPO[tipo] ?? item.tipo}</Selo>
          <span>{item.sobre_nome}</span>
        </p>
        <p className="mt-1 text-sm text-foreground">{item.titulo}</p>
        {item.detalhe && (
          <p className="mt-1 text-sm text-muted-foreground">{item.detalhe}</p>
        )}
      </div>

      <div className="shrink-0 text-right">
        <p className="text-xs text-muted-foreground">{formatarDataHora(item.quando)}</p>
        {item.lido_em && (
          <p className="mt-1 text-xs text-success">
            ciente em {formatarDataHora(item.lido_em)}
          </p>
        )}
      </div>
    </li>
  );
}
