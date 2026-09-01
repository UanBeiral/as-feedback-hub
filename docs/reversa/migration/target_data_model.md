---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: target_data_model
producedBy: designer
hash: "sha256:682b6354efbad2f82ff592f8e51931227eac34d9772a2a44f13282cbf89cd258"
---

# Target Data Model

> Schema PostgreSQL do sistema novo. Convenções: PK `id uuid DEFAULT gen_random_uuid()`; toda tabela de domínio tem `tenant_id uuid NOT NULL REFERENCES tenants(id)` + índice composto iniciando por `tenant_id`; `created_at/updated_at timestamptz` em todas; migrations via Alembic. RLS não é mecanismo primário (AD-10).

## Entidades por contexto

| Tabela | Contexto | Aggregate dono | Origem no legado |
|---|---|---|---|
| `tenants` | identity | Tenant | novo |
| `users` | identity | UserAccount | novo (substitui `auth.users`) |
| `refresh_tokens` | identity | UserAccount | novo |
| `profiles` | identity | Profile | `profiles` (renomeações mínimas) |
| `departments` | identity | Profile | `departments` |
| `profile_departments` | identity | Profile | `profile_departments` |
| `coordinator_members` | identity | TeamScope | `coordinator_members` (+ FKs físicas que faltavam) |
| `team_requests` | identity | TeamScope | `team_requests` (+ FKs físicas) |
| `feedback_forms` | feedback | FeedbackForm | `feedback_forms` |
| `feedback_form_questions` | feedback | FeedbackForm | `feedback_form_questions` |
| `feedback_cycles` | feedback | FeedbackCycle | `feedback_cycles` |
| `feedback_permissions` | feedback | FeedbackCycle | `feedback_permissions` |
| `feedback_requests` | feedback | FeedbackRequest | `feedback_requests` |
| `feedback_answers` | feedback | FeedbackRequest | `feedback_answers` (+ FKs físicas) |
| `free_feedbacks` | feedback | FreeFeedback | `free_feedbacks` |
| `cycle_notes` | feedback | CycleNote | `cycle_notes` |
| `client_eval_forms` | client_eval | ClientEvalForm | `client_feedback_forms` |
| `client_eval_form_questions` | client_eval | ClientEvalForm | `client_feedback_form_questions` |
| `client_evaluations` | client_eval | ClientEvaluation | `client_feedbacks` |
| `client_eval_answers` | client_eval | ClientEvaluation | `client_feedback_answers` |
| `service_tags` | client_eval | ClientEvaluation | `client_feedback_service_tags` |
| `client_evaluation_tags` | client_eval | ClientEvaluation | `client_feedback_tags` |
| `notifications` | engagement | Notification | `notifications` |
| `outbox_messages` | engagement | OutboxMessage | novo |
| `audit_logs` | engagement | AuditLog | `audit_logs` |
| `tenant_settings` | engagement | TenantSetting | `company_settings` |
| `platform_updates` | engagement | PlatformUpdate | `platform_updates` |
| `contact_messages` | engagement | ContactMessage | `feedback_contacts` |
| `export_jobs` | reporting | ExportJob | novo |

**Fora do primeiro corte** (dados arquivados, sem tabela nova): `feedback_ai_analysis`, `feedback_ai_cycle_analysis` (AMB-005 — caches regeneráveis), `daily_appointments`, `google_calendar_tokens` (AMB-007 — fase 2; tokens OAuth não migram por segurança).

## DDL (núcleo representativo)

```sql
CREATE TABLE tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email citext NOT NULL,
  password_hash text NOT NULL,             -- bcrypt (compatível com export Supabase — R-07)
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','deleted')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);

CREATE TABLE profiles (
  id uuid PRIMARY KEY,                      -- = users.id (1:1)
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL UNIQUE REFERENCES users(id),
  full_name text NOT NULL,
  role text NOT NULL CHECK (role IN ('admin','rh','gestor','colaborador')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','deleted')),
  department_id uuid REFERENCES departments(id),
  manager_id uuid REFERENCES profiles(id),
  is_coordinator boolean NOT NULL DEFAULT false,
  whatsapp text,
  can_request_client_feedback boolean NOT NULL DEFAULT false,
  can_view_feedback_answers boolean NOT NULL DEFAULT false,
  can_view_team_history boolean NOT NULL DEFAULT false,
  can_generate_reports boolean NOT NULL DEFAULT false,
  can_view_manager_dashboard boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_profiles_tenant ON profiles (tenant_id, status);
CREATE INDEX idx_profiles_manager ON profiles (tenant_id, manager_id);

CREATE TABLE feedback_cycles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name text NOT NULL,
  form_id uuid NOT NULL REFERENCES feedback_forms(id),
  frequency text,                           -- base do limite de concorrência (BR-MIGRAR-011)
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','open','closed','published','archived')),
  start_date date NOT NULL,
  end_date date NOT NULL,
  evaluated_start date,                     -- override manual (BR-MIGRAR-006)
  evaluated_end date,
  closed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_cycles_tenant_status ON feedback_cycles (tenant_id, status);

CREATE TABLE feedback_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  cycle_id uuid NOT NULL REFERENCES feedback_cycles(id),
  form_id uuid NOT NULL REFERENCES feedback_forms(id),
  giver_id uuid NOT NULL REFERENCES profiles(id),
  receiver_id uuid NOT NULL REFERENCES profiles(id),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','draft','submitted','expired','waived','cancelled')),
  due_date date,
  submitted_at timestamptz,
  cancel_justification text,
  read_at timestamptz,
  read_by uuid REFERENCES profiles(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, giver_id, receiver_id, form_id)   -- BR-MIGRAR-010
);
CREATE INDEX idx_requests_tenant_cycle ON feedback_requests (tenant_id, cycle_id, status);
CREATE INDEX idx_requests_giver ON feedback_requests (tenant_id, giver_id, status);

CREATE TABLE client_evaluations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  target_user_id uuid NOT NULL REFERENCES profiles(id),
  form_id uuid NOT NULL REFERENCES client_eval_forms(id),
  flow_type text NOT NULL DEFAULT 'requested' CHECK (flow_type IN ('requested','spontaneous')),
  requested_by uuid REFERENCES profiles(id),
  client_name text,
  client_whatsapp text,
  client_email text,
  token text UNIQUE,                        -- BR-MIGRAR-019
  token_expires_at timestamptz,
  contact_motivation text,
  overall_rating int,
  recommendation_rating int,
  has_negative boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','in_progress','submitted','expired')),
  submitted_at timestamptz,
  tracking_data jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_client_evals_tenant_target ON client_evaluations (tenant_id, target_user_id, status);

CREATE TABLE outbox_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  topic text NOT NULL,                      -- ex: cycle.opened, request.submitted
  payload jsonb NOT NULL,
  idempotency_key text NOT NULL,            -- ex: update_id:user_id (BR-MIGRAR-024)
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','dispatched','failed','dead')),
  attempts int NOT NULL DEFAULT 0,
  next_attempt_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (topic, idempotency_key)
);
CREATE INDEX idx_outbox_pending ON outbox_messages (status, next_attempt_at);

CREATE TABLE tenant_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  key text NOT NULL,
  value text,
  updated_by uuid NOT NULL REFERENCES profiles(id),   -- obrigatório (dívida do legado sanada)
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, key)                              -- BR-MIGRAR-027
);

CREATE TABLE audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  actor_id uuid REFERENCES profiles(id),               -- actor_id, não user_id (BR-MIGRAR-026)
  action text NOT NULL,
  table_name text,
  record_id uuid,
  details jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_tenant_time ON audit_logs (tenant_id, created_at DESC);
```

Demais tabelas seguem as mesmas convenções; colunas espelham o legado documentado em `_reversa_sdd/database/` com renomeações da tabela de mapeamento acima.

## Relacionamentos e restrições estruturais

- **Toda FK que era "sem FK" no legado vira FK física** (`coordinator_members`, `team_requests`, `feedback_answers`, `notifications.user_id`, `contact_messages.created_by`) — dívida estrutural sanada.
- **Soft-delete**: `profiles.status='deleted'` mantém FKs válidas; `free_feedbacks.giver_id` é `ON DELETE SET NULL` apenas para anonimização explícita (AMB-001), nunca por remoção de usuário.
- **Isolamento multi-tenant**: repositórios sempre filtram por `tenant_id` resolvido do contexto de sessão; testes de isolamento no CI (AD-10 / R-09). Índices compostos começam por `tenant_id`.
- **Concorrência**: `tenant_settings` usa upsert por `(tenant_id, key)` com verificação otimista de `updated_at`; submissão pública usa `UPDATE ... WHERE status='pending' AND token=... AND token_expires_at > now()` retornando linha afetada (guard atômico).

## Considerações do paradigma alvo

- **Transactional outbox** (`outbox_messages`) substitui Edge Functions/`waitUntil`; o worker faz polling por `status='pending' AND next_attempt_at <= now()` com backoff exponencial e move para `dead` (DLQ) após N tentativas (AMB-006).
- **Scheduler**: jobs de fechamento de ciclo (carência 3 dias) e expiração de tokens rodam no worker; nenhum `pg_cron` (BR-DESCARTAR-003).
- **`response_data jsonb` do legado**: o legado mantinha respostas duplicadas em `feedback_requests.response_data` e `feedback_answers`. O modelo novo mantém **apenas `feedback_answers`** como fonte de verdade. 🟡 A migração precisa reconciliar as duas fontes (ver plano).

## Origem no legado (mudanças que não são 1-para-1)

| Mudança | Detalhe |
|---|---|
| Renomeação de contexto | `client_feedback_*` → `client_eval_*`; `company_settings` → `tenant_settings`; `feedback_contacts` → `contact_messages` |
| Divisão | `auth.users` (Supabase) → `users` + `refresh_tokens` |
| Fusão | `feedback_requests.response_data` (jsonb) absorvido por `feedback_answers` |
| Novo | `tenants`, `outbox_messages`, `export_jobs` |
| Removido do corte | `feedback_ai_*`, `daily_appointments`, `google_calendar_tokens` (arquivados no export final) |
| Status removido | `feedback_requests.status='reviewed'` não existe no schema novo (AMB-003) |
