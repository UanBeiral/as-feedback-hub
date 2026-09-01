---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: data_migration_plan
producedBy: designer
hash: "sha256:091014b9224467fb8d7fc0ac0b1a3e8ed71c998ab4be822013dcdb03c8db49e6"
---

# Data Migration Plan

> Migração de dados Supabase (single-tenant) → PostgreSQL próprio (multi-tenant), estratégia Big Bang com janela congelada (sem captura de delta — ver `cutover_plan.md`).

## Princípios

1. **Fonte da verdade do schema legado é o banco de produção**, não as migrations versionadas (12 de 28 tabelas sem DDL no repo — R-01). Passo zero: `pg_dump --schema-only` do Supabase.
2. **Idempotência**: todo script usa UPSERT por id legado; re-execução é segura (ensaios repetidos — pré-requisito 2 do cutover).
3. **Tenant único no corte**: toda a base migra para o tenant do cliente atual (`tenants` seed) — elimina ambiguidade de atribuição (R-09).
4. **IDs preservados**: UUIDs do legado mantidos nas tabelas novas para rastreabilidade e simplicidade de FK.

## Mapeamento legado → novo (com transformações)

| Origem (Supabase) | Destino | Transformações |
|---|---|---|
| `auth.users` | `users` | export de hashes bcrypt (R-07); `email` normalizado lowercase; usuários sem perfil → relatório de órfãos (decisão manual); `tenant_id` = tenant seed |
| `profiles` | `profiles` | flags booleanas NULL → false (deny-by-default, BR-MIGRAR-013); `user_id` = id (1:1); status preservado incl. `deleted` |
| `departments`, `profile_departments` | idem | direto + `tenant_id` |
| `coordinator_members`, `team_requests` | idem | linhas com uuid órfão (sem FK física no legado) → quarentena em tabela `_migration_rejects` com motivo |
| `feedback_forms`, `feedback_form_questions` | idem | direto; `sort_order` NULL → posição por created_at |
| `feedback_cycles` | `feedback_cycles` | status do legado documentado como `open|closed` no DDL mas telas operam draft/published/archived — mapear valores reais encontrados; 🟡 valores fora do CHECK novo → quarentena |
| `feedback_permissions` | idem | `active` NULL → false; pares duplicados → dedupe mantendo o mais recente |
| `feedback_requests` | `feedback_requests` | **`status='reviewed'` → `submitted`** (AMB-003), registrando os ids afetados em `_migration_notes`; `response_data` jsonb reconciliado com `feedback_answers` (ver regra abaixo) |
| `feedback_answers` | `feedback_answers` | linhas órfãs (request/question inexistente) → quarentena; se request tem `response_data` sem linhas em answers, explodir o jsonb em linhas de `feedback_answers` 🟡 |
| `free_feedbacks` | idem | anônimos: garantir `giver_id` NULL (anonimização por design — AMB-001) |
| `cycle_notes` | idem | direto |
| `client_feedback_forms/_questions` | `client_eval_forms/_form_questions` | renomeação de tabela; `display_order` preservado |
| `client_feedbacks` | `client_evaluations` | renomeação; tokens já usados permanecem com status/`submitted_at`; `token_expires_at` no passado + status pending → `expired` (normalização) |
| `client_feedback_answers` | `client_eval_answers` | renomeação; órfãs → quarentena |
| `client_feedback_service_tags`, `client_feedback_tags` | `service_tags`, `client_evaluation_tags` | renomeação |
| `notifications` | `notifications` | `read_at` preservado (BR-MIGRAR-023); tipo NULL → 'general' |
| `audit_logs` | `audit_logs` | `user_id` → `actor_id` (BR-MIGRAR-026); referências a auth.users deletados → NULL |
| `company_settings` | `tenant_settings` | 8 chaves do catálogo; `updated_by` NULL → id do admin do tenant (backfill documentado) |
| `platform_updates`, `feedback_contacts` | `platform_updates`, `contact_messages` | renomeação; status de contacts validado contra `novo|em_andamento|resolvido` |
| `feedback_ai_analysis`, `feedback_ai_cycle_analysis` | (não migram) | caches regeneráveis — arquivados no export final (AMB-005) |
| `daily_appointments` | (arquivada) | fase 2 (AMB-007); dados preservados no export |
| `google_calendar_tokens` | (não migra) | tokens OAuth não devem trocar de custódia; reconexão na fase 2 |
| Storage `company-assets` | disco VPS `/data/assets/<tenant>/` | download via API do Supabase; caminhos atualizados em `tenant_settings` (logo) |

## Estratégia de ETL

- **Ferramenta**: scripts Python no repositório novo (`deploy/migrate/`), usando `psycopg` contra os dois bancos; sem ferramenta externa (volume pequeno: 1 escritório, protótipo).
- **Fluxo**: `extract` (dump/cópia read-only) → `transform+load` por tabela na ordem de dependência (tenants → users → profiles → departments → ... → answers) → `validate`.
- **Idempotência**: `INSERT ... ON CONFLICT (id) DO UPDATE`; execução completa re-executável.
- **Throughput**: volume estimado é baixo (uma empresa); execução única em minutos — sem particionamento.
- **Quarentena**: `_migration_rejects` (linha original em jsonb + motivo) e `_migration_notes` (normalizações aplicadas, ex.: reviewed→submitted); ambas revisadas antes do go.

## Backfill e captura de delta

- **Delta**: não há — o cutover congela o legado em somente-leitura antes do dump final (ver `cutover_plan.md` § Janela); a migração roda sobre base estática.
- **Backfills novos**: `tenant_id` (tenant seed em tudo), `tenant_settings.updated_by`, flags NULL→false, normalizações de status. Todos registrados em `_migration_notes`.

## Cutover de dados (sequência resumida)

1. Congelar legado (somente-leitura) → 2. Dump final (schema real + dados + storage) → 3. Rodar ETL ensaiado → 4. Validação (abaixo) → 5. Revisar quarentena/notas → 6. Liberar API.

Pré-requisitos já cobertos no `cutover_plan.md`: inventário `pg_cron` (AMB-008) e credenciais (AMB-009/R-07).

## Validação de qualidade

| Verificação | Critério de aceite |
|---|---|
| Contagem por tabela | destino = origem − quarentena (quarentena justificada linha a linha) |
| Checksums | soma de colunas-chave (ex.: count por status de requests, soma de ratings) idêntica origem/destino |
| Integridade referencial | zero FK inválida (garantido por constraints novas; quarentena absorve órfãos) |
| Máquinas de estado | nenhum status fora dos CHECKs novos; contagem de normalizações reportada |
| Autenticação | amostra de logins reais com hash migrado (staging) |
| Multi-tenant | 100% das linhas com `tenant_id` do tenant seed |

## Lacunas explícitas (🔴 validar na codificação)

- Schema real das 12 tabelas sem DDL versionado — o mapeamento acima usa a estrutura inferida pelo Data Master; o `pg_dump` de produção pode revelar colunas extras (R-01).
- Semântica exata de `feedback_requests.response_data` vs `feedback_answers` — a regra de reconciliação (explodir jsonb quando answers ausente) precisa ser confirmada contra dados reais.
- Valores reais de `feedback_cycles.status` em produção (DDL diz `open|closed`, telas operam 5 estados).
- Formato de export dos hashes do Supabase Auth (bcrypt esperado; verificar cedo — R-07).
