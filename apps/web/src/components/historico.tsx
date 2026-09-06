"use client";

/**
 * O histórico, em duas telas: o da equipe e o meu.
 *
 * As duas mostram as mesmas três seções (livre, cliente, 360) com o mesmo item — muda o
 * escopo, que o servidor resolve, e a ação de dar ciência, que só existe sobre o que é
 * dirigido a mim. Um componente só porque uma segunda cópia divergiria na primeira
 * mudança de rótulo, e o histórico é onde a diferença entre "elogio" e "crítica" já
 * custou uma divergência.
 */

import { useMemo, useState, type ReactNode } from "react";

import { Botao, Carregando, Cartao, EstadoVazio, Selo } from "@/components/ui";
import { formatarDataHora } from "@/lib/formato";
import type { HistoricoDaEquipe, ItemDeHistorico } from "@/lib/tipos";

type Aba = "todos" | "livre" | "cliente" | "ciclo";

const ABAS: [Aba, string][] = [
  ["todos", "Todos"],
  ["livre", "Feedback livre"],
  ["cliente", "Clientes"],
  ["ciclo", "360"],
];

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

export function Historico({
  historico,
  vazio,
  aoMarcarCiente,
}: {
  historico: HistoricoDaEquipe | null;
  vazio: { titulo: string; descricao: string };
  /** Quando existe, o item que ainda não foi lido ganha o botão de ciência. */
  aoMarcarCiente?: (item: ItemDeHistorico) => void | Promise<void>;
}) {
  const [aba, setAba] = useState<Aba>("todos");
  const [busca, setBusca] = useState("");
  const [recentesPrimeiro, setRecentesPrimeiro] = useState(true);

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

    // Item sem data vai para o fim nas duas direções: "sem data" no topo de "mais
    // antigos primeiro" seria uma resposta errada para a pergunta que a ordem faz.
    return [...filtrados].sort((a, b) => {
      if (!a.quando) return 1;
      if (!b.quando) return -1;
      return recentesPrimeiro ? b.quando.localeCompare(a.quando) : a.quando.localeCompare(b.quando);
    });
  }, [historico, aba, busca, recentesPrimeiro]);

  const contagem = historico
    ? {
        todos: historico.livre.length + historico.clientes.length + historico.ciclos.length,
        livre: historico.livre.length,
        cliente: historico.clientes.length,
        ciclo: historico.ciclos.length,
      }
    : { todos: 0, livre: 0, cliente: 0, ciclo: 0 };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex gap-2">
          {ABAS.map(([chave, rotulo]) => (
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

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setRecentesPrimeiro((atual) => !atual)}
            aria-pressed={!recentesPrimeiro}
            className={
              "h-9 rounded-md border border-input bg-card px-3 text-sm text-foreground " +
              "hover:bg-muted"
            }
          >
            {recentesPrimeiro ? "Mais recentes ↓" : "Mais antigos ↑"}
          </button>
          <input
            type="search"
            placeholder="Buscar por pessoa ou conteúdo"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            className={
              "h-9 w-64 rounded-md border border-input bg-card px-3 text-sm text-foreground " +
              "placeholder:text-muted-foreground"
            }
          />
        </div>
      </div>

      <Cartao>
        {historico === null ? (
          <Carregando />
        ) : itens.length === 0 ? (
          <EstadoVazio titulo={vazio.titulo} descricao={vazio.descricao} />
        ) : (
          <ul className="divide-y divide-border">
            {itens.map((item) => (
              <ItemDoHistorico
                key={`${item.tipo}-${item.item_id}`}
                item={item}
                aoMarcarCiente={aoMarcarCiente}
              />
            ))}
          </ul>
        )}
      </Cartao>
    </div>
  );
}

function ItemDoHistorico({
  item,
  aoMarcarCiente,
}: {
  item: ItemDeHistorico;
  aoMarcarCiente?: (item: ItemDeHistorico) => void | Promise<void>;
}) {
  const tipo = item.tipo as keyof typeof TOM_DO_TIPO;
  // Avaliação de cliente não é dirigida a ninguém: é sobre a pessoa, não para ela, e
  // por isso não tem ciência a dar.
  const podeDarCiencia = aoMarcarCiente && !item.lido_em && tipo !== "cliente";

  return (
    <li className="flex items-start justify-between gap-4 py-3">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
          <Selo tom={TOM_DO_TIPO[tipo] ?? "neutro"}>{ROTULO_DO_TIPO[tipo] ?? item.tipo}</Selo>
          <span>{item.sobre_nome}</span>
        </p>
        <p className="mt-1 text-sm text-foreground">{item.titulo}</p>
        {/* Com rotulo, e nao numa frase corrida: elogio e critica sao coisas diferentes
            no formulario, e junta-los apaga a distincao que quem escreveu fez questao de
            manter. O `detalhe` continua existindo para busca e exportacao. */}
        {item.partes.length > 0 ? (
          <dl className="mt-1.5 space-y-1">
            {item.partes.map((parte) => (
              <div key={parte.rotulo}>
                <dt className="text-xs font-medium text-muted-foreground">{parte.rotulo}</dt>
                <dd className="whitespace-pre-wrap text-sm text-foreground">{parte.texto}</dd>
              </div>
            ))}
          </dl>
        ) : (
          item.detalhe && <p className="mt-1 text-sm text-muted-foreground">{item.detalhe}</p>
        )}
      </div>

      <div className="shrink-0 space-y-1 text-right">
        <p className="text-xs text-muted-foreground">{formatarDataHora(item.quando)}</p>
        {item.lido_em ? (
          <Ciencia quando={item.lido_em} quem={item.lido_por} />
        ) : (
          podeDarCiencia && (
            <Botao variante="secundario" onClick={() => void aoMarcarCiente?.(item)}>
              Marcar ciente
            </Botao>
          )
        )}
      </div>
    </li>
  );
}

function Ciencia({ quando, quem }: { quando: string; quem: string | null | undefined }): ReactNode {
  return (
    <p className="text-xs text-success">
      ✅ Ciente em {formatarDataHora(quando)}
      {quem && ` por ${quem}`}
    </p>
  );
}
