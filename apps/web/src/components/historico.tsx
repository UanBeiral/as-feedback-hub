"use client";

/**
 * O histórico, em três telas: o da equipe, o de uma pessoa e o meu.
 *
 * As três mostram as mesmas seções (livre, cliente, 360) com o mesmo item — muda o
 * escopo, que o servidor resolve, e a ação de dar ciência, que só existe sobre o que é
 * dirigido a mim. Um componente só porque uma segunda cópia divergiria na primeira
 * mudança de rótulo, e o histórico é onde a diferença entre "elogio" e "crítica" já
 * custou uma divergência.
 *
 * Os filtros são os do legado, por seção: no feedback livre, a ciência; no 360, o
 * status do pedido, os cancelados (ocultos por padrão), o período e a ordem A-Z. Busca
 * e ordenação por data valem para todas. Tudo no navegador: a lista já veio inteira.
 */

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";

import {
  Botao,
  Carregando,
  Cartao,
  EstadoVazio,
  FiltroDeData,
  FiltroSelecao,
  Selo,
} from "@/components/ui";
import { ROTULO_DO_REQUEST, formatarDataHora } from "@/lib/formato";
import type { HistoricoDaEquipe, ItemDeHistorico } from "@/lib/tipos";

type Aba = "todos" | "livre" | "cliente" | "ciclo";
type Ordem = "data-desc" | "data-asc" | "nome";

const ABAS: [Aba, string][] = [
  ["todos", "Todos os tipos"],
  ["livre", "Feedback Livre"],
  ["cliente", "Avaliações de Clientes"],
  ["ciclo", "360° — Ciclos de Feedback"],
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

const TOM_DO_STATUS: Record<string, "neutro" | "sucesso" | "alerta" | "perigo"> = {
  pending: "alerta",
  draft: "neutro",
  submitted: "sucesso",
  waived: "neutro",
  cancelled: "perigo",
  expired: "perigo",
};

export function Historico({
  historico,
  vazio,
  aoMarcarCiente,
  comLinkParaPessoa,
}: {
  historico: HistoricoDaEquipe | null;
  vazio: { titulo: string; descricao: string };
  /** Quando existe, o item que ainda não foi lido ganha o botão de ciência. */
  aoMarcarCiente?: (item: ItemDeHistorico) => void | Promise<void>;
  /** Liga o nome ao histórico daquela pessoa (SCR-0037). Desligado na tela dela. */
  comLinkParaPessoa?: boolean;
}) {
  const [aba, setAba] = useState<Aba>("todos");
  const [busca, setBusca] = useState("");
  const [ordem, setOrdem] = useState<Ordem>("data-desc");
  const [ciencia, setCiencia] = useState("");
  const [status, setStatus] = useState("");
  const [comCancelados, setComCancelados] = useState(false);
  const [desde, setDesde] = useState("");
  const [ate, setAte] = useState("");

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

    const filtrados = todos.filter((item) => {
      // Cancelado fica oculto por padrão, como no legado: é ruído para quem quer saber
      // o que a equipe recebeu, e o toggle existe para quem precisa auditar.
      if (!comCancelados && item.status === "cancelled") return false;
      if (status && item.tipo === "ciclo" && item.status !== status) return false;
      if (ciencia === "com" && item.tipo === "livre" && !item.lido_em) return false;
      if (ciencia === "sem" && item.tipo === "livre" && item.lido_em) return false;
      if (desde && (!item.quando || item.quando.slice(0, 10) < desde)) return false;
      if (ate && (!item.quando || item.quando.slice(0, 10) > ate)) return false;
      if (busca.trim()) {
        const alvo =
          `${item.sobre_nome} ${item.autor_nome ?? ""} ${item.titulo} ${item.detalhe ?? ""}`.toLowerCase();
        if (!alvo.includes(busca.toLowerCase())) return false;
      }
      return true;
    });

    // Item sem data vai para o fim nas duas direções: "sem data" no topo de "mais
    // antigos primeiro" seria uma resposta errada para a pergunta que a ordem faz.
    return [...filtrados].sort((a, b) => {
      if (ordem === "nome") return a.sobre_nome.localeCompare(b.sobre_nome, "pt-BR");
      if (!a.quando) return 1;
      if (!b.quando) return -1;
      return ordem === "data-desc"
        ? b.quando.localeCompare(a.quando)
        : a.quando.localeCompare(b.quando);
    });
  }, [historico, aba, busca, ordem, ciencia, status, comCancelados, desde, ate]);

  const contagem = historico
    ? {
        todos: historico.livre.length + historico.clientes.length + historico.ciclos.length,
        livre: historico.livre.length,
        cliente: historico.clientes.length,
        ciclo: historico.ciclos.length,
      }
    : { todos: 0, livre: 0, cliente: 0, ciclo: 0 };

  const mostraFiltrosDe360 = aba === "ciclo" || aba === "todos";
  const mostraFiltrosDeLivre = aba === "livre" || aba === "todos";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <nav className="flex flex-wrap gap-2" aria-label="Exibir">
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
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          placeholder={mostraFiltrosDe360 ? "Avaliador ou avaliado..." : "Buscar por nome..."}
          value={busca}
          onChange={(evento) => setBusca(evento.target.value)}
          className={
            "h-9 w-56 rounded-md border border-input bg-card px-3 text-sm text-foreground " +
            "placeholder:text-muted-foreground"
          }
        />

        {mostraFiltrosDeLivre && (
          <FiltroSelecao
            rotuloDeTodos="Todos"
            valor={ciencia}
            aoMudar={setCiencia}
            opcoes={[
              { valor: "com", rotulo: "Com ciência" },
              { valor: "sem", rotulo: "Sem ciência" },
            ]}
          />
        )}

        {mostraFiltrosDe360 && (
          <>
            <FiltroSelecao
              rotuloDeTodos="Status: todos"
              valor={status}
              aoMudar={setStatus}
              opcoes={[
                { valor: "pending", rotulo: "Pendente" },
                { valor: "draft", rotulo: "Rascunho" },
                { valor: "submitted", rotulo: "Enviado" },
                { valor: "waived", rotulo: "Abdicado" },
              ]}
            />
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              Cancelados
              <input
                type="checkbox"
                checked={comCancelados}
                onChange={(e) => setComCancelados(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span className="text-xs">{comCancelados ? "Visíveis" : "Ocultos"}</span>
            </label>
            <FiltroDeData rotulo="De" valor={desde} aoMudar={setDesde} />
            <FiltroDeData rotulo="Até" valor={ate} aoMudar={setAte} />
          </>
        )}

        <span className="ml-auto flex gap-1">
          <BotaoDeOrdem ativo={ordem === "nome"} onClick={() => setOrdem("nome")}>
            A-Z
          </BotaoDeOrdem>
          <BotaoDeOrdem
            ativo={ordem !== "nome"}
            onClick={() => setOrdem(ordem === "data-desc" ? "data-asc" : "data-desc")}
          >
            Data {ordem === "data-asc" ? "↑" : "↓"}
          </BotaoDeOrdem>
        </span>
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
                comLinkParaPessoa={comLinkParaPessoa}
              />
            ))}
          </ul>
        )}
      </Cartao>
    </div>
  );
}

function BotaoDeOrdem({
  ativo,
  onClick,
  children,
}: {
  ativo: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={ativo}
      className={
        "h-9 rounded-md border px-3 text-sm " +
        (ativo
          ? "border-primary bg-primary text-primary-foreground"
          : "border-input bg-card text-foreground hover:bg-muted")
      }
    >
      {children}
    </button>
  );
}

function ItemDoHistorico({
  item,
  aoMarcarCiente,
  comLinkParaPessoa,
}: {
  item: ItemDeHistorico;
  aoMarcarCiente?: (item: ItemDeHistorico) => void | Promise<void>;
  comLinkParaPessoa?: boolean;
}) {
  const tipo = item.tipo as keyof typeof TOM_DO_TIPO;
  // Avaliação de cliente não é dirigida a ninguém: é sobre a pessoa, não para ela, e
  // por isso não tem ciência a dar.
  const podeDarCiencia = aoMarcarCiente && !item.lido_em && tipo !== "cliente";

  const nome = comLinkParaPessoa ? (
    <Link href={`/historico/${item.sobre_id}`} className="text-primary underline-offset-4 hover:underline">
      {item.sobre_nome}
    </Link>
  ) : (
    <span>{item.sobre_nome}</span>
  );

  return (
    <li className="flex items-start justify-between gap-4 py-3">
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
          <Selo tom={TOM_DO_TIPO[tipo] ?? "neutro"}>{ROTULO_DO_TIPO[tipo] ?? item.tipo}</Selo>
          {tipo === "livre" ? (
            // "Para: X · De: Y", como no legado. O anônimo não tem autor no banco
            // (AMB-001), e o histórico diz isso em vez de esconder o campo.
            <span>
              Para: {nome} · De: {item.autor_nome ?? "anônimo"}
            </span>
          ) : (
            nome
          )}
          {tipo === "ciclo" && item.status && (
            <Selo tom={TOM_DO_STATUS[item.status] ?? "neutro"}>
              {ROTULO_DO_REQUEST[item.status] ?? item.status}
            </Selo>
          )}
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
