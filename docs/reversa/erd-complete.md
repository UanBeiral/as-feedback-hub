# ERD Completo

```mermaid
erDiagram
    PROFILES ||--o{ FEEDBACK_REQUESTS : gives
    PROFILES ||--o{ FEEDBACK_REQUESTS : receives
    FEEDBACK_CYCLES ||--o{ FEEDBACK_REQUESTS : contains
    FEEDBACK_REQUESTS ||--o{ FEEDBACK_ANSWERS : has
    FEEDBACK_FORMS ||--o{ FEEDBACK_CYCLES : configures
    FEEDBACK_FORMS ||--o{ FEEDBACK_FORM_QUESTIONS : defines
    PROFILES ||--o{ FEEDBACK_PERMISSIONS : reviewer
    PROFILES ||--o{ FEEDBACK_PERMISSIONS : reviewee
    PROFILES ||--o{ CLIENT_FEEDBACKS : target
    CLIENT_FEEDBACK_FORMS ||--o{ CLIENT_FEEDBACK_FORM_QUESTIONS : defines
    CLIENT_FEEDBACK_FORMS ||--o{ CLIENT_FEEDBACKS : used_by
    PROFILES ||--o{ FREE_FEEDBACKS : giver
    PROFILES ||--o{ FREE_FEEDBACKS : receiver
    PROFILES ||--o{ NOTIFICATIONS : receives
    PROFILES ||--o{ AUDIT_LOGS : acts
    DEPARTMENTS ||--o{ PROFILES : groups
    PROFILES ||--o{ COORDINATOR_MEMBERS : coordinator
    PROFILES ||--o{ COORDINATOR_MEMBERS : member
    PROFILES ||--o{ COMPANY_SETTINGS : updates

    PROFILES { string id PK string role string status string department_id FK string manager_id FK boolean is_coordinator }
    FEEDBACK_CYCLES { string id PK string status string form_id FK date start_date date end_date }
    FEEDBACK_REQUESTS { string id PK string cycle_id FK string giver_id FK string receiver_id FK string status date due_date timestamp submitted_at }
    FEEDBACK_ANSWERS { string id PK string request_id FK string question_id FK number answer_score string answer_text }
    FEEDBACK_PERMISSIONS { string id PK string reviewer_id FK string reviewee_id FK string permission_type boolean active }
    CLIENT_FEEDBACKS { string id PK string target_user_id FK string form_id FK string status number overall_rating timestamp submitted_at }
    FREE_FEEDBACKS { string id PK string giver_id FK string receiver_id FK boolean is_anonymous boolean is_sensitive }
    DEPARTMENTS { string id PK string name }
    NOTIFICATIONS { string id PK string user_id FK string type string link }
    AUDIT_LOGS { string id PK string actor_id FK string action string record_id }
    COMPANY_SETTINGS { string key PK string value }
}
```

🟢 Entidades e relações principais são confirmadas por queries e tipos. Cardinalidades e algumas chaves de tabelas secundárias são 🟡 **INFERIDAS**; devem ser confirmadas nas migrations.
