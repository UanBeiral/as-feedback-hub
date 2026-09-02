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
export function SeloDePapel({ papel, coordenador }: { papel: string; coordenador?: boolean }) {
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
    >
      {rotulos[papel] ?? papel}
    </span>
  );
}

export function Campo({
  rotulo,
  children,
  dica,
  obrigatorio,
}: {
  rotulo: string;
  children: ReactNode;
  dica?: string;
  obrigatorio?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-foreground">
        {rotulo}
        {obrigatorio && <span className="ml-1 text-destructive">*</span>}
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

export function Tabela({
  colunas,
  children,
  vazio,
}: {
  colunas: string[];
  children: ReactNode;
  vazio?: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            {colunas.map((coluna) => (
              <th key={coluna} className="px-3 py-2 font-medium text-muted-foreground">
                {coluna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {vazio ? (
            <tr>
              <td colSpan={colunas.length} className="px-3 py-8 text-center text-muted-foreground">
                Nada por aqui ainda.
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
