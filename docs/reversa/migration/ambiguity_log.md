# Ambiguity Log — Migração A&S Feedback Hub

> Consolidação de ambiguidades e pendências levantadas pelos agentes do Time de Migração.
> Estados: PENDENTE → RESOLVIDO COM DECISÃO HUMANA | REFERIDO À CODIFICAÇÃO.

## PENDENTES

_(nenhum — consolidação final em 2026-08-28, após o Inspector)_

## RESOLVIDOS COM DECISÃO HUMANA

> Recomendações do Curator aceitas integralmente pelo usuário (Uan) em 2026-08-28.

| ID | Descrição curta | Decisão registrada |
|---|---|---|
| AMB-001 | Retenção/anonimização de dados sensíveis | Default conservador no schema novo (anonimização de feedback anônimo por design, exportação só por admin) + definição formal com o cliente antes da homologação |
| AMB-002 | Fluxo público espontâneo (sem token) | Manter atrás de flag por tenant, com rate limiting |
| AMB-003 | Status `reviewed` de request | Omitir do modelo novo até haver caso de uso real |
| AMB-004 | Máquina de `team_requests` incompleta | Migrar só o confirmado (aprovação/rejeição); Designer fecha as transições faltantes |
| AMB-005 | Funções de IA sem contrato versionado | Adiar para pós-homologação; reimplementar como jobs no worker com contrato novo |
| AMB-006 | Política de retry/entrega de notificações | Retry exponencial + DLQ da fila; leitura permanece `read_at` |
| AMB-007 | Google Calendar | Adiar para fase 2 pós-homologação |

## REFERIDOS À CODIFICAÇÃO

> Itens que não exigem decisão humana agora: são ações e validações da fase de codificação/ensaios, com owner e referência. AMB-008/009 reclassificados de PENDENTES em 2026-08-28 (são pré-requisitos operacionais do cutover, já cobertos em `cutover_plan.md` § Pré-requisitos 3 e 4).

| ID | Descrição curta | Referência |
|---|---|---|
| AMB-008 | Inventariar jobs `pg_cron` do banco de produção e mapear para jobs do worker (pré-requisito do cutover) | `discard_log.md` § BR-DESCARTAR-003; `cutover_plan.md` § Pré-req. 3 |
| AMB-009 | Verificar exportabilidade dos hashes do Supabase Auth e testar migração de credenciais (pré-requisito do cutover) | `discard_log.md` § BR-DESCARTAR-005; `cutover_plan.md` § Pré-req. 4 |
| AMB-010 | Schema real das 12 tabelas sem DDL versionado — confirmar via `pg_dump` de produção | `data_migration_plan.md` § Lacunas |
| AMB-011 | Reconciliação `feedback_requests.response_data` (jsonb) vs `feedback_answers` — confirmar contra dados reais | `data_migration_plan.md` § Lacunas |
| AMB-012 | Valores reais de `feedback_cycles.status` em produção (DDL diz 2 estados, telas operam 5) | `data_migration_plan.md` § Lacunas |
| AMB-013 | Formato de export dos hashes do Supabase Auth (bcrypt esperado) — verificar cedo | `data_migration_plan.md` § Lacunas; R-07 |
