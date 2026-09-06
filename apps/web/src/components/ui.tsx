"use client";

/**
 * Primitivas de UI.
 *
 * O legado usava shadcn/ui com 48 primitivas; aqui existem as que as telas realmente
 * consomem. Duas regras valem para todas:
 *
 * - **Nenhum literal hexadecimal** (DEV-003): toda cor sai de um token semântico.
 * - **Estado vazio e estado de erro são parte do componente**, não um `if` esquecido na
 *   página. Tela que renderiza tabela vazia sem dizer nada foi a reclamação recorrente
 *   do legado.
 */

import type { ReactNode } from "react";

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function Botao({
  children,
  variante = "primario",
  tipo = "button",
  onClick,
  desabilitado,
  className,
}: {
  children: ReactNode;
  variante?: "primario" | "secundario" | "perigo" | "fantasma";
  tipo?: "button" | "submit";
  onClick?: () => void;
  desabilitado?: boolean;
  className?: string;
}) {
  const variantes = {
    primario: "bg-primary text-primary-foreground hover:opacity-90",
    secundario: "border border-border bg-card text-foreground hover:bg-muted",
    perigo: "bg-destructive text-destructive-foreground hover:opacity-90",
    fantasma: "text-foreground hover:bg-muted",
  } as const;

  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={desabilitado}
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium",
        "transition disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        variantes[variante],
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Cartao({
  titulo,
  descricao,
  acao,
  children,
  className,
}: {
  titulo?: string;
  descricao?: string;
  acao?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-card p-5", className)}>
      {(titulo || acao) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            {titulo && <h2 className="text-base font-semibold text-card-foreground">{titulo}</h2>}
            {descricao && <p className="mt-1 text-sm text-muted-foreground">{descricao}</p>}
          </div>
          {acao}
        </header>
      )}
      {children}
    </section>
  );
}

export function Estatistica({
  rotulo,
  valor,
  detalhe,
}: {
  rotulo: string;
  valor: string | number;
  detalhe?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-sm text-muted-foreground">{rotulo}</p>
      <p className="mt-1 text-2xl font-semibold text-card-foreground">{valor}</p>
      {detalhe && <p className="mt-1 text-xs text-muted-foreground">{detalhe}</p>}
    </div>
  );
}

const TONS = {
  neutro: "bg-muted text-muted-foreground",
  sucesso: "bg-success text-success-foreground",
  alerta: "bg-warning text-warning-foreground",
  perigo: "bg-destructive text-destructive-foreground",
  destaque: "bg-accent text-accent-foreground",
} as const;

export function Selo({
  children,
  tom = "neutro",
}: {
  children: ReactNode;
  tom?: keyof typeof TONS;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        TONS[tom],
      )}
    >
      {children}
    </span>
  );
}

/** Badge de papel com os tokens derivados de DEV-008. */
/**
 * O selo de papel.
 *
 * `papelReal` só aparece quando difere de `papel`: é a troca de contexto de
 * BR-MIGRAR-016 em curso, e sem ela na tela a pessoa esquece que está vendo o sistema
 * pelos olhos de outro papel — e conclui que perdeu acesso.
 */
export function SeloDePapel({
  papel,
  papelReal,
  coordenador,
}: {
  papel: string;
  papelReal?: string;
  coordenador?: boolean;
}) {
  if (coordenador) {
    return (
      <span className="inline-flex items-center rounded-full bg-role-coordinator px-2.5 py-0.5 text-xs font-semibold text-primary-foreground">
        Coordenador
      </span>
    );
  }
  const rotulos: Record<string, string> = {
    admin: "Admin",
    rh: "RH",
    gestor: "Gestor",
    colaborador: "Colaborador",
  };
  const classe =
    papel === "gestor"
      ? "bg-role-manager text-accent-foreground"
      : papel === "colaborador"
        ? "bg-muted text-muted-foreground"
        : "bg-primary text-primary-foreground";
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", classe)}
      title={
        papelReal && papelReal !== papel
          ? `Vendo como ${rotulos[papel] ?? papel}. Seu papel é ${rotulos[papelReal] ?? papelReal}.`
          : undefined
      }
    >
      {rotulos[papel] ?? papel}
      {papelReal && papelReal !== papel && ` (${rotulos[papelReal] ?? papelReal})`}
    </span>
  );
}

export function Campo({
  rotulo,
  children,
  dica,
  ajuda,
  obrigatorio,
}: {
  rotulo: string;
  children: ReactNode;
  /** Texto sempre visível abaixo do controle. */
  dica?: string;
  /** O ⓘ ao lado do rótulo: explica o que o campo faz, sem ocupar linha. */
  ajuda?: string;
  obrigatorio?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-foreground">
        {rotulo}
        {obrigatorio && <span className="ml-1 text-destructive">*</span>}
        {ajuda && (
          <span
            title={ajuda}
            aria-label={ajuda}
            role="note"
            className="ml-1.5 cursor-help text-muted-foreground"
          >
            ⓘ
          </span>
        )}
      </span>
      {children}
      {dica && <span className="mt-1 block text-xs text-muted-foreground">{dica}</span>}
    </label>
  );
}

const CLASSE_ENTRADA =
  "w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground " +
  "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-ring";

export function Entrada(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(CLASSE_ENTRADA, props.className)} />;
}

export function AreaDeTexto(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(CLASSE_ENTRADA, "min-h-24", props.className)} />;
}

export function Selecao(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(CLASSE_ENTRADA, props.className)} />;
}

/**
 * Ordenação da tabela. `campo` é a chave que a página usa para saber por onde ordenar;
 * `null` significa "sem ordenação escolhida", e a tabela fica na ordem que a API mandou.
 */
export type Ordenacao = {
  campo: string | null;
  direcao: "asc" | "desc";
  aoOrdenar: (campo: string) => void;
};

/**
 * Uma coluna. Passe `string` para coluna simples, ou `{ rotulo, campo }` para a coluna
 * ser clicável — `campo` é o que volta em `aoOrdenar`.
 */
export type Coluna = string | { rotulo: string; campo: string };

export function Tabela({
  colunas,
  children,
  vazio,
  ordenacao,
  vazioTexto = "Nada por aqui ainda.",
}: {
  colunas: Coluna[];
  children: ReactNode;
  vazio?: boolean;
  ordenacao?: Ordenacao;
  vazioTexto?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            {colunas.map((coluna) => {
              const rotulo = typeof coluna === "string" ? coluna : coluna.rotulo;
              const campo = typeof coluna === "string" ? null : coluna.campo;
              const ativa = campo !== null && ordenacao?.campo === campo;

              return (
                <th
                  key={rotulo}
                  className="px-3 py-2 font-medium text-muted-foreground"
                  // `aria-sort` é atributo da célula de cabeçalho, não do botão dentro
                  // dela: é o `th` que o leitor de tela anuncia como coluna ordenada.
                  aria-sort={
                    ativa ? (ordenacao?.direcao === "asc" ? "ascending" : "descending") : undefined
                  }
                >
                  {campo && ordenacao ? (
                    <button
                      type="button"
                      onClick={() => ordenacao.aoOrdenar(campo)}
                      className="inline-flex items-center gap-1 hover:text-foreground"
                    >
                      {rotulo}
                      {/* A seta some quando a coluna não é a ordenada. Deixar uma seta
                          neutra em todas faria a ordenada desaparecer no meio delas. */}
                      <span className="text-xs" aria-hidden="true">
                        {ativa ? (ordenacao.direcao === "asc" ? "↑" : "↓") : "↕"}
                      </span>
                    </button>
                  ) : (
                    rotulo
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {vazio ? (
            <tr>
              <td colSpan={colunas.length} className="px-3 py-8 text-center text-muted-foreground">
                {vazioTexto}
              </td>
            </tr>
          ) : (
            children
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Linha({ children }: { children: ReactNode }) {
  return <tr className="border-b border-border last:border-0">{children}</tr>;
}

export function Celula({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={cn("px-3 py-2.5 text-foreground", className)}>{children}</td>;
}

export function Progresso({ valor }: { valor: number }) {
  const seguro = Math.max(0, Math.min(100, valor));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-accent" style={{ width: `${seguro}%` }} />
      </div>
      <span className="w-12 shrink-0 text-right text-xs text-muted-foreground">{seguro}%</span>
    </div>
  );
}

/**
 * Barra de filtros acima de uma tabela: busca à esquerda, seletores no meio, ações à
 * direita.
 *
 * Uma peça só, e não cada tela montando a sua, porque o legado filtra em quase toda
 * tabela e a conferência mostrou o custo de não ter isso: seis telas sem filtro nenhum.
 */
export function BarraDeFiltros({
  busca,
  aoBuscar,
  placeholder = "Buscar…",
  children,
  acoes,
}: {
  busca?: string;
  aoBuscar?: (valor: string) => void;
  placeholder?: string;
  children?: ReactNode;
  acoes?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      {aoBuscar && (
        <input
          type="search"
          value={busca ?? ""}
          onChange={(e) => aoBuscar(e.target.value)}
          placeholder={placeholder}
          className={
            "h-9 w-full max-w-xs rounded-md border border-input bg-card px-3 text-sm " +
            "text-foreground placeholder:text-muted-foreground focus-visible:outline-none " +
            "focus-visible:ring-2 focus-visible:ring-ring"
          }
        />
      )}
      {children}
      {acoes && <span className="ml-auto flex items-center gap-2">{acoes}</span>}
    </div>
  );
}

/** Seletor de filtro. A primeira opção é sempre o "todos", com valor vazio. */
export function FiltroSelecao({
  valor,
  aoMudar,
  opcoes,
  rotuloDeTodos,
}: {
  valor: string;
  aoMudar: (valor: string) => void;
  opcoes: { valor: string; rotulo: string }[];
  rotuloDeTodos: string;
}) {
  return (
    <select
      value={valor}
      onChange={(e) => aoMudar(e.target.value)}
      // Sem `CLASSE_ENTRADA`: ela carrega `w-full`, e `w-auto` depois não vence de
      // forma confiável — a ordem no CSS gerado é que decide, não a da string. Um
      // seletor de filtro esticado empilha a barra inteira.
      className={
        "h-9 rounded-md border border-input bg-card px-3 text-sm text-foreground " +
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      }
      aria-label={rotuloDeTodos}
    >
      <option value="">{rotuloDeTodos}</option>
      {opcoes.map((opcao) => (
        <option key={opcao.valor} value={opcao.valor}>
          {opcao.rotulo}
        </option>
      ))}
    </select>
  );
}

/** Data com rótulo à esquerda, para caber na barra de filtros sem virar formulário. */
export function FiltroDeData({
  rotulo,
  valor,
  aoMudar,
}: {
  rotulo: string;
  valor: string;
  aoMudar: (valor: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      {rotulo}
      <input
        type="date"
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        className={
          "h-9 rounded-md border border-input bg-card px-2 text-sm text-foreground " +
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        }
      />
    </label>
  );
}

/**
 * Escolha de colunas visíveis.
 *
 * `details`/`summary` em vez de um popover próprio: abre, fecha ao clicar fora do
 * conteúdo pelo comportamento nativo, é navegável por teclado sem uma linha de JS e não
 * some quando o React remonta a tabela ao lado.
 *
 * Colunas `fixa` aparecem desabilitadas em vez de sumirem da lista: esconder a coluna
 * que identifica a linha deixa a tabela ilegível, e omitir a caixa faria parecer que a
 * coluna não existe.
 */
export function SeletorDeColunas({
  colunas,
  ocultas,
  aoAlternar,
}: {
  colunas: { chave: string; rotulo: string; fixa?: boolean }[];
  ocultas: string[];
  aoAlternar: (chave: string) => void;
}) {
  const mostrando = colunas.length - ocultas.length;

  return (
    <details className="relative">
      <summary
        className={
          "inline-flex h-9 cursor-pointer list-none items-center rounded-md border " +
          "border-input bg-card px-3 text-sm text-foreground hover:bg-muted"
        }
      >
        Colunas ({mostrando})
      </summary>
      <div
        className={
          "absolute right-0 z-10 mt-1 w-52 rounded-md border border-border bg-card p-2 " +
          "shadow-lg"
        }
      >
        {colunas.map((coluna) => (
          <label
            key={coluna.chave}
            className={
              "flex items-center gap-2 rounded px-2 py-1.5 text-sm text-foreground " +
              (coluna.fixa ? "opacity-60" : "cursor-pointer hover:bg-muted")
            }
          >
            <input
              type="checkbox"
              checked={coluna.fixa || !ocultas.includes(coluna.chave)}
              disabled={coluna.fixa}
              onChange={() => aoAlternar(coluna.chave)}
              className="h-4 w-4 rounded border-input"
            />
            {coluna.rotulo}
          </label>
        ))}
      </div>
    </details>
  );
}

/**
 * Botão de exportar CSV.
 *
 * Desabilitado quando não há linha: exportar um arquivo vazio é o tipo de coisa que a
 * pessoa só descobre depois de abrir a planilha.
 */
export function BotaoDeExportar({
  onClick,
  quantidade,
}: {
  onClick: () => void;
  quantidade: number;
}) {
  return (
    <Botao variante="secundario" onClick={onClick} desabilitado={quantidade === 0}>
      Exportar CSV{quantidade > 0 && ` (${quantidade})`}
    </Botao>
  );
}

/**
 * Contador do que a filtragem deixou passar.
 *
 * Existe para o caso em que o filtro esconde tudo: sem ele, a tabela vazia parece
 * sistema sem dados, e não busca que não achou nada.
 */
export function ContadorDeResultados({ mostrando, total }: { mostrando: number; total: number }) {
  if (mostrando === total) {
    return (
      <span className="text-sm text-muted-foreground">
        {total} {total === 1 ? "resultado" : "resultados"}
      </span>
    );
  }
  return (
    <span className="text-sm text-muted-foreground">
      {mostrando} de {total}
    </span>
  );
}

/**
 * Barras horizontais para comparar poucas categorias.
 *
 * O legado usava barras verticais e uma rosca, com biblioteca de gráfico. Aqui são
 * `div`s: os dados destas telas cabem em menos de dez linhas, a leitura horizontal
 * acomoda nomes longos de departamento sem girar o texto, e uma dependência de gráfico
 * é peso que só se paga quando há gráfico de verdade a desenhar.
 *
 * `total` fixa a escala. Sem ele cada barra viraria percentual de si mesma e a maior
 * ficaria sempre cheia — que é como um gráfico mente sem errar nenhum número.
 */
export function BarrasHorizontais({
  itens,
  total,
  tom = "accent",
}: {
  itens: { rotulo: string; valor: number; detalhe?: string }[];
  total?: number;
  tom?: "accent" | "primary" | "success";
}) {
  const maximo = Math.max(total ?? 0, ...itens.map((i) => i.valor), 1);
  const cores = {
    accent: "bg-accent",
    primary: "bg-primary",
    success: "bg-success",
  } as const;

  if (itens.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Nada a mostrar ainda.</p>;
  }

  return (
    <ul className="space-y-3">
      {itens.map((item) => (
        <li key={item.rotulo}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="truncate text-sm text-foreground">{item.rotulo}</span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {item.detalhe ?? item.valor}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", cores[tom])}
              style={{ width: `${(item.valor / maximo) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Aviso({
  children,
  tom = "neutro",
}: {
  children: ReactNode;
  tom?: "neutro" | "erro" | "sucesso";
}) {
  const tons = {
    neutro: "border-border bg-muted text-foreground",
    erro: "border-destructive bg-destructive/10 text-destructive",
    sucesso: "border-success bg-success/10 text-success",
  } as const;
  return (
    <div className={cn("rounded-md border px-3 py-2 text-sm", tons[tom])} role="status">
      {children}
    </div>
  );
}

export function Carregando({ children = "Carregando…" }: { children?: ReactNode }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{children}</p>;
}

export function EstadoVazio({ titulo, descricao }: { titulo: string; descricao?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center">
      <p className="text-sm font-medium text-foreground">{titulo}</p>
      {descricao && <p className="mt-1 text-sm text-muted-foreground">{descricao}</p>}
    </div>
  );
}
