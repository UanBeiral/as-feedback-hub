# Paleta de Cores — aesfeedbackinterno

> Gerado pelo Reversa Design System em 2026-08-28
> Fontes: `src/index.css` (variáveis CSS HSL), `tailwind.config.ts`, varredura de classes arbitrárias nos componentes.
> Escala de confiança: 🟢 extraído de arquivo de configuração | 🟡 inferido de uso | 🔴 referenciado mas não definido

## Identidade da marca

O sistema tem duas cores de marca, usadas em toda a interface:

| Papel | Cor | HSL | Hex aprox. | Confiança |
|-------|-----|-----|------------|-----------|
| **Navy (primária)** | Azul-marinho institucional | `213 52% 24%` | `#1e3a5f` | 🟢 |
| **Gold (destaque)** | Dourado | `42 52% 54%` | `#c9a84c` | 🟢 |

No **modo claro**, primary = navy e accent = gold. No **modo escuro**, primary passa a ser o **gold** (`42 52% 54%`) — inversão intencional para contraste.

## Tokens semânticos — modo claro (`:root`) 🟢

| Token | HSL | Hex aprox. | Uso |
|-------|-----|------------|-----|
| `--background` | `210 33% 97%` | `#f4f6f9` | Fundo geral da aplicação |
| `--foreground` | `213 44% 24%` | `#223a58` | Texto principal |
| `--card` | `0 0% 100%` | `#ffffff` | Fundo de cards |
| `--card-foreground` | `213 44% 24%` | `#223a58` | Texto em cards |
| `--popover` | `0 0% 100%` | `#ffffff` | Fundo de popovers |
| `--popover-foreground` | `213 44% 24%` | `#223a58` | Texto em popovers |
| `--primary` | `213 52% 24%` | `#1e3a5f` | Botões primários, links, ênfase |
| `--primary-foreground` | `0 0% 100%` | `#ffffff` | Texto sobre primary |
| `--secondary` | `210 33% 97%` | `#f4f6f9` | Botões secundários |
| `--secondary-foreground` | `213 44% 24%` | `#223a58` | Texto sobre secondary |
| `--muted` | `210 33% 95%` | `#eef1f6` | Fundos atenuados |
| `--muted-foreground` | `213 10% 47%` | `#6c7684` | Texto secundário |
| `--accent` | `42 52% 54%` | `#c9a84c` | Destaques dourados |
| `--accent-foreground` | `0 0% 100%` | `#ffffff` | Texto sobre accent |
| `--destructive` | `0 84% 60%` | `#ef4444` | Ações destrutivas, erros |
| `--destructive-foreground` | `0 0% 100%` | `#ffffff` | Texto sobre destructive |
| `--border` | `214 20% 88%` | `#dae0e6` | Bordas |
| `--input` | `214 20% 88%` | `#dae0e6` | Bordas de inputs |
| `--ring` | `213 52% 24%` | `#1e3a5f` | Anel de foco |
| `--success` | `142 71% 45%` | `#22c55e` | Sucesso |
| `--success-foreground` | `0 0% 100%` | `#ffffff` | Texto sobre success |
| `--warning` | `38 92% 50%` | `#f59e0b` | Alerta |
| `--warning-foreground` | `0 0% 100%` | `#ffffff` | Texto sobre warning |

### Sidebar (grupo próprio de tokens) 🟢

| Token | HSL claro | Hex aprox. | Observação |
|-------|-----------|------------|------------|
| `--sidebar-background` | `213 52% 24%` | `#1e3a5f` | Sidebar é sempre navy no claro |
| `--sidebar-foreground` | `0 0% 100%` | `#ffffff` | |
| `--sidebar-primary` | `42 52% 54%` | `#c9a84c` | Item ativo em gold |
| `--sidebar-primary-foreground` | `0 0% 100%` | `#ffffff` | |
| `--sidebar-accent` | `213 52% 30%` | `#254a77` | Hover de itens |
| `--sidebar-accent-foreground` | `0 0% 100%` | `#ffffff` | |
| `--sidebar-border` | `213 52% 30%` | `#254a77` | |
| `--sidebar-ring` | `42 52% 54%` | `#c9a84c` | |
| `--sidebar-muted-foreground` | `210 20% 70%` | `#a3b2c2` | Não mapeado no tailwind.config 🟡 |

## Tokens semânticos — modo escuro (`.dark`) 🟢

| Token | HSL escuro | Hex aprox. | Mudança relevante |
|-------|------------|------------|-------------------|
| `--background` | `215 28% 10%` | `#121821` | |
| `--foreground` | `210 20% 90%` | `#e0e6eb` | |
| `--card` / `--popover` | `215 28% 13%` | `#181f2a` | |
| `--primary` | `42 52% 54%` | `#c9a84c` | **Navy → Gold** |
| `--secondary` | `215 28% 16%` | `#1d2634` | |
| `--muted` | `215 28% 18%` | `#212b3b` | |
| `--muted-foreground` | `210 15% 60%` | `#8a98a8` | |
| `--accent` | `42 52% 54%` | `#c9a84c` | |
| `--destructive` | `0 84% 60%` | `#ef4444` | inalterado |
| `--border` / `--input` | `215 20% 22%` | `#2d3543` | |
| `--ring` | `42 52% 54%` | `#c9a84c` | Navy → Gold |
| `--sidebar-background` | `215 28% 8%` | `#0e131a` | |
| `--success` / `--warning` | inalterados | | |

## Cores hardcoded fora dos tokens 🟡

A varredura encontrou **657 ocorrências em 65 arquivos** de cores em classes arbitrárias do Tailwind, contornando o sistema de tokens:

| Hex | Papel observado | Onde aparece |
|-----|-----------------|--------------|
| `#1e3a5f` | Navy da marca (duplica `--primary`) | Dashboards, formulários, headers — uso massivo |
| `#c9a84c` | Gold da marca (duplica `--accent`) | Badges, banners, destaques |
| `#2d5491` | Navy claro (gradientes `from-[#1e3a5f] to-[#2d5491]`) | Cards de notificação |
| `#b8963e` | Gold escuro (gradientes) | Cards de notificação |
| `#7c3aed` | Violeta (badges de papel/categoria) | Histórico, badges |
| `#6366f1` | Indigo (badges) | Cards de feedback |
| `#f4f6f9` | Fundo claro (duplica `--background`) | Cards de feedback |
| `#fffbeb` / `#fef3c7` / `#fde68a` | Amarelos (cards de feedback de cliente) | Fluxo público/cliente |
| `#92400e` / `#dc2626` | Âmbar escuro / vermelho (texto) | Alertas |

Além disso, escalas padrão do Tailwind são usadas diretamente como cores de status/pós-it: `amber`, `blue`, `green`, `rose`, `violet`, `orange`, `red`, `emerald`, `indigo`, `purple`, `yellow`, `slate`, `gray` (variações 50–800).

### Consequência estrutural

O modo escuro depende de **~270 linhas de overrides `.dark` com `!important`** em `src/index.css` (linhas 90–361) para reverter cada cor hardcoded classe a classe — inclusive regras genéricas agressivas como `.dark .border { ... }`, `.dark .rounded-full { ... }` e `.dark [class*="bg-gradient-to"] { background-image: none }`. Isso é dívida de design tokens: qualquer cor nova hardcoded exige um novo override manual para o dark mode. Registrado como recomendação em `design-system.md`.

## Cores de pós-it (anotações) 🟡

Inferido dos overrides dark e do uso em `CycleNoteDrawer`/`MinhasAnotacoes`: as anotações usam 6 variantes de pós-it via classes Tailwind `bg-{amber|blue|green|rose|violet|orange}-50` com bordas `-200` correspondentes.
