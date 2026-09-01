# Dicionário de Dados — Relatórios

## Escopo

Campos observados nas consultas e agregações do módulo `reports`. Tipos e obrigatoriedade refletem o uso no frontend; não substituem o schema ou as políticas do banco.

## Entidades

| Entidade | Campo | Tipo observado | Obrigatório | Confiança |
|---|---|---:|:---:|:---:|
| `feedback_requests` | `id` | string | sim | 🟢 CONFIRMADO |
| `feedback_requests` | `giver_id` / `receiver_id` / `cycle_id` | string | sim | 🟢 CONFIRMADO |
| `feedback_requests` | `status` | string | sim | 🟢 CONFIRMADO |
| `feedback_requests` | `due_date` | date ou nulo | não | 🟢 CONFIRMADO |
| `feedback_requests` | `submitted_at` | timestamp ou nulo | não | 🟢 CONFIRMADO |
| `feedback_answers` | `request_id` / `question_id` | string | sim | 🟢 CONFIRMADO |
| `feedback_answers` | `answer_score` / `answer_text` | number/string ou nulo | não | 🟢 CONFIRMADO |
| `client_feedbacks` | `id` / `client_name` | string | sim | 🟢 CONFIRMADO |
| `client_feedbacks` | `overall_rating` / `recommendation_rating` | number ou nulo | não | 🟢 CONFIRMADO |
| `client_feedbacks` | `has_negative` | boolean ou nulo | não | 🟢 CONFIRMADO |
| `client_feedbacks` | `contact_motivation` | enum/string ou nulo | não | 🟢 CONFIRMADO |
| `client_feedbacks` | `status` | string | sim | 🟢 CONFIRMADO |
| `client_feedbacks` | `created_at` / `submitted_at` | timestamp | `created_at`: sim | 🟢 CONFIRMADO |
| `free_feedbacks` | `giver_id` / `receiver_id` | string ou nulo | não confirmado | 🟢 CONFIRMADO |
| `free_feedbacks` | `positives` / `improvements` / `message` | string ou nulo | não | 🟢 CONFIRMADO |
| `free_feedbacks` | `is_anonymous` / `is_sensitive` | boolean | não confirmado | 🟢 CONFIRMADO |
| `feedback_ai_analysis` | `person_id` / `cycle_id` / `analysis` | string/string/JSON | sim | 🟡 INFERIDO |
| `feedback_ai_cycle_analysis` | `cycle_id` / `generated_by` / `analysis` | string/string/JSON | sim | 🟡 INFERIDO |
| `feedback_ai_cycle_analysis` | `member_count` | number | não | 🟡 INFERIDO |

## Valores de domínio

- `feedback_requests.status`: `pending`, `draft`, `submitted`, `expired`, `waived`, `cancelled`, `reviewed`.
- `client_feedbacks.status`: `submitted` representa avaliação respondida; outros estados são exibidos como aguardando ou em andamento.
- `contact_motivation`: `praise`, `evaluate`, `problem`, `other`.
- Escopo do PDF: `individual_complete`, `individual_specific`, `cycle_general`.

🔴 **LACUNA:** o schema SQL definitivo e as restrições de nulidade não foram confirmados para as tabelas de cache de IA.

## Validação humana — 2026-08-25

- 🟢 `feedback_ai_analysis` tem unicidade `(person_id, cycle_id)` e FKs para `profiles` e `feedback_cycles`.
- 🟢 `feedback_ai_cycle_analysis` tem unicidade `(cycle_id, generated_by)` e FKs para `feedback_cycles` e `profiles`.
- 🔴 As colunas não-chave, nulabilidade e as migrations ainda não estão no repositório; o schema deve ser fechado por consulta ao banco de produção.
