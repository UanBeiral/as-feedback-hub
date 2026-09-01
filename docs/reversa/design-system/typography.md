# Tipografia — aesfeedbackinterno

> Gerado pelo Reversa Design System em 2026-08-28
> Fontes: `src/index.css` (import Google Fonts), `tailwind.config.ts` (fontFamily).
> Escala de confiança: 🟢 config | 🟡 inferido de uso | 🔴 não definido

## Família de fonte 🟢

| Token | Valor | Origem |
|-------|-------|--------|
| `font-sans` | `'Inter', sans-serif` | `tailwind.config.ts` → `theme.extend.fontFamily.sans` |

- Carregada via Google Fonts em `src/index.css` linha 1: `Inter:wght@300;400;500;600;700`
- Aplicada globalmente: `body { @apply font-sans; font-family: 'Inter', sans-serif; }`
- Fallback: apenas `sans-serif` genérico (sem stack detalhado como `-apple-system`, `Segoe UI`) 🟢
- Nenhuma fonte serifada ou monoespaçada customizada declarada; `font-mono` cai no default do Tailwind 🟡

## Pesos disponíveis 🟢

| Peso | Nome | Carregado |
|------|------|-----------|
| 300 | Light | ✅ |
| 400 | Regular | ✅ |
| 500 | Medium | ✅ |
| 600 | SemiBold | ✅ |
| 700 | Bold | ✅ |

Pesos 100, 200, 800, 900 **não** são carregados — classes como `font-extrabold`/`font-black` renderizariam com síntese do browser 🟢.

## Escala de tamanhos 🟡

O projeto **não customiza** a escala tipográfica: usa a escala padrão do Tailwind CSS.

| Classe | Tamanho | Line-height | Uso observado no projeto |
|--------|---------|-------------|--------------------------|
| `text-xs` | 12px / 0.75rem | 16px | Badges, labels, metadados |
| `text-sm` | 14px / 0.875rem | 20px | Corpo padrão (botões, inputs, tabelas) |
| `text-base` | 16px / 1rem | 24px | Corpo de texto |
| `text-lg` | 18px / 1.125rem | 28px | Subtítulos de card |
| `text-xl` | 20px / 1.25rem | 28px | Títulos de seção |
| `text-2xl` | 24px / 1.5rem | 32px | Títulos de página, valores de StatsCard |
| `text-3xl` | 30px / 1.875rem | 36px | Números de destaque em dashboards |

## Hierarquia 🟡

Não há tags `h1–h6` estilizadas globalmente nem componente `Typography` dedicado. A hierarquia é composta ad hoc por combinação de utilitárias, padrão inferido dos componentes:

| Nível | Composição típica |
|-------|-------------------|
| Título de página | `text-2xl font-bold text-[#1e3a5f]` (navy hardcoded) |
| Título de card | `CardTitle` (shadcn) — `text-2xl font-semibold leading-none tracking-tight` |
| Descrição de card | `CardDescription` — `text-sm text-muted-foreground` |
| Corpo | `text-sm` / `text-base text-foreground` |
| Metadado / caption | `text-xs text-muted-foreground` |
| Label de form | `Label` (shadcn) — `text-sm font-medium leading-none` |

## Letter-spacing e line-height 🟡

Sem customização: valores padrão do Tailwind. `tracking-tight` aparece nos títulos de card via shadcn/ui.
