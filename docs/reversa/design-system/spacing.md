# Espaçamento, Grid e Breakpoints — aesfeedbackinterno

> Gerado pelo Reversa Design System em 2026-08-28
> Fontes: `tailwind.config.ts`, `src/App.css`.
> Escala de confiança: 🟢 config | 🟡 inferido de uso

## Escala de espaçamento 🟡

Não há customização de `spacing` no `tailwind.config.ts` — o projeto usa a escala padrão do Tailwind (base 4px):

| Classe | Valor | Uso típico observado |
|--------|-------|----------------------|
| `p-1` / `gap-1` | 4px | Ícones, badges compactos |
| `p-2` / `gap-2` | 8px | Espaço entre ícone e texto (botões usam `gap-2`) |
| `p-3` / `gap-3` | 12px | Itens de lista |
| `p-4` / `gap-4` | 16px | Padding interno de cards e grids |
| `p-6` | 24px | `CardHeader`/`CardContent` (shadcn) |
| `p-8` / `px-8` | 32px | Botão `lg`, seções |

## Container 🟢

Configurado em `tailwind.config.ts`:

| Propriedade | Valor |
|-------------|-------|
| `center` | `true` (margens automáticas) |
| `padding` | `2rem` (32px) |
| `screens.2xl` | `1400px` (largura máxima do container) |

Adicionalmente, `src/App.css` define `#root { max-width: 1280px; margin: 0 auto; padding: 2rem; text-align: center }` — **resquício do template Vite** que convive com o layout real 🟡 (as páginas usam layouts próprios; `App.css` contém apenas estilos do boilerplate, incluindo `.logo`, `.card`, `.read-the-docs`).

## Breakpoints 🟢/🟡

Sem override de `screens` (exceto o container): valem os padrões do Tailwind.

| Breakpoint | Valor | Origem |
|------------|-------|--------|
| `sm` | 640px | Tailwind default 🟡 |
| `md` | 768px | Tailwind default 🟡 |
| `lg` | 1024px | Tailwind default 🟡 |
| `xl` | 1280px | Tailwind default 🟡 |
| `2xl` | 1536px (utilitárias) / **1400px (container)** | default / `tailwind.config.ts` 🟢 |

## Grid 🟡

Sem sistema de grid formal. Layouts compostos com utilitárias `grid grid-cols-{1..4}` + `md:grid-cols-N` e flexbox, caso a caso por página.
