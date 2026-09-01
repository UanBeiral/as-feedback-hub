# Relacionamentos — Banco de Dados

> Gerado pelo **Data Master** (Reversa) em 2026-08-28.

## Relacionamentos com constraint física (FK declarada)

| De | Coluna | Para | Cardinalidade | ON DELETE | Fonte |
|----|--------|------|:---:|-----------|:---:|
| `profiles` | `id` | `auth.users(id)` | 1:1 | CASCADE | 🟢 |
| `profiles` | `department_id` | `departments(id)` | N:1 | — | 🟢 |
| `profiles` | `manager_id` | `profiles(id)` | N:1 (auto-ref) | — | 🟢 |
| `profile_departments` | `profile_id` | `profiles(id)` | N:1 | CASCADE | 🟢 |
| `profile_departments` | `department_id` | `departments(id)` | N:1 | CASCADE | 🟢 |
| `feedback_form_questions` | `form_id` | `feedback_forms(id)` | N:1 | CASCADE | 🟢 |
| `feedback_cycles` | `form_id` | `feedback_forms(id)` | N:1 | — | 🟢 |
| `feedback_permissions` | `reviewer_id` | `profiles(id)` | N:1 | CASCADE | 🟢 |
| `feedback_permissions` | `reviewee_id` | `profiles(id)` | N:1 | CASCADE | 🟢 |
| `feedback_permissions` | `cycle_id` | `feedback_cycles(id)` | N:1 | SET NULL | 🟢 |
| `feedback_requests` | `cycle_id` | `feedback_cycles(id)` | N:1 | CASCADE | 🟢 |
| `feedback_requests` | `form_id` | `feedback_forms(id)` | N:1 | — | 🟢 |
| `feedback_requests` | `giver_id` | `profiles(id)` | N:1 | — | 🟢 |
| `feedback_requests` | `receiver_id` | `profiles(id)` | N:1 | — | 🟢 |
| `free_feedbacks` | `giver_id` | `profiles(id)` | N:1 | SET NULL | 🟢 |
| `free_feedbacks` | `receiver_id` | `profiles(id)` | N:1 | CASCADE | 🟢 |
| `free_feedbacks` | `read_by` | `profiles(id)` | N:1 | — | 🟢 |
| `platform_updates` | `created_by` | `profiles(id)` | N:1 | — | 🟢 |
| `audit_logs` | `user_id` | `auth.users(id)` | N:1 | SET NULL | 🟢 |
| `cycle_notes` | `cycle_id` | `feedback_cycles(id)` | N:1 | ? | 🟡* |
| `cycle_notes` | `author_id` | `profiles(id)` | N:1 | ? | 🟡* |
| `cycle_notes` | `about_user_id` | `profiles(id)` | N:1 | ? | 🟡* |

\* FKs de `cycle_notes` existem fisicamente (o app usa embeds PostgREST pelos nomes `cycle_notes_*_fkey`, que só funcionam com FK declarada), mas o DDL não está no repositório.

## Relacionamentos lógicos SEM constraint física

Colunas uuid que referenciam outra tabela apenas por convenção — integridade garantida só pelo aplicativo:

| De | Coluna | Para (lógico) | Risco | Fonte |
|----|--------|------|-------|:---:|
| `feedback_answers` | `request_id` | `feedback_requests(id)` | respostas órfãs se o request for deletado | 🟢 (types.ts confirma `Relationships: []`) |
| `feedback_answers` | `question_id` | `feedback_form_questions(id)` | idem para perguntas | 🟢 |
| `feedback_requests` | `read_by` | `profiles(id)` | — | 🟢 |
| `coordinator_members` | `coordinator_id` / `member_id` | `profiles(id)` | vínculos órfãos | 🟢 |
| `team_requests` | `requester_id` / `requested_member_id` / `approved_by` | `profiles(id)` | idem | 🟢 |
| `feedback_contacts` | `created_by` | `profiles(id)` | idem | 🟢 |
| `notifications` | `user_id` | `profiles(id)` | 🔴 não confirmado se há FK | 🟡 |
| `daily_appointments` | `user_id` / `verified_by` | `profiles(id)` | 🔴 não confirmado | 🟡 |
| `google_calendar_tokens` | `user_id` | `profiles(id)` ou `auth.users(id)` | 🔴 não confirmado | 🟡 |
| `client_feedbacks` | `target_user_id` / `requested_by` | `profiles(id)` | 🔴 não confirmado | 🟡 |
| `client_feedback_answers` | `client_feedback_id` / `question_id` | família `client_*` | 🔴 não confirmado | 🟡 |
| `client_feedback_tags` | `client_feedback_id` / `tag_id` | família `client_*` | 🔴 não confirmado | 🟡 |

## Tabelas de junção (N:M)

| Junção | Liga | Unicidade | Fonte |
|--------|------|-----------|:---:|
| `profile_departments` | `profiles` ↔ `departments` | UNIQUE(profile_id, department_id) | 🟢 |
| `coordinator_members` | `profiles` (coordenador) ↔ `profiles` (membro) | UNIQUE(coordinator_id, member_id) | 🟢 |
| `client_feedback_tags` | `client_feedbacks` ↔ `client_feedback_service_tags` | 🔴 não confirmada | 🟡 |

## Unicidades de negócio (além das junções)

| Tabela | Constraint | Significado de negócio |
|--------|-----------|------------------------|
| `feedback_requests` | UNIQUE(cycle_id, giver_id, receiver_id) | uma pessoa avalia outra no máximo uma vez por ciclo |
| `feedback_answers` | UNIQUE(request_id, question_id) | uma resposta por pergunta por request |
| `feedback_permissions` | UNIQUE(reviewer_id, reviewee_id, permission_type, cycle_id) | permissão não duplicada por tipo/ciclo |
| `company_settings` | UNIQUE(key) | configuração chave-valor |
| `google_calendar_tokens` | UNIQUE(user_id) 🟡 | uma conexão Google por usuário (upsert `onConflict: user_id`) |
| `feedback_ai_analysis` | UNIQUE(person_id, cycle_id) 🟢 validado | um cache de IA por pessoa por ciclo |
| `feedback_ai_cycle_analysis` | UNIQUE(cycle_id, generated_by) 🟢 validado | um cache de IA de ciclo por gerador |

## Relacionamentos polimórficos

Não existem relacionamentos polimórficos formais. `audit_logs` usa o par (`table_name`, `record_id`) como referência genérica a qualquer tabela — polimorfismo fraco, sem constraint.

## Cascatas relevantes para o negócio

1. **Deletar usuário em `auth.users`** → apaga `profiles` (CASCADE) → apaga `profile_departments`, `feedback_permissions` e `free_feedbacks` como receiver (CASCADE); `free_feedbacks.giver_id` vira NULL. `feedback_requests` **bloqueia** a deleção (FK sem CASCADE) — por isso existe o fluxo de desativação (status) em vez de deleção.
2. **Deletar ciclo** → apaga `feedback_requests` (CASCADE), mas **as `feedback_answers` ficam órfãs** (sem FK). `feedback_permissions.cycle_id` vira NULL (a permissão sobrevive como permanente — efeito colateral possivelmente não intencional).
3. **Deletar formulário** → bloqueado se houver ciclos ou requests apontando (FKs sem CASCADE); perguntas caem junto (CASCADE).
