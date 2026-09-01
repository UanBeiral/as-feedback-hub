# ERD Completo — Banco de Dados

> Gerado pelo **Data Master** (Reversa) em 2026-08-28.
> ERD geral simplificado + ERDs parciais por domínio. Entidades 🟡 têm estrutura inferida do código (ver `data-dictionary.md`).

## ERD geral (simplificado)

```mermaid
erDiagram
    PROFILES ||--o{ FEEDBACK_REQUESTS : "dá/recebe"
    PROFILES ||--o{ FEEDBACK_PERMISSIONS : "avalia/é avaliado"
    PROFILES ||--o{ FREE_FEEDBACKS : "dá/recebe"
    PROFILES ||--o{ CLIENT_FEEDBACKS : "é avaliado por cliente"
    PROFILES ||--o{ CYCLE_NOTES : "anota/é anotado"
    PROFILES ||--o{ NOTIFICATIONS : recebe
    PROFILES ||--o{ DAILY_APPOINTMENTS : "tem agenda"
    PROFILES ||--o| GOOGLE_CALENDAR_TOKENS : conecta
    DEPARTMENTS ||--o{ PROFILES : agrupa
    PROFILES }o--o{ DEPARTMENTS : "N:M via profile_departments"
    PROFILES }o--o{ PROFILES : "coordenador N:M via coordinator_members"
    FEEDBACK_FORMS ||--o{ FEEDBACK_CYCLES : configura
    FEEDBACK_CYCLES ||--o{ FEEDBACK_REQUESTS : contém
    FEEDBACK_REQUESTS ||--o{ FEEDBACK_ANSWERS : tem
    CLIENT_FEEDBACK_FORMS ||--o{ CLIENT_FEEDBACKS : usa
    CLIENT_FEEDBACKS ||--o{ CLIENT_FEEDBACK_ANSWERS : tem
    CLIENT_FEEDBACKS }o--o{ CLIENT_FEEDBACK_SERVICE_TAGS : "N:M via client_feedback_tags"
```

## Domínio: Identidade & Organização

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : "espelha (trigger)"
    DEPARTMENTS ||--o{ PROFILES : "department_id"
    PROFILES ||--o{ PROFILES : "manager_id (auto-ref)"
    PROFILES ||--o{ PROFILE_DEPARTMENTS : ""
    DEPARTMENTS ||--o{ PROFILE_DEPARTMENTS : ""
    PROFILES ||--o{ COORDINATOR_MEMBERS : "coordinator_id"
    PROFILES ||--o{ COORDINATOR_MEMBERS : "member_id"
    PROFILES ||--o{ TEAM_REQUESTS : "requester_id"
    PROFILES ||--o{ TEAM_REQUESTS : "requested_member_id"

    PROFILES {
        uuid id PK
        text full_name
        text email
        text role "admin|rh|gestor|colaborador"
        uuid department_id FK
        uuid manager_id FK
        text status "active|inactive|deleted"
        boolean is_coordinator
        text whatsapp
    }
    DEPARTMENTS {
        uuid id PK
        text name
    }
    PROFILE_DEPARTMENTS {
        uuid id PK
        uuid profile_id FK
        uuid department_id FK
    }
    COORDINATOR_MEMBERS {
        uuid id PK
        uuid coordinator_id "sem FK"
        uuid member_id "sem FK"
    }
    TEAM_REQUESTS {
        uuid id PK
        uuid requester_id "sem FK"
        uuid requested_member_id "sem FK"
        text status "pending|approved|rejected"
        uuid approved_by
        text rejection_reason
    }
```

## Domínio: Feedback interno (ciclos 360)

```mermaid
erDiagram
    FEEDBACK_FORMS ||--o{ FEEDBACK_FORM_QUESTIONS : define
    FEEDBACK_FORMS ||--o{ FEEDBACK_CYCLES : configura
    FEEDBACK_CYCLES ||--o{ FEEDBACK_PERMISSIONS : "escopo opcional"
    FEEDBACK_CYCLES ||--o{ FEEDBACK_REQUESTS : contém
    FEEDBACK_CYCLES ||--o{ CYCLE_NOTES : contexto
    FEEDBACK_CYCLES ||--o{ FEEDBACK_AI_ANALYSIS : "cache IA pessoa"
    FEEDBACK_CYCLES ||--o{ FEEDBACK_AI_CYCLE_ANALYSIS : "cache IA ciclo"
    PROFILES ||--o{ FEEDBACK_PERMISSIONS : "reviewer/reviewee"
    PROFILES ||--o{ FEEDBACK_REQUESTS : "giver/receiver"
    PROFILES ||--o{ CYCLE_NOTES : "author/about"
    PROFILES ||--o{ FEEDBACK_AI_ANALYSIS : person
    FEEDBACK_REQUESTS ||--o{ FEEDBACK_ANSWERS : "tem (sem FK física)"
    FEEDBACK_FORM_QUESTIONS ||--o{ FEEDBACK_ANSWERS : "responde (sem FK física)"

    FEEDBACK_CYCLES {
        uuid id PK
        text name
        date start_date
        date end_date
        text status "open|closed"
        uuid form_id FK
        date evaluated_start "override manual"
        date evaluated_end "override manual"
    }
    FEEDBACK_FORM_QUESTIONS {
        uuid id PK
        uuid form_id FK
        text question_text
        text question_type "rating|textarea"
        int sort_order
        boolean required
    }
    FEEDBACK_PERMISSIONS {
        uuid id PK
        uuid reviewer_id FK
        uuid reviewee_id FK
        text permission_type "peer|manager|subordinate|self"
        uuid cycle_id FK "NULL = permanente"
        boolean active
    }
    FEEDBACK_REQUESTS {
        uuid id PK
        uuid cycle_id FK
        uuid form_id FK
        uuid giver_id FK
        uuid receiver_id FK
        text status "pending|draft|submitted|expired|waived|cancelled|reviewed"
        date due_date
        timestamptz submitted_at
        jsonb response_data
        timestamptz read_at
        uuid read_by
    }
    FEEDBACK_ANSWERS {
        uuid id PK
        uuid request_id "sem FK"
        uuid question_id "sem FK"
        text answer_text
        int answer_score
    }
    CYCLE_NOTES {
        uuid id PK
        uuid cycle_id FK
        uuid author_id FK
        uuid about_user_id FK
        text content
        boolean is_audio_transcription
    }
    FEEDBACK_AI_ANALYSIS {
        uuid person_id FK "UNIQUE(person_id,cycle_id)"
        uuid cycle_id FK
        jsonb analysis
    }
    FEEDBACK_AI_CYCLE_ANALYSIS {
        uuid cycle_id FK "UNIQUE(cycle_id,generated_by)"
        uuid generated_by FK
        jsonb analysis
        int member_count
    }
```

## Domínio: Feedback livre

```mermaid
erDiagram
    PROFILES ||--o{ FREE_FEEDBACKS : "giver (NULL se anônimo)"
    PROFILES ||--o{ FREE_FEEDBACKS : receiver
    PROFILES ||--o{ FREE_FEEDBACKS : read_by

    FREE_FEEDBACKS {
        uuid id PK
        uuid giver_id FK "SET NULL"
        uuid receiver_id FK "CASCADE"
        boolean is_anonymous
        boolean is_sensitive "sensível: só gestão vê"
        text positives
        text improvements
        text message
        timestamptz read_at
        uuid read_by FK
    }
```

## Domínio: Feedback de clientes (fluxo público) 🟡

```mermaid
erDiagram
    CLIENT_FEEDBACK_FORMS ||--o{ CLIENT_FEEDBACK_FORM_QUESTIONS : define
    CLIENT_FEEDBACK_FORMS ||--o{ CLIENT_FEEDBACKS : usa
    PROFILES ||--o{ CLIENT_FEEDBACKS : "target_user_id"
    PROFILES ||--o{ CLIENT_FEEDBACKS : "requested_by"
    CLIENT_FEEDBACKS ||--o{ CLIENT_FEEDBACK_ANSWERS : tem
    CLIENT_FEEDBACK_FORM_QUESTIONS ||--o{ CLIENT_FEEDBACK_ANSWERS : responde
    CLIENT_FEEDBACKS ||--o{ CLIENT_FEEDBACK_TAGS : ""
    CLIENT_FEEDBACK_SERVICE_TAGS ||--o{ CLIENT_FEEDBACK_TAGS : ""

    CLIENT_FEEDBACKS {
        uuid id PK
        text client_name
        text client_whatsapp
        text client_email
        uuid target_user_id FK
        uuid form_id FK
        text flow_type "requested|spontaneous"
        uuid requested_by FK
        text token "link público"
        timestamptz token_expires_at
        text contact_motivation "praise|evaluate|problem|other"
        int overall_rating
        int recommendation_rating
        boolean has_negative
        text status "pending|in_progress|submitted"
        timestamptz submitted_at
        jsonb tracking_data
    }
    CLIENT_FEEDBACK_FORM_QUESTIONS {
        uuid id PK
        uuid form_id FK
        text question_text
        text question_type "rating|text|textarea|yes_no|nps|multiple_choice"
        boolean is_required
        int display_order
        text placeholder
    }
    CLIENT_FEEDBACK_ANSWERS {
        uuid id PK
        uuid client_feedback_id FK
        uuid question_id FK
        int rating_value
        text text_value
    }
    CLIENT_FEEDBACK_SERVICE_TAGS {
        uuid id PK
        text name
        boolean is_active
        int display_order
    }
    CLIENT_FEEDBACK_TAGS {
        uuid client_feedback_id FK
        uuid tag_id FK
    }
```

## Domínio: Agenda & Plataforma 🟡

```mermaid
erDiagram
    PROFILES ||--o| GOOGLE_CALENDAR_TOKENS : "1:1 (UNIQUE user_id)"
    PROFILES ||--o{ DAILY_APPOINTMENTS : "agenda do dia"
    PROFILES ||--o{ NOTIFICATIONS : recebe
    PROFILES ||--o{ PLATFORM_UPDATES : publica
    PROFILES ||--o{ FEEDBACK_CONTACTS : envia
    AUTH_USERS ||--o{ AUDIT_LOGS : registra

    GOOGLE_CALENDAR_TOKENS {
        uuid user_id UK
        text access_token
        text refresh_token
        timestamptz expires_at
    }
    DAILY_APPOINTMENTS {
        uuid id PK
        uuid user_id
        date event_date
        text event_time
        text event_title
        text client_name
        text google_event_id
        boolean feedback_requested
        uuid verified_by
        timestamptz verified_at
    }
    NOTIFICATIONS {
        uuid id PK
        uuid user_id
        text type
        text title
        text message
        text link
        timestamptz read_at
    }
    PLATFORM_UPDATES {
        uuid id PK
        text title
        text content
        uuid created_by FK
        int notified_count
        boolean draft
    }
    FEEDBACK_CONTACTS {
        uuid id PK
        text type
        text contact_name
        text email
        text message
        text status
        uuid created_by "sem FK"
    }
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK "auth.users SET NULL"
        text action
        text table_name
        uuid record_id
        jsonb details
    }
    COMPANY_SETTINGS {
        uuid id PK
        text key UK
        text value
    }
```

🟢 Domínios de identidade, feedback interno, feedback livre e plataforma confirmados por migrations. 🟡 Domínios de clientes e agenda inferidos do código; a marcação "sem FK" indica coluna uuid sem constraint física confirmada.
