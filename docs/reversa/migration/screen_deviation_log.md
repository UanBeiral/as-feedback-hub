---
schemaVersion: 1
generatedAt: 2026-08-28T02:10:00Z
reversa:
  version: "1.2.60"
kind: screen_deviation_log
producedBy: screen-translator
hash: "sha256:7427f84fa463cb52e06969d7b3a6082716a44956f52e0c3415791735caa3ae4d"
---

# Screen Deviation Log

> Registro append-only de toda divergência entre o legado e as specs geradas. Deviations pendentes bloqueiam o handoff ao Inspector.

| ID | Tela(s) | Tipo | Descrição | Motivo | Aprovação |
|---|---|---|---|---|---|
| DEV-001 | todas | tecnica | Dados via client OpenAPI gerado em vez de `supabase.from(...)` no componente | BR-DESCARTAR-004; contrato de tela inalterado | aprovado (Uan, 2026-08-28) |
| DEV-002 | SCR-0016, SCR-0017 | plataforma | Exportações pesadas (PDF/XLSX, relatório executivo) viram job assíncrono no worker com link de download; no legado eram geradas no browser (jspdf/xlsx) | AD-07; latência percebida muda (spinner → "seu relatório está sendo gerado") | aprovado (Uan, 2026-08-28) |
| DEV-003 | todas | tecnica | 657 cores hex hardcoded (#1e3a5f, #c9a84c e derivados) substituídas pelos tokens `--primary`/`--accent` e afins; ~270 linhas de overrides `.dark !important` não reproduzidas | BR-DESCARTAR-007; os hex do legado são os mesmos valores dos tokens (paleta preservada) | aprovado (Uan, 2026-08-28) |
| DEV-004 | SCR-0036..0044 (subset modernizado) | modernizacao | 8 telas sem captura ganham os 4 estados declarados (idle/loading/error/success) e layout idiomático do design system | modo híbrido aprovado; sem oráculo visual | aprovado (Uan, 2026-08-28) |
| DEV-005 | shell / rotas | correcao | Rotas duplicadas de coordenador do `App.tsx` não reproduzidas | defeito do legado (BR-DESCARTAR-006) | aprovado (Uan, 2026-08-28) |
| DEV-006 | todas | tecnica | Opacidades sobre hex (`bg-[#1e3a5f]/10` etc.) viram modificadores sobre tokens (`bg-primary/10`) | consequência direta de DEV-003 | aprovado (Uan, 2026-08-28) |
| DEV-007 | SCR-0001, SCR-0038 | plataforma | Autenticação Supabase substituída por auth própria (JWT + refresh); telas idênticas, mecanismo e mensagens de erro do provedor mudam | BR-DESCARTAR-005 / AD-03 | aprovado (Uan, 2026-08-28) |
| DEV-008 | shell, SCR-0035, badges | tecnica | 4 tokens derivados criados em `tokens-derived.md`: `--role-coordinator`, `--role-manager`, `--role-collaborator`, `--public-gradient-from/to` — valores exatos a extrair dos screenshots/código na codificação | cores presentes nas telas sem token no `tokens.md` | aprovado (Uan, 2026-08-28) |

## Notas

- DEV-001/003/006 são transversais e de baixo risco visual: os valores finais renderizados são os mesmos; muda a fonte (token vs literal).
- DEV-002 é a única deviation com mudança de comportamento percebível pelo usuário — recomenda-se demonstrá-la explicitamente na homologação.
- DEV-008 fica totalmente resolvida quando o codificador extrair os valores exatos e preencher `tokens-derived.md`.
