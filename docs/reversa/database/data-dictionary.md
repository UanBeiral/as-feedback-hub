# Dicionário de Dados — Banco Completo

> Gerado pelo **Data Master** (Reversa) em 2026-08-28.
> Fontes: migrations SQL em `supabase/migrations/` (🟢), tipos gerados `src/integrations/supabase/types.ts` (🟢, parcialmente desatualizado) e uso no código frontend/edge functions (🟡).
> Banco: PostgreSQL (Supabase), schema `public`. Extensões: `pg_cron`, `pg_net`.

## Escala de confiança

- 🟢 **CONFIRMADO** — DDL/migration presente no repositório
- 🟡 **INFERIDO** — deduzido de queries/inserts no código; tipos e nulabilidade podem divergir
- 🔴 **LACUNA** — requer consulta ao banco de produção

## Inventário de tabelas (28)

| # | Tabela | Domínio | Propósito | Fonte |
|---|--------|---------|-----------|:-----:|
| 1 | `profiles` | Identidade | Perfil do usuário (espelho de `auth.users`), papel e hierarquia | 🟢 |
| 2 | `departments` | Identidade | Departamentos da empresa | 🟢 |
| 3 | `profile_departments` | Identidade | Junção N:M perfil↔departamento | 🟢 |
| 4 | `coordinator_members` | Identidade | Junção coordenador↔membro da equipe | 🟢 |
| 5 | `team_requests` | Identidade | Solicitações de inclusão de membro em equipe | 🟢 |
| 6 | `feedback_forms` | Feedback interno | Formulários de feedback (ciclos) | 🟢 |
| 7 | `feedback_form_questions` | Feedback interno | Perguntas dos formulários internos | 🟢 |
| 8 | `feedback_cycles` | Feedback interno | Ciclos de feedback 360 | 🟢 |
| 9 | `feedback_permissions` | Feedback interno | Quem avalia quem (matriz avaliador↔avaliado) | 🟢 |
| 10 | `feedback_requests` | Feedback interno | Solicitações de feedback dentro de um ciclo | 🟢 |
| 11 | `feedback_answers` | Feedback interno | Respostas por pergunta de cada request | 🟢 |
| 12 | `cycle_notes` | Feedback interno | Anotações do avaliador sobre pessoas durante o ciclo | 🟡 |
| 13 | `feedback_ai_analysis` | Feedback interno | Cache da análise de IA por pessoa/ciclo | 🟡 |
| 14 | `feedback_ai_cycle_analysis` | Feedback interno | Cache da análise de IA consolidada do ciclo | 🟡 |
| 15 | `free_feedbacks` | Feedback livre | Feedback espontâneo entre colegas (anônimo/sensível) | 🟢 |
| 16 | `client_feedback_forms` | Feedback de clientes | Formulários públicos de avaliação por clientes | 🟡 |
| 17 | `client_feedback_form_questions` | Feedback de clientes | Perguntas dos formulários públicos | 🟡 |
| 18 | `client_feedbacks` | Feedback de clientes | Avaliação de cliente (espontânea ou solicitada via token) | 🟡 |
| 19 | `client_feedback_answers` | Feedback de clientes | Respostas por pergunta da avaliação de cliente | 🟡 |
| 20 | `client_feedback_service_tags` | Feedback de clientes | Catálogo de tags de serviço | 🟡 |
| 21 | `client_feedback_tags` | Feedback de clientes | Junção N:M avaliação↔tag | 🟡 |
| 22 | `google_calendar_tokens` | Agenda | Tokens OAuth do Google Calendar por usuário | 🟡 |
| 23 | `daily_appointments` | Agenda | Atendimentos do dia importados do Google Calendar | 🟡 |
| 24 | `notifications` | Plataforma | Notificações in-app | 🟡 |
| 25 | `platform_updates` | Plataforma | Comunicados de novidades publicados pelo admin | 🟢 |
| 26 | `company_settings` | Plataforma | Configurações chave-valor da empresa | 🟢 |
| 27 | `feedback_contacts` | Plataforma | Mensagens de contato/sugestão internas | 🟢 |
| 28 | `audit_logs` | Plataforma | Trilha de auditoria de ações | 🟢 |

Além das tabelas: bucket de storage `company-assets` (público) 🟢.

---

## Domínio: Identidade & Organização

### `profiles` 🟢

PK: `id` (= `auth.users.id`, `ON DELETE CASCADE`).

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | — | PK, FK → `auth.users(id)` CASCADE |
| `full_name` | text | sim | — | |
| `email` | text | não | — | |
| `job_title` | text | sim | — | |
| `role` | text | não | `'colaborador'` | Valores em uso: `admin`, `rh`, `gestor`, `colaborador` (default original era `'collaborator'`, alterado em migration) |
| `department_id` | uuid | sim | — | FK → `departments(id)` |
| `manager_id` | uuid | sim | — | FK → `profiles(id)` (auto-referência) |
| `status` | text | não | `'active'` | CHECK: `active`, `inactive`, `deleted` |
| `is_active` | boolean | não | `true` | Redundante com `status` (débito técnico) |
| `is_coordinator` | boolean | não | `false` | Papel transversal de coordenador |
| `whatsapp` | text | sim | — | |
| `created_at` | timestamptz | não | `now()` | |
| `updated_at` | timestamptz | não | `now()` | |

### `departments` 🟢

| Coluna | Tipo | Nulo | Default |
|--------|------|:---:|---------|
| `id` | uuid | não | `gen_random_uuid()` (PK) |
| `name` | text | não | — |
| `created_at` | timestamptz | não | `now()` |

### `profile_departments` 🟢

Junção N:M. UNIQUE(`profile_id`, `department_id`).

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `profile_id` | uuid | não | FK → `profiles(id)` CASCADE |
| `department_id` | uuid | não | FK → `departments(id)` CASCADE |
| `created_at` | timestamptz | não | |

### `coordinator_members` 🟢

UNIQUE(`coordinator_id`, `member_id`). **Sem FKs declaradas** (colunas uuid soltas).

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `coordinator_id` | uuid | não | referencia logicamente `profiles(id)` — sem constraint |
| `member_id` | uuid | não | referencia logicamente `profiles(id)` — sem constraint |
| `created_at` | timestamptz | não | |

### `team_requests` 🟢

**Sem FKs declaradas.**

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `requester_id` | uuid | não | — | logicamente `profiles(id)` |
| `requested_member_id` | uuid | não | — | logicamente `profiles(id)` |
| `status` | text | não | `'pending'` | 🟡 valores: `pending`, `approved`, `rejected` |
| `approved_by` | uuid | sim | — | |
| `rejection_reason` | text | sim | — | |
| `created_at` | timestamptz | não | `now()` | |

---

## Domínio: Feedback interno (ciclos 360)

### `feedback_forms` 🟢

| Coluna | Tipo | Nulo | Default |
|--------|------|:---:|---------|
| `id` | uuid | não | `gen_random_uuid()` (PK) |
| `name` | text | não | — |
| `description` | text | sim | — |
| `created_at` / `updated_at` | timestamptz | não | `now()` |

### `feedback_form_questions` 🟢

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `form_id` | uuid | não | — | FK → `feedback_forms(id)` CASCADE |
| `question_text` | text | não | — | |
| `question_type` | text | não | `'textarea'` | 🟡 valores em uso: `rating`, `textarea` |
| `sort_order` | int | não | `0` | |
| `required` | boolean | não | `true` | |
| `help_text` | text | sim | — | |
| `created_at` | timestamptz | não | `now()` | |

### `feedback_cycles` 🟢

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `name` | text | não | — | |
| `start_date` | date | sim | — | |
| `end_date` | date | sim | — | |
| `status` | text | não | `'active'` | 🟡 valores em uso: `open`, `closed` (default `'active'` aparenta ser legado) |
| `form_id` | uuid | sim | — | FK → `feedback_forms(id)` |
| `evaluated_start` | date | sim | — | Override manual do período avaliado; NULL = regra automática (mês anterior ao `start_date`) |
| `evaluated_end` | date | sim | — | idem |
| `created_at` / `updated_at` | timestamptz | não | `now()` | |

### `feedback_permissions` 🟢

UNIQUE(`reviewer_id`, `reviewee_id`, `permission_type`, `cycle_id`).

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `reviewer_id` | uuid | não | — | FK → `profiles(id)` CASCADE |
| `reviewee_id` | uuid | não | — | FK → `profiles(id)` CASCADE |
| `permission_type` | text | não | `'peer'` | 🟡 valores em uso: `peer`, `manager`, `subordinate`, `self` |
| `cycle_id` | uuid | sim | — | FK → `feedback_cycles(id)` SET NULL; NULL = permissão permanente |
| `active` | boolean | não | `true` | renomeada de `is_active` em migration |
| `created_at` | timestamptz | não | `now()` | |

### `feedback_requests` 🟢

UNIQUE(`cycle_id`, `giver_id`, `receiver_id`).

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `cycle_id` | uuid | não | — | FK → `feedback_cycles(id)` CASCADE |
| `form_id` | uuid | sim | — | FK → `feedback_forms(id)` |
| `giver_id` | uuid | não | — | FK → `profiles(id)` |
| `receiver_id` | uuid | não | — | FK → `profiles(id)` |
| `status` | text | não | `'pending'` | Valores em uso: `pending`, `draft`, `submitted`, `expired`, `waived`, `cancelled`, `reviewed` |
| `due_date` | date | sim | — | |
| `submitted_at` | timestamptz | sim | — | |
| `response_data` | jsonb | sim | — | |
| `read_at` | timestamptz | sim | `NULL` | marcação de leitura pelo receiver |
| `read_by` | uuid | sim | `NULL` | **sem FK declarada** |
| `created_at` / `updated_at` | timestamptz | não | `now()` | |

### `feedback_answers` 🟢

UNIQUE(`request_id`, `question_id`). **Sem FKs declaradas** (`request_id` e `question_id` são uuid soltos — confirmado por `Relationships: []` no types.ts).

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `request_id` | uuid | não | logicamente `feedback_requests(id)` |
| `question_id` | uuid | não | logicamente `feedback_form_questions(id)` |
| `answer_text` | text | sim | |
| `answer_score` | integer | sim | |
| `created_at` / `updated_at` | timestamptz | não | |

### `cycle_notes` 🟡

FKs confirmadas pelos nomes usados em embeds PostgREST: `cycle_notes_cycle_id_fkey`, `cycle_notes_author_id_fkey`, `cycle_notes_about_user_id_fkey`.

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `cycle_id` | uuid | não | FK → `feedback_cycles(id)` |
| `author_id` | uuid | não | FK → `profiles(id)` |
| `about_user_id` | uuid | não | FK → `profiles(id)` |
| `content` | text | não | |
| `is_audio_transcription` | boolean | não | anotação ditada por áudio |
| `created_at` / `updated_at` | timestamptz | não | `updated_at` atualizado pelo app |

### `feedback_ai_analysis` 🟡

UNIQUE(`person_id`, `cycle_id`) — 🟢 validado por humano em 2026-08-25 (upsert `onConflict: "person_id,cycle_id"`).

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `person_id` | uuid | não | FK → `profiles(id)` (validado) |
| `cycle_id` | uuid | não | FK → `feedback_cycles(id)` (validado) |
| `analysis` | jsonb | não | resultado da análise de IA por pessoa |

🔴 LACUNA: colunas não-chave (id, timestamps) não confirmadas — fechar consultando produção.

### `feedback_ai_cycle_analysis` 🟡

UNIQUE(`cycle_id`, `generated_by`) — 🟢 validado por humano em 2026-08-25.

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `cycle_id` | uuid | não | FK → `feedback_cycles(id)` (validado) |
| `generated_by` | uuid | não | FK → `profiles(id)` (validado) |
| `analysis` | jsonb | não | análise consolidada do ciclo |
| `member_count` | integer | sim | nº de membros na geração |

---

## Domínio: Feedback livre

### `free_feedbacks` 🟢

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `giver_id` | uuid | sim | — | FK → `profiles(id)` SET NULL; NULL quando anônimo |
| `receiver_id` | uuid | não | — | FK → `profiles(id)` CASCADE |
| `is_anonymous` | boolean | não | `false` | |
| `is_sensitive` | boolean | não | `false` | sensível: receiver não vê, só gestão |
| `positives` | text | sim | — | |
| `improvements` | text | sim | — | |
| `message` | text | sim | — | |
| `read_at` | timestamptz | sim | — | |
| `read_by` | uuid | sim | — | FK → `profiles(id)` |
| `created_at` / `updated_at` | timestamptz | não | `now()` | |

---

## Domínio: Feedback de clientes (fluxo público)

> Todo este domínio foi criado fora das migrations do repositório (via dashboard). Estrutura inferida do código — 🟡. A migration `20260703150000` referencia essas tabelas e confirma a existência de `token`, `token_expires_at`, `status`, `submitted_at`, `tracking_data` e das colunas concedidas ao papel `anon`.

### `client_feedback_forms` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `name` | text | |
| `is_default` | boolean | formulário usado no fluxo espontâneo |
| `is_active` | boolean | |

### `client_feedback_form_questions` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `form_id` | uuid | FK → `client_feedback_forms(id)` |
| `question_text` | text | |
| `question_type` | text | `rating`, `text`, `textarea`, `yes_no`, `nps`, `multiple_choice` |
| `is_required` | boolean | |
| `display_order` | int | |
| `placeholder` | text (nulo) | |

### `client_feedbacks` 🟡

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `client_name` | text | sim* | preenchido na submissão |
| `client_whatsapp` | text | sim* | dígitos apenas (normalizado no app) |
| `client_email` | text | sim | |
| `target_user_id` | uuid | não | FK → `profiles(id)`; avaliado |
| `form_id` | uuid | sim | FK → `client_feedback_forms(id)` |
| `flow_type` | text | não | `requested` (via token) ou `spontaneous` |
| `requested_by` | uuid | sim | FK → `profiles(id)`; quem gerou o link |
| `token` | text | sim | token do link público (fluxo `requested`) |
| `token_expires_at` | timestamptz | sim | validade do link |
| `contact_motivation` | text | sim | `praise`, `evaluate`, `problem`, `other` |
| `contact_motivation_text` | text | sim | texto livre quando não é `evaluate` |
| `overall_rating` | integer | sim | |
| `recommendation_rating` | integer | sim | NPS |
| `has_negative` | boolean | sim | flag de avaliação negativa |
| `status` | text | não | `pending`, `in_progress`, `submitted` |
| `submitted_at` | timestamptz | sim | |
| `tracking_data` | jsonb | sim | metadados de rastreio da submissão |
| `created_at` | timestamptz | não | |

### `client_feedback_answers` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `client_feedback_id` | uuid | FK → `client_feedbacks(id)` |
| `question_id` | uuid | FK → `client_feedback_form_questions(id)` |
| `rating_value` | integer (nulo) | |
| `text_value` | text (nulo) | |

### `client_feedback_service_tags` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `name` | text | |
| `is_active` | boolean | |
| `display_order` | int | |

### `client_feedback_tags` 🟡

Junção N:M avaliação↔tag.

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `client_feedback_id` | uuid | FK → `client_feedbacks(id)` |
| `tag_id` | uuid | FK → `client_feedback_service_tags(id)` |

---

## Domínio: Agenda & Google Calendar

### `google_calendar_tokens` 🟡

Upsert com `onConflict: "user_id"` ⇒ UNIQUE(`user_id`).

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `user_id` | uuid | UNIQUE; FK → `profiles(id)`/`auth.users(id)` |
| `access_token` | text | ⚠️ segredo em texto no banco |
| `refresh_token` | text | ⚠️ segredo em texto no banco |
| `expires_at` | timestamptz | |
| `updated_at` | timestamptz | |

### `daily_appointments` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `user_id` | uuid | dono da agenda sincronizada |
| `event_date` | date | |
| `event_time` | text/time | formatada pelo app |
| `event_title` | text | resumo do evento |
| `client_name` | text | extraído do título |
| `google_event_id` | text | dedupe por usuário+dia |
| `feedback_requested` | boolean | default `false`; checklist do dia |
| `verified_by` | uuid (nulo) | quem marcou o checklist |
| `verified_at` | timestamptz (nulo) | |

---

## Domínio: Plataforma & suporte

### `notifications` 🟡

| Coluna | Tipo | Observações |
|--------|------|-------------|
| `id` | uuid | PK |
| `user_id` | uuid | destinatário |
| `type` | text | `cycle_opened`, `calendar_sync`, `feedback_check_alert`, `client_feedback_received`, `client_feedback_negative`, `platform_update`, entre outros |
| `title` | text | |
| `message` | text (nulo) | |
| `link` | text (nulo) | rota interna do app |
| `read_at` | timestamptz (nulo) | NULL = não lida |
| `created_at` | timestamptz | |

### `platform_updates` 🟢

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `title` | text | não | — | |
| `content` | text | não | — | |
| `created_by` | uuid | sim | — | FK → `profiles(id)` |
| `notified_count` | int | sim | — | emails enviados na publicação |
| `draft` | boolean | não | `false` | rascunho auto-salvo do admin |
| `created_at` | timestamptz | não | `now()` | |

### `company_settings` 🟢

Chave-valor. UNIQUE(`key`).

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `key` | text | não | UNIQUE. Chaves conhecidas: `logo_url`, `company_name`, `client_feedback_motivations` (JSON) |
| `value` | text | sim | |
| `created_at` / `updated_at` | timestamptz | não | |

Seed inicial: `logo_url = NULL`, `company_name = 'Amadeus & Santos Advogados Associados'`.

### `feedback_contacts` 🟢

| Coluna | Tipo | Nulo | Default | Observações |
|--------|------|:---:|---------|-------------|
| `id` | uuid | não | `gen_random_uuid()` | PK |
| `type` | text | não | — | |
| `company` | text | sim | — | |
| `contact_name` | text | não | — | |
| `email` | text | não | — | |
| `phone` | text | sim | — | |
| `message` | text | não | — | |
| `status` | text | não | `'novo'` | |
| `created_by` | uuid | não | — | **sem FK declarada** |
| `created_at` / `updated_at` | timestamptz | não | `now()` | |

### `audit_logs` 🟢

| Coluna | Tipo | Nulo | Observações |
|--------|------|:---:|-------------|
| `id` | uuid | não | PK |
| `user_id` | uuid | sim | FK → `auth.users(id)` SET NULL |
| `action` | text | não | |
| `table_name` | text | sim | |
| `record_id` | uuid | sim | |
| `details` | jsonb | sim | |
| `created_at` | timestamptz | não | |

---

## Storage

| Bucket | Público | Uso | Fonte |
|--------|:---:|-----|:-----:|
| `company-assets` | sim | logo e ativos da empresa; escrita restrita a admin/rh via RLS em `storage.objects` | 🟢 |

## Lacunas consolidadas 🔴

1. DDL definitivo das 12 tabelas 🟡 (domínio `client_*`, `cycle_notes`, `daily_appointments`, `notifications`, `google_calendar_tokens`, `feedback_ai_*`) não está no repositório — fechar com `supabase db pull` ou consulta a produção.
2. `src/integrations/supabase/types.ts` está desatualizado (não contém as tabelas acima nem `platform_updates`) — o app usa casts `as any` para contorná-las.
3. Jobs do `pg_cron` (agendamento de `auto-cycle-manager`, `google-calendar-sync`, `send-weekly-summary` etc.) são definidos direto no banco e não constam do repositório.
4. Índices além dos implícitos (PK/UNIQUE) não são declarados em nenhuma migration.
