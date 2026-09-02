# Tokens Derivados — Screen Translator (Time de Migração)

> Criado pelo Screen Translator em 2026-08-28 (DEV-008 em `_reversa_sdd/migration/screen_deviation_log.md`).
> Append-only. Tokens presentes nas telas do legado sem correspondente em `tokens.md`. Valores exatos a extrair dos screenshots/código durante a codificação.

| Token derivado | Uso observado | Valor | Origem |
|---|---|---|---|
| `--role-coordinator` | badge de papel "Coordenador" (roxo) | 🔴 extrair | `ui/inventory.md` § Padrões transversais |
| `--role-manager` | badge de papel "Gestor" (dourado — provável = `--accent`) | 🔴 confirmar se ≡ `--accent` | idem |
| `--role-collaborator` | badge "Colaborador" (cinza claro — provável = `--muted`) | 🔴 confirmar se ≡ `--muted` | idem |
| `--public-gradient-from` | início do gradiente roxo do fluxo público | 🟢 `239 84% 67%` (#6366f1) | amostragem de pixel em `public/screenshots/` |
| `--public-gradient-to` | fim do gradiente roxo do fluxo público | 🟢 `258 90% 66%` (#8b5cf6) | idem |
| `--public-surface` | fundo da página pública (mais claro que `--background`) | 🟢 `220 27% 98%` (#f8f9fb) | idem |

## Como os valores do fluxo público saíram

Medidos no oráculo, não escolhidos: o botão "Começar avaliação" de
`avaliacao-boas-vindas.png` tem #6366f1 na borda esquerda e #8b5cf6 na direita, e a barra
de progresso do topo usa o mesmo par. São, respectivamente, `indigo-500` e `violet-500` da
paleta do Tailwind — o legado era um projeto Lovable, e as classes utilitárias explicam a
coincidência.

O verde das estrelas e do botão de envio é #22c55e, que já é exatamente o `--success` de
`tokens.md`: não virou token novo.

Fica aberto o `--role-coordinator`: o roxo do badge de papel está em telas do app interno,
que ainda não foram conferidas contra o oráculo. O valor de hoje é chute e está marcado
como tal em `tokens.css`.
