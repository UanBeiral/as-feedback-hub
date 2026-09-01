---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: discard_log
producedBy: curator
hash: "sha256:68d6bf7ff2213064a9786bf2251160989e9795f590f2f04c342532e769499072"
---

# Discard Log

> Registro completo do que foi descartado da migração e por quê. Cada item tem rastreabilidade para a origem no legado.
> Importante: nenhum item abaixo descarta uma **regra de negócio** — são mecanismos, dependências de plataforma ou defeitos do protótipo. As regras que eles serviam migram com novo mecanismo (ver `target_business_rules.md`).

## Itens descartados

### BR-DESCARTAR-001
- **Origem**: `_reversa_sdd/domain.md` § Regras (🟡 RLS); `_reversa_sdd/permissions.md` § Validação humana; `_reversa_sdd/gaps.md` § Críticas
- **Descrição**: Row Level Security (RLS) do Supabase como mecanismo de autorização de dados, complementado por flags de UI e redirecionamento de componente.
- **Justificativa**: o paradigma alvo centraliza autorização na camada de aplicação (dependencies FastAPI); manter RLS como mecanismo primário perpetuaria a autorização invisível e não testável que o `confidence-report` apontou como nunca comprovada.
- **Vinculado a paradigma**: sim
  - Procedural client-centric (cliente fala direto com o banco, banco autoriza) → OO com DI (API autoriza explicitamente antes de tocar o banco). A camada de autorização com escopo de `tenant_id` + papel + flags absorve o caso por construção.
- **Reposição no sistema novo**: guards/dependencies de autorização na API, especificados a partir da matriz de `permissions.md`. Postgres RLS *pode* ser mantido como defesa em profundidade opcional, a critério do Designer, mas nunca como mecanismo primário.
- **Risco de descartar**: baixo — a regra de negócio (negar por padrão, escopos por papel) migra integralmente em BR-MIGRAR-013/014/015/017.

### BR-DESCARTAR-002
- **Origem**: `_reversa_sdd/domain.md` § Decisões e sinais do histórico; commits recentes (`fix: remover EdgeRuntime.waitUntil`, `waitUntil no envio em background`)
- **Descrição**: Edge Functions Deno com `waitUntil`/Promise pendente para envio de notificações em background.
- **Justificativa**: mecanismo frágil (o histórico registra dois fixes de incompatibilidade com Deno Deploy) que existia porque a plataforma serverless não oferece processos residentes.
- **Vinculado a paradigma**: sim
  - Serverless event-driven improvisado → fila Redis + worker residente. Enfileirar job após commit substitui o `waitUntil` por construção, com retry e observabilidade que o mecanismo antigo não tinha.
- **Reposição no sistema novo**: jobs na fila Redis consumidos por workers (BR-MIGRAR-024/025).
- **Risco de descartar**: baixo.

### BR-DESCARTAR-003
- **Origem**: checkpoint Data Master (`.reversa/state.json`): "jobs pg_cron não versionados"; `_reversa_sdd/database/procedures.md`
- **Descrição**: Jobs agendados via `pg_cron`/`pg_net` no banco (fechamento automático de ciclo e afins), não versionados no repositório.
- **Justificativa**: agendamento dentro do banco era o único mecanismo disponível no Supabase; no alvo, o scheduling pertence à camada de aplicação.
- **Vinculado a paradigma**: sim
  - Cron no banco → scheduler do worker (beat/cron do framework de fila). A regra de negócio servida (fechamento com carência de 3 dias) migra em BR-MIGRAR-005; muda apenas o executor.
- **Reposição no sistema novo**: jobs agendados no worker, versionados em código.
- **Risco de descartar**: médio — os jobs de produção não estão versionados, então o inventário completo do que o pg_cron faz hoje é 🔴 LACUNA. O Strategist deve prever extração desse inventário do banco de produção antes do cutover.

### BR-DESCARTAR-004
- **Origem**: `_reversa_sdd/inventory.md` ("uso massivo de `supabase.from(...)` no frontend"); `_reversa_sdd/architecture.md` § Riscos; `_reversa_sdd/public/requirements.md` § Validação humana (anon key)
- **Descrição**: Acesso direto do cliente ao banco via Supabase JS (incluindo anon key no fluxo público) e o acoplamento da UI ao schema.
- **Justificativa**: é o padrão estrutural central do protótipo e a causa raiz da lógica espalhada; incompatível com multi-tenancy segura.
- **Vinculado a paradigma**: sim
  - Client-centric → API-centric: contrato OpenAPI absorve todos os casos; o front nunca conhece o schema do banco.
- **Reposição no sistema novo**: API FastAPI com Pydantic schemas + repositories (BR-MIGRAR transversal).
- **Risco de descartar**: baixo.

### BR-DESCARTAR-005
- **Origem**: `_reversa_sdd/auth/requirements.md` (sessão Supabase); `_reversa_sdd/database/` (google_calendar_tokens, storage bucket `company-assets`)
- **Descrição**: Supabase Auth como provedor de identidade e Supabase Storage como armazenamento de assets.
- **Justificativa**: o brief exige infraestrutura própria em VPS (Postgres próprio, sem Supabase gerenciado).
- **Vinculado a paradigma**: não — restrição declarada no `migration_brief.md` § Restrições técnicas.
- **Reposição no sistema novo**: solução de auth própria (a definir pelo Designer: FastAPI + JWT/refresh, ou IdP self-hosted) preservando BR-MIGRAR-016/018; storage local/S3-compatible na VPS para assets (logo etc.).
- **Risco de descartar**: médio — migração de credenciais dos usuários existentes (hashes de senha do Supabase Auth) precisa constar do plano de migração de dados do Designer/Strategist.

### BR-DESCARTAR-006
- **Origem**: `_reversa_sdd/architecture.md` § Riscos e dívidas ("rotas duplicadas para coordenador no App.tsx, sinal de manutenção incompleta")
- **Descrição**: Rotas duplicadas de coordenador no roteamento central.
- **Justificativa**: defeito/resíduo de manutenção do protótipo, sem valor de negócio.
- **Vinculado a paradigma**: não — defeito.
- **Reposição no sistema novo**: none (o roteamento novo do Next.js nasce limpo).
- **Risco de descartar**: baixo.

### BR-DESCARTAR-007
- **Origem**: checkpoint Design System (`.reversa/state.json`): 657 cores hex hardcoded em 65 arquivos; ~270 linhas de overrides `.dark !important`; `--sidebar-muted-foreground` órfão; `src/App.css` residual
- **Descrição**: Dívidas do design system do protótipo: cores hardcoded contornando tokens e a cascata de overrides compensatórios.
- **Justificativa**: dívida visual sem valor; os **tokens semânticos** extraídos (32 tokens claro/escuro, Inter 300–700, radius 0.5rem, catálogo em `_reversa_sdd/design-system/`) migram — as violações deles, não.
- **Vinculado a paradigma**: não — dívida de implementação.
- **Reposição no sistema novo**: design system tokenizado desde o início no Next.js (insumo direto para o Screen Translator).
- **Risco de descartar**: baixo.

## Itens descartados por mudança de paradigma (subseção dedicada)

> Lista apenas dos itens cujo `Vinculado a paradigma = sim`. Auditoria explícita para o agente de codificação.

| ID | Origem | Paradigma legado | Substituto no paradigma alvo |
|---|---|---|---|
| BR-DESCARTAR-001 | RLS + flags de UI | banco autoriza o cliente | camada de autorização na API (guards com tenant + papel + flags) |
| BR-DESCARTAR-002 | Edge Functions `waitUntil` | serverless com background improvisado | fila Redis + worker (retry, DLQ, observabilidade) |
| BR-DESCARTAR-003 | jobs `pg_cron` no banco | cron dentro do banco | scheduler do worker, versionado em código |
| BR-DESCARTAR-004 | `supabase.from(...)` no cliente | cliente acoplado ao schema | contrato OpenAPI + repositories |

## Notas
- Dois descartes carregam risco médio com ação pendente: **BR-DESCARTAR-003** (inventariar jobs pg_cron de produção antes do cutover) e **BR-DESCARTAR-005** (plano de migração de credenciais do Supabase Auth). Ambos referidos ao Strategist/Designer.
