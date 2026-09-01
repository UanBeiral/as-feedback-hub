# Design System — aesfeedbackinterno (documento consolidado)

> Gerado pelo Reversa Design System em 2026-08-28
> Escala de confiança: 🟢 config | 🟡 inferido | 🔴 lacuna

## Visão geral

Stack de UI: **React + Tailwind CSS + shadcn/ui (Radix UI)**, estilo `default`, base color `slate`, com variáveis CSS habilitadas (`components.json` 🟢). Tema claro/escuro por classe (`darkMode: ["class"]`). Fonte única: **Inter** (300–700, Google Fonts).

Identidade visual: **navy `#1e3a5f`** (primária) + **gold `#c9a84c`** (destaque) — no dark mode a primária inverte para o gold. Sidebar sempre navy no claro, com item ativo em gold.

Documentos detalhados:
- [color-palette.md](color-palette.md) — paleta completa claro/escuro + cores hardcoded
- [typography.md](typography.md) — Inter, pesos, escala e hierarquia
- [spacing.md](spacing.md) — espaçamento, container, breakpoints
- [tokens.md](tokens.md) — tabela consolidada de todos os tokens

## Arquitetura de estilos

```
src/index.css          → variáveis CSS (:root / .dark) + ~270 linhas de overrides dark
tailwind.config.ts     → mapeamento tokens → classes, fonte, radius, animações
components.json        → configuração shadcn/ui (style default, baseColor slate)
src/components/ui/     → 48 primitivas shadcn/ui (cva + tailwind-merge)
src/components/        → 34 componentes de negócio
src/App.css            → resquício do template Vite (sem uso real nas páginas) 🟡
```

Utilitário de composição: `cn()` em `src/lib/utils.ts` (clsx + tailwind-merge) 🟢.

## Biblioteca de componentes

### Primitivas shadcn/ui (48) 🟢

accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toast, toaster, toggle-group, toggle, tooltip.

**Variantes principais (cva):**

| Componente | Variantes | Tamanhos |
|------------|-----------|----------|
| `Button` | default, destructive, outline, secondary, ghost, link | default (h-10), sm (h-9), lg (h-11), icon (10×10) |
| `Badge` | default, secondary, destructive, outline | único (pill, `text-xs font-semibold`) |

### Componentes de negócio (34) 🟢

Modais: AddMemberModal, CancelFeedbackModal, ClientFeedbackAnswersModal, ContactUsModal, FeedbackAnswersModal, FreeFeedbackModal, RemoveMemberModal, RequestClientFeedbackModal, RoleSelectionModal.
Ciclos: CycleClosedBanner, CycleDeadlineBanner, CycleComparison, CycleInfoPopover, CycleNoteDrawer, GlobalCycleNotes.
Feedback: ClientFeedbackDashboard, FreeFeedbackCard, FreeFeedbackList, SensitiveFeedbackAlert, StarRating10, TeamRequestsSection, UnreadFeedbackBanner, ReminderButton.
Infra de UI: CompanyLogo, DynamicFavicon, EmptyState, LoadingState, StatsCard, NavLink, ColumnTooltip, GlobalSearch, GuidedTour, NotificationCenter, ProtectedRoute.

### Branding dinâmico 🟢

`CompanyLogo` + `DynamicFavicon` consomem `logo_url` de `company_settings` (via `useCompanySettings`) — o logo é configurável por empresa, mas **as cores não são** (navy/gold fixos no código).

## Resumo de tokens por categoria

| Categoria | Quantidade | Confiança predominante |
|-----------|------------|------------------------|
| Cores semânticas (claro + escuro) | 23 pares + 9 de sidebar | 🟢 |
| Cores hardcoded fora do sistema | ~10 hex recorrentes, 657 ocorrências em 65 arquivos | 🟡 |
| Tipografia | 1 família, 5 pesos, escala default | 🟢 |
| Espaçamento | escala default Tailwind, container 1400px | 🟢/🟡 |
| Border-radius | 1 token base (`--radius: 0.5rem`) + 3 derivados | 🟢 |
| Sombras | default + 3 overrides dark | 🟡 |
| Animações | 2 keyframes + plugin tailwindcss-animate | 🟢 |
| Breakpoints | defaults Tailwind (container 2xl = 1400px) | 🟢/🟡 |

## Achados e recomendações

1. **🔴 Dívida principal — cores hardcoded:** 657 usos de hex arbitrários (`#1e3a5f`, `#c9a84c` etc.) duplicam os tokens `--primary`/`--accent`. O dark mode só funciona graças a ~270 linhas de overrides `!important` em `index.css`, incluindo seletores genéricos perigosos (`.dark .border`, `.dark .rounded-full`, `.dark [class*="bg-gradient-to"]`). Recomendação: migrar gradualmente `text-[#1e3a5f]` → `text-primary` (claro) e remover os overrides correspondentes.
2. **🔴 Token órfão:** `--sidebar-muted-foreground` é definido no CSS mas não mapeado no `tailwind.config.ts` — inutilizável como classe Tailwind.
3. **🟡 Resquício de boilerplate:** `src/App.css` mantém estilos do template Vite (`#root` com `max-width: 1280px` e `text-align: center`, `.logo` animado) que não refletem o layout real.
4. **🟡 Sem escala tipográfica própria:** hierarquia composta ad hoc; um componente `PageTitle`/`SectionTitle` eliminaria a repetição de `text-2xl font-bold text-[#1e3a5f]`.
5. **🟢 Base sólida:** o conjunto shadcn/ui + tokens HSL está corretamente configurado; o problema é de adesão, não de fundação.
