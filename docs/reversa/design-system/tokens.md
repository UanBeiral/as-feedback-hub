# Tabela Consolidada de Tokens — aesfeedbackinterno

> Gerado pelo Reversa Design System em 2026-08-28
> Escala de confiança: 🟢 config | 🟡 inferido | 🔴 referenciado mas não definido

## Cores (variáveis CSS, formato HSL sem `hsl()` — consumidas via `hsl(var(--x))`)

| Token | Claro | Escuro | Confiança |
|-------|-------|--------|-----------|
| `--background` | `210 33% 97%` | `215 28% 10%` | 🟢 |
| `--foreground` | `213 44% 24%` | `210 20% 90%` | 🟢 |
| `--card` | `0 0% 100%` | `215 28% 13%` | 🟢 |
| `--card-foreground` | `213 44% 24%` | `210 20% 90%` | 🟢 |
| `--popover` | `0 0% 100%` | `215 28% 13%` | 🟢 |
| `--popover-foreground` | `213 44% 24%` | `210 20% 90%` | 🟢 |
| `--primary` | `213 52% 24%` | `42 52% 54%` | 🟢 |
| `--primary-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--secondary` | `210 33% 97%` | `215 28% 16%` | 🟢 |
| `--secondary-foreground` | `213 44% 24%` | `210 20% 90%` | 🟢 |
| `--muted` | `210 33% 95%` | `215 28% 18%` | 🟢 |
| `--muted-foreground` | `213 10% 47%` | `210 15% 60%` | 🟢 |
| `--accent` | `42 52% 54%` | `42 52% 54%` | 🟢 |
| `--accent-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--destructive` | `0 84% 60%` | `0 84% 60%` | 🟢 |
| `--destructive-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--border` | `214 20% 88%` | `215 20% 22%` | 🟢 |
| `--input` | `214 20% 88%` | `215 20% 22%` | 🟢 |
| `--ring` | `213 52% 24%` | `42 52% 54%` | 🟢 |
| `--success` | `142 71% 45%` | `142 71% 45%` | 🟢 |
| `--success-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--warning` | `38 92% 50%` | `38 92% 50%` | 🟢 |
| `--warning-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--sidebar-background` | `213 52% 24%` | `215 28% 8%` | 🟢 |
| `--sidebar-foreground` | `0 0% 100%` | `210 20% 90%` | 🟢 |
| `--sidebar-primary` | `42 52% 54%` | `42 52% 54%` | 🟢 |
| `--sidebar-primary-foreground` | `0 0% 100%` | `0 0% 100%` | 🟢 |
| `--sidebar-accent` | `213 52% 30%` | `215 28% 14%` | 🟢 |
| `--sidebar-accent-foreground` | `0 0% 100%` | `210 20% 90%` | 🟢 |
| `--sidebar-border` | `213 52% 30%` | `215 20% 18%` | 🟢 |
| `--sidebar-ring` | `42 52% 54%` | `42 52% 54%` | 🟢 |
| `--sidebar-muted-foreground` | `210 20% 70%` | `210 15% 55%` | 🟢 (definido no CSS, **não mapeado** no `tailwind.config.ts` 🔴) |

## Border-radius 🟢

| Token | Valor | Resultado |
|-------|-------|-----------|
| `--radius` | `0.5rem` | base (8px) |
| `rounded-lg` | `var(--radius)` | 8px — cards, dialogs |
| `rounded-md` | `calc(var(--radius) - 2px)` | 6px — botões, inputs |
| `rounded-sm` | `calc(var(--radius) - 4px)` | 4px — elementos menores |
| `rounded-full` | 9999px (default Tailwind) | badges, avatares, pills 🟡 |

## Sombras 🟡

Sem customização no config — escala padrão do Tailwind (`shadow-sm`, `shadow`, `shadow-lg`, `shadow-2xl`). No dark mode, três níveis são substituídos manualmente em `index.css`:

| Classe | Override dark |
|--------|---------------|
| `shadow-sm` | `0 1px 2px hsl(0 0% 0% / 0.3)` |
| `shadow-lg` | `0 4px 12px hsl(0 0% 0% / 0.4)` |
| `shadow-2xl` | `0 8px 24px hsl(0 0% 0% / 0.5)` |

## Z-index 🟡

Sem escala customizada; componentes shadcn/Radix usam `z-50` para overlays (dialog, popover, dropdown, toast) — padrão da biblioteca.

## Animações e transições 🟢

| Token | Valor | Origem |
|-------|-------|--------|
| `accordion-down` | `height 0 → var(--radix-accordion-content-height)`, `0.2s ease-out` | `tailwind.config.ts` |
| `accordion-up` | inverso, `0.2s ease-out` | `tailwind.config.ts` |
| Plugin | `tailwindcss-animate` (fade/zoom/slide dos componentes shadcn) | `tailwind.config.ts` |
| Transição padrão | `transition-colors` em botões/badges | shadcn/ui 🟡 |
| `.logo` (boilerplate) | `transition: filter 300ms` + `logo-spin 20s linear` | `App.css` (resquício Vite, sem uso real) 🟡 |

## Dark mode 🟢

- Estratégia: `darkMode: ["class"]` — classe `.dark` no elemento raiz.
- Complemento: ~270 linhas de overrides `.dark ... !important` em `src/index.css` para neutralizar cores hardcoded (ver `color-palette.md`).

## Opacidades semânticas 🟡

Sem tokens dedicados; uso recorrente de modificadores de opacidade do Tailwind sobre as cores da marca: `/5`, `/10`, `/15`, `/20`, `/30`, `/50`, `/80`, `/90` (ex.: `bg-[#1e3a5f]/10`, `bg-[#c9a84c]/20`, `hover:bg-primary/90`).
