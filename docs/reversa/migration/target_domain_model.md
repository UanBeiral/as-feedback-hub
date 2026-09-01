---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: target_domain_model
producedBy: designer
hash: "sha256:1ed33344c443c5e4f8cc480c53ce055e60d904fae237beb7427a1e210693f234"
---

# Target Domain Model

> Modelo de domínio do sistema novo, organizado pelos 5 bounded contexts de `target_architecture.md`.
> Paradigma: OO com DI; eventos internos são registros de outbox (não event-driven pleno), conforme `paradigm_decision.md`.

## Contexto `identity`

### Aggregate: Tenant
- **Root**: `Tenant`
- **Invariantes**: slug único; um tenant ativo possui ≥1 usuário admin.
- **Comandos**: `create_tenant`, `deactivate_tenant`.
- **Entidades/VOs**: `TenantSettingsRef` (ponteiro para engagement).

### Aggregate: UserAccount
- **Root**: `UserAccount` (credenciais + sessão)
- **Invariantes**: email único por tenant; usuário `deleted`/`inactive` não emite sessão (BR-MIGRAR-016/018); refresh token rotativo de uso único.
- **Comandos**: `register`, `authenticate`, `refresh_session`, `revoke_sessions`, `reset_password`.

### Aggregate: Profile
- **Root**: `Profile`
- **Invariantes**: papel ∈ {admin, rh, gestor, colaborador}; `is_coordinator` e flags de capacidade são atributos, não papéis (BR-MIGRAR-015); soft-delete preserva histórico e revoga sessões (BR-MIGRAR-018); negar por padrão em toda resolução de capacidade (BR-MIGRAR-013).
- **Comandos**: `update_profile`, `change_role`, `set_flags`, `soft_delete`, `assign_manager`, `set_departments`.
- **Entidades/VOs**: `CapabilityFlags` (VO imutável), `ActiveRole` (VO de contexto de sessão — BR-MIGRAR-016).

### Aggregate: TeamScope
- **Root**: `TeamScope` (serviço de resolução de escopo, sem persistência própria além das relações)
- **Invariantes**: equipe do gestor = `manager_id`; equipe do coordenador = união deduplicada com `coordinator_members` (BR-MIGRAR-017); parâmetros externos nunca ampliam escopo.
- **Comandos**: `add_coordinator_member`, `remove_member` (audita + notifica — BR-MIGRAR-026), `approve_team_request`, `reject_team_request` (única parte confirmada de team_requests — AMB-004).

## Contexto `feedback`

### Aggregate: FeedbackForm
- **Root**: `FeedbackForm`
- **Invariantes**: perguntas ordenadas por `sort_order`; tipo ∈ {rating, textarea}; formulário em uso por ciclo aberto não pode ser excluído.
- **Comandos**: `create_form`, `add_question`, `reorder_questions`, `archive_form`.

### Aggregate: FeedbackCycle
- **Root**: `FeedbackCycle`
- **Invariantes**:
  - transições `draft → open → closed → published → archived` e `draft → archived` (BR-MIGRAR-004), somente via comandos;
  - abertura gera requests a partir de permissões ativas de usuários ativos, idempotente por (cycle, giver, receiver, form) (BR-MIGRAR-001/010);
  - limite de concorrência por frequência por tenant (BR-MIGRAR-011);
  - período avaliado pode divergir das datas do ciclo (`evaluated_start/end` — BR-MIGRAR-006);
  - fechamento automático respeita carência de 3 dias (BR-MIGRAR-005, executado pelo scheduler).
- **Comandos**: `create`, `open` (gera requests + outbox), `close`, `publish`, `archive`, `extend_evaluated_period`.
- **Eventos (outbox)**: `cycle.opened`, `cycle.closed`, `cycle.published`.

### Aggregate: FeedbackRequest
- **Root**: `FeedbackRequest`
- **Invariantes**: máquina `pending → draft → submitted`, `pending|draft → waived → pending`, `pending|draft → cancelled` (com justificativa), `pending|draft → expired` (BR-MIGRAR-003; `reviewed` omitido — AMB-003); submissão exige respostas válidas contra o formulário e grava `submitted_at` (BR-MIGRAR-008); rascunho preserva respostas (BR-MIGRAR-012); atraso/expiração é derivação server-side de prazo + tolerância (BR-MIGRAR-007).
- **Comandos**: `start_draft`, `save_draft`, `submit`, `waive`, `resume`, `cancel(justification)`.
- **Eventos (outbox)**: `request.submitted`, `request.cancelled`.

### Serviço de domínio: CycleProgress
- Único cálculo de progresso do sistema: exclui `cancelled`/`waived` do denominador, `submitted` = concluído (BR-MIGRAR-009). Consumido por API (dashboards de todos os papéis) e `reporting`.

### Aggregate: FreeFeedback
- **Root**: `FreeFeedback`
- **Invariantes**: anônimo ⇒ `giver_id` nulo por design (suporta o default LGPD — AMB-001); sensível ⇒ visível só à gestão; leitura registrada por `read_at/read_by`.
- **Comandos**: `send`, `mark_read`.

### Aggregate: CycleNote
- **Root**: `CycleNote` — anotações por pessoa/ciclo; sem invariantes além de autoria e escopo de equipe.

## Contexto `client_eval`

### Aggregate: ClientEvalForm
- **Root**: `ClientEvalForm` — perguntas dinâmicas ordenadas, tipos {rating, text, textarea, yes_no, nps, multiple_choice} (BR-MIGRAR-020).

### Aggregate: ClientEvaluation
- **Root**: `ClientEvaluation`
- **Invariantes**:
  - máquina `pending → in_progress → submitted` e `pending → expired` (BR-MIGRAR-022; expiração via scheduler);
  - submissão por token: update condicional atômico exigindo `status='pending'` + token válido; segunda submissão retorna confirmação idempotente (BR-MIGRAR-019);
  - fluxo `spontaneous` habilitado apenas por flag do tenant (AMB-002);
  - sinalização automática por nota baixa/palavras negativas do tenant (BR-MIGRAR-021);
  - WhatsApp mascarado em toda serialização sem permissão explícita (BR-MIGRAR-022).
- **Comandos**: `request_evaluation` (gera token + expiração), `open_by_token`, `submit_by_token`, `expire`.
- **Eventos (outbox)**: `client_eval.submitted`, `client_eval.flagged_negative`.
- **Entidades/VOs**: `EvalToken` (VO com expiração), `ServiceTag`.

## Contexto `engagement`

### Aggregate: Notification
- **Root**: `Notification` — destinatário, tipo, título, mensagem, link; não lida = `read_at IS NULL` (BR-MIGRAR-023).
- **Comandos**: `create` (via consumo de outbox), `mark_read`.

### Aggregate: OutboxMessage
- **Root**: `OutboxMessage` — gravado na transação do comando de origem; idempotência por chave natural (ex.: `update_id + user_id` para comunicações de ciclo — BR-MIGRAR-024); despachado pelo worker com retry exponencial + DLQ (AMB-006). Falha de despacho jamais desfaz a operação principal (BR-MIGRAR-025).

### Aggregate: AuditLog
- **Root**: `AuditLog` — append-only; `actor_id` (nunca `user_id` — BR-MIGRAR-026); gravado via outbox pós-commit.

### Aggregate: TenantSetting
- **Root**: `TenantSetting` — key/value por tenant (catálogo inicial: as 8 chaves do legado — BR-MIGRAR-027); upsert por chave com concorrência otimista e `updated_by` obrigatório.

### Aggregates menores: PlatformUpdate (comunicados com contagem de notificados), ContactMessage (máquina `novo → em_andamento → resolvido`).

## Contexto `reporting`

Sem aggregates — read models:
- `Report360Query`, `ClientReportQuery`, `EngagementQuery` (só ciclos fechados, exclui pessoas sem requests — BR-MIGRAR-028), `ExecutiveReport` (validações de escopo — BR-MIGRAR-028).
- `ExportJob` (única entidade persistida): pedido de exportação assíncrona (PDF/XLSX) processado pelo worker com link de download (BR-MIGRAR-029/030); CSV síncrono respeita filtros ativos e separador `;`.

## Tabela: Regras de domínio (BR-MIGRAR → local no domínio novo)

| Regra | Local |
|---|---|
| BR-MIGRAR-001 | `feedback.FeedbackCycle.open` |
| BR-MIGRAR-002 | `feedback.PermissionService.grant` (reversa peer em transação) |
| BR-MIGRAR-003 | `feedback.FeedbackRequest` (máquina de estados) |
| BR-MIGRAR-004 | `feedback.FeedbackCycle` (máquina de estados) |
| BR-MIGRAR-005 | `worker.scheduler.close_cycles_job` (parâmetro de carência) |
| BR-MIGRAR-006 | `feedback.FeedbackCycle.extend_evaluated_period` |
| BR-MIGRAR-007 | `feedback.RequestQueryService.overdue_of` (derivação server-side) |
| BR-MIGRAR-008 | `feedback.FeedbackRequest.submit` |
| BR-MIGRAR-009 | `feedback.CycleProgress` (serviço único) |
| BR-MIGRAR-010 | constraint UNIQUE + idempotência em `FeedbackCycle.open` |
| BR-MIGRAR-011 | `feedback.FeedbackCycle.open` (checagem por frequência/tenant) |
| BR-MIGRAR-012 | `feedback.FeedbackRequest.save_draft` |
| BR-MIGRAR-013 | `core.security` (deny-by-default) |
| BR-MIGRAR-014 | `core.security.require_role` (matriz RBAC) |
| BR-MIGRAR-015 | `identity.CapabilityFlags` + guards |
| BR-MIGRAR-016 | `identity.UserAccount` / `ActiveRole` |
| BR-MIGRAR-017 | `identity.TeamScope.resolve` |
| BR-MIGRAR-018 | `identity.Profile.soft_delete` |
| BR-MIGRAR-019 | `client_eval.ClientEvaluation.submit_by_token` |
| BR-MIGRAR-020 | `client_eval.ClientEvalForm` |
| BR-MIGRAR-021 | `client_eval.ClientEvaluation` (sinalização) |
| BR-MIGRAR-022 | `client_eval` serializers (status map + máscara) |
| BR-MIGRAR-023 | `engagement.Notification` |
| BR-MIGRAR-024 | `engagement.OutboxMessage` (idempotência) |
| BR-MIGRAR-025 | padrão outbox (AD-04) |
| BR-MIGRAR-026 | `engagement.AuditLog` |
| BR-MIGRAR-027 | `engagement.TenantSetting` |
| BR-MIGRAR-028 | `reporting.EngagementQuery` / `ExecutiveReport` |
| BR-MIGRAR-029 | `reporting.ExportJob` + queries |
| BR-MIGRAR-030 | `worker.jobs.send_report_email` (adapter) |

## Tabela: Rastreabilidade para legado

| Elemento novo | Origem no legado | Tipo de mapeamento |
|---|---|---|
| `identity.Tenant` | (inexistente — sistema single-tenant) | novo |
| `identity.UserAccount` | Supabase Auth (`auth.users`) | novo (substitui — BR-DESCARTAR-005) |
| `identity.Profile` | `profiles` + flags | 1-para-1 |
| `identity.TeamScope` | `manager_id` + `coordinator_members` + `team_requests` | fundido |
| `feedback.FeedbackForm` | `feedback_forms` + `feedback_form_questions` | 1-para-1 |
| `feedback.FeedbackCycle` | `feedback_cycles` + lógica de `AdminCiclos.tsx` | fundido (dados + regra dispersa) |
| `feedback.FeedbackRequest` | `feedback_requests` + `feedback_answers` | fundido (answers como entidade filha) |
| `feedback.CycleProgress` | cálculos duplicados em gestor/coordenador/dashboard | fundido (3→1) |
| `feedback.FreeFeedback` | `free_feedbacks` | 1-para-1 |
| `feedback.CycleNote` | `cycle_notes` | 1-para-1 |
| `client_eval.ClientEvaluation` | `client_feedbacks` + `client_feedback_answers` + tags | fundido |
| `client_eval.ClientEvalForm` | `client_feedback_forms` + questions | 1-para-1 |
| `engagement.Notification` | `notifications` | 1-para-1 |
| `engagement.OutboxMessage` | Edge Functions `waitUntil` + outbox validado | novo (substitui — BR-DESCARTAR-002) |
| `engagement.AuditLog` | `audit_logs` | 1-para-1 |
| `engagement.TenantSetting` | `company_settings` | 1-para-1 (generalizado por tenant) |
| `engagement.PlatformUpdate` | `platform_updates` | 1-para-1 |
| `engagement.ContactMessage` | `feedback_contacts` | 1-para-1 |
| `reporting.*Query` | agregações client-side de `AdminRelatorios.tsx` etc. | fundido (movidas para server) |
| `reporting.ExportJob` | exportações síncronas no browser (jspdf/xlsx) | novo (substitui mecanismo) |
| Caches IA (`feedback_ai_*`) | `feedback_ai_analysis`, `feedback_ai_cycle_analysis` | adiado (AMB-005 — não modelado no primeiro corte) |
| Agenda (`daily_appointments`, `google_calendar_tokens`) | módulo agenda | adiado (AMB-007 — fase 2) |

## Notas
- `reviewed` foi deliberadamente omitido da máquina de `FeedbackRequest` (AMB-003). O valor existente em produção será normalizado na migração de dados (ver `data_migration_plan.md`).
- Transições faltantes de `team_requests` (cancelamento/expiração) são **decisão de design em aberto controlada**: o primeiro corte implementa só aprovação/rejeição (AMB-004); demais transições retornam 409.
