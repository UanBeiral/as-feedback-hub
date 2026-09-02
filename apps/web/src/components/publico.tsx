"use client";

/**
 * Primitivas do fluxo público de avaliação (SCR-0035).
 *
 * Vivem separadas de `ui.tsx` de propósito. O wizard público é a única superfície do
 * sistema aberta na internet e tem **identidade visual própria** — gradiente roxo, card
 * único centrado, sem shell autenticado (DEV-008). Reaproveitar as primitivas do app
 * interno aqui faria a tela do cliente herdar, em silêncio, cada mudança pensada para a
 * tela do funcionário.
 *
 * Duas regras seguem valendo:
 *
 * - **Nenhum literal hexadecimal** (DEV-003): as cores saem de `--public-gradient-*` e
 *   dos tokens semânticos.
 * - **Nada aqui sabe o que é uma pergunta.** Estas peças desenham; quem decide o que
 *   mostrar é a página.
 */

import type { ReactNode } from "react";

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ ícones
 *
 * Desenhados à mão em vez de trazer uma biblioteca de ícones: são seis, e uma
 * dependência a mais na única página que um estranho carrega é peso mal gasto.
 */

type PropsDeIcone = { className?: string };

export function IconeCoracao({ className }: PropsDeIcone) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 20.5 3.9 12.6a5 5 0 1 1 7.1-7.1l1 1 1-1a5 5 0 1 1 7.1 7.1Z" strokeLinejoin="round" />
    </svg>
  );
}

export function IconeEstrela({ className, preenchida }: PropsDeIcone & { preenchida?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill={preenchida ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.6"
      className={className}
      aria-hidden="true"
    >
      <path
        d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9Z"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IconeAlerta({ className }: PropsDeIcone) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M10.3 3.9 1.8 18.3A2 2 0 0 0 3.5 21.3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"
        strokeLinejoin="round"
      />
      <path d="M12 9v4.5M12 17.2v.01" strokeLinecap="round" />
    </svg>
  );
}

export function IconeBalao({ className }: PropsDeIcone) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.9-.9L3 20.5l1.5-4.6A8.4 8.4 0 0 1 12 3.1a8.4 8.4 0 0 1 9 8.4Z"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IconeRelogio({ className }: PropsDeIcone) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      className={className}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.2V12l3 1.8" strokeLinecap="round" />
    </svg>
  );
}

export function IconeCheck({ className }: PropsDeIcone) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      className={className}
      aria-hidden="true"
    >
      <path d="m5 12.8 4.5 4.4L19 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconeSeta({ para }: { para: "esquerda" | "direita" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        d={para === "direita" ? "m9 5 7 7-7 7" : "m15 5-7 7 7 7"}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ moldura */

/**
 * A página inteira: barra de progresso colada no topo da janela e um card só no meio.
 *
 * A barra fica **fora** do card, atravessando a viewport, como no oráculo — é o que dá
 * ao cliente a noção de "quanto falta" antes mesmo de ele ler o card.
 */
export function MolduraDoWizard({
  progresso,
  children,
}: {
  progresso: number | null;
  children: ReactNode;
}) {
  const seguro = Math.max(0, Math.min(100, progresso ?? 0));
  return (
    <main className="min-h-screen bg-publico-fundo">
      <div
        className="h-1 w-full"
        role={progresso === null ? undefined : "progressbar"}
        aria-valuenow={progresso === null ? undefined : Math.round(seguro)}
        aria-valuemin={progresso === null ? undefined : 0}
        aria-valuemax={progresso === null ? undefined : 100}
        aria-label={progresso === null ? undefined : "Progresso da avaliação"}
      >
        {progresso !== null && (
          <div
            className="h-full bg-gradient-to-r from-publico-de to-publico-ate transition-[width] duration-300"
            style={{ width: `${seguro}%` }}
          />
        )}
      </div>

      <div className="flex min-h-[calc(100vh-0.25rem)] items-center justify-center px-4 py-10">
        <div className="w-full max-w-lg rounded-2xl bg-card p-8 shadow-sm sm:p-10">{children}</div>
      </div>
    </main>
  );
}

/** Título da etapa. `centralizado` acompanha o oráculo: perguntas centram, o resto não. */
export function TituloDaEtapa({
  children,
  centralizado,
}: {
  children: ReactNode;
  centralizado?: boolean;
}) {
  return (
    <h1
      className={cn(
        "text-xl font-semibold leading-snug text-card-foreground",
        centralizado && "text-center",
      )}
    >
      {children}
    </h1>
  );
}

export function SubtituloDaEtapa({
  children,
  centralizado,
}: {
  children: ReactNode;
  centralizado?: boolean;
}) {
  return (
    <p className={cn("mt-1.5 text-sm text-muted-foreground", centralizado && "text-center")}>
      {children}
    </p>
  );
}

/** Sub-progresso "N de M" dentro do bloco de perguntas. */
export function ContadorDePerguntas({ atual, total }: { atual: number; total: number }) {
  return (
    <div className="mb-5 flex items-center gap-3">
      <span className="shrink-0 text-xs font-semibold text-publico-de">
        {atual} de {total}
      </span>
      <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-publico-de to-publico-ate transition-[width] duration-300"
          style={{ width: `${(atual / total) * 100}%` }}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ botões */

export function BotaoDoWizard({
  children,
  variante = "gradiente",
  tipo = "button",
  onClick,
  desabilitado,
  larguraTotal,
}: {
  children: ReactNode;
  variante?: "gradiente" | "conclusao";
  tipo?: "button" | "submit";
  onClick?: () => void;
  desabilitado?: boolean;
  /** Só a capa usa: lá o botão ocupa a largura do card, como no oráculo. */
  larguraTotal?: boolean;
}) {
  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={desabilitado}
      className={cn(
        "inline-flex h-12 items-center justify-center gap-2 rounded-xl px-7 text-sm font-semibold",
        "text-primary-foreground transition disabled:cursor-not-allowed disabled:opacity-40",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-publico-de",
        "focus-visible:ring-offset-2 enabled:hover:brightness-105",
        larguraTotal && "w-full",
        variante === "conclusao" ? "bg-success" : "bg-gradient-to-r from-publico-de to-publico-ate",
      )}
    >
      {children}
      {variante === "gradiente" && <IconeSeta para="direita" />}
    </button>
  );
}

/**
 * Rodapé da etapa: "Voltar" à esquerda, ação principal à direita.
 *
 * "Voltar" some na primeira etapa em vez de ficar desabilitado — botão morto na tela de
 * boas-vindas só convida a clicar.
 */
export function RodapeDaEtapa({
  aoVoltar,
  children,
}: {
  aoVoltar?: () => void;
  children?: ReactNode;
}) {
  return (
    <div className="mt-8 flex items-center justify-between gap-4">
      {aoVoltar ? (
        <button
          type="button"
          onClick={aoVoltar}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-2 py-2 text-sm text-muted-foreground",
            "transition hover:text-card-foreground focus-visible:outline-none",
            "focus-visible:ring-2 focus-visible:ring-publico-de",
          )}
        >
          <IconeSeta para="esquerda" />
          Voltar
        </button>
      ) : (
        <span />
      )}
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ escolhas */

/** Card da etapa de motivação. Clicar escolhe **e avança** — como no oráculo. */
export function CartaoDeEscolha({
  icone,
  rotulo,
  onClick,
}: {
  icone: ReactNode;
  rotulo: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-card",
        "px-4 py-6 text-sm text-card-foreground transition",
        "hover:border-publico-de hover:bg-muted",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-publico-de",
      )}
    >
      <span className="text-muted-foreground">{icone}</span>
      <span className="text-center leading-tight">{rotulo}</span>
    </button>
  );
}

/** Chip multi-seleção do tipo de serviço. */
export function ChipDeServico({
  marcada,
  children,
  onClick,
}: {
  marcada: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={marcada}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm transition",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-publico-de",
        marcada
          ? "border-publico-de bg-publico-de/10 font-medium text-publico-de"
          : "border-border text-card-foreground hover:bg-muted",
      )}
    >
      {marcada && <IconeCheck className="h-3.5 w-3.5" />}
      {children}
    </button>
  );
}

/**
 * Escala em estrelas, 1 a `maximo` (10 no oráculo).
 *
 * É um `radiogroup` de verdade: quem navega por teclado escolhe a nota com as setas, e
 * o leitor de tela anuncia "8 de 10" em vez de "botão, botão, botão". Clicar na estrela
 * já marcada limpa a nota — é como se desfaz um clique errado sem recarregar a página.
 */
export function Estrelas({
  valor,
  aoEscolher,
  maximo = 10,
  rotulo,
}: {
  valor: number | null;
  aoEscolher: (nota: number | null) => void;
  maximo?: number;
  rotulo: string;
}) {
  const notas = Array.from({ length: maximo }, (_, i) => i + 1);
  return (
    <div className="mt-6">
      <div role="radiogroup" aria-label={rotulo} className="flex justify-center gap-1">
        {notas.map((nota) => {
          const acesa = valor !== null && nota <= valor;
          return (
            <button
              key={nota}
              type="button"
              role="radio"
              aria-checked={valor === nota}
              aria-label={`${nota} de ${maximo}`}
              tabIndex={valor === nota || (valor === null && nota === 1) ? 0 : -1}
              onClick={() => aoEscolher(valor === nota ? null : nota)}
              onKeyDown={(evento) => {
                if (evento.key === "ArrowRight" || evento.key === "ArrowUp") {
                  evento.preventDefault();
                  aoEscolher(Math.min(maximo, (valor ?? 0) + 1));
                }
                if (evento.key === "ArrowLeft" || evento.key === "ArrowDown") {
                  evento.preventDefault();
                  const proxima = (valor ?? 1) - 1;
                  aoEscolher(proxima < 1 ? null : proxima);
                }
              }}
              className={cn(
                "rounded p-0.5 transition focus-visible:outline-none focus-visible:ring-2",
                "focus-visible:ring-publico-de",
                acesa ? "text-success" : "text-border hover:text-muted-foreground",
              )}
            >
              <IconeEstrela className="h-7 w-7" preenchida={acesa} />
            </button>
          );
        })}
      </div>
      {/* A altura fica reservada mesmo sem nota: o card não pula quando o cliente escolhe. */}
      <p className="mt-2 h-5 text-center text-sm font-medium text-success">
        {valor === null ? "" : `${valor}/${maximo}`}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ campos */

const CAMPO_PUBLICO =
  "w-full rounded-lg border border-input bg-card px-4 py-3 text-sm text-card-foreground " +
  "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-publico-de";

export function EntradaPublica(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(CAMPO_PUBLICO, props.className)} />;
}

export function AreaDeTextoPublica(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(CAMPO_PUBLICO, "min-h-28 resize-y", props.className)} />;
}

export function CampoPublico({
  rotulo,
  obrigatorio,
  opcional,
  dica,
  children,
}: {
  rotulo: string;
  obrigatorio?: boolean;
  opcional?: boolean;
  dica?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-card-foreground">
        {rotulo}
        {obrigatorio && <span className="ml-1">*</span>}
        {opcional && <span className="ml-1 font-normal text-muted-foreground">(opcional)</span>}
      </span>
      {children}
      {dica && <span className="mt-1.5 block text-xs text-muted-foreground">{dica}</span>}
    </label>
  );
}
