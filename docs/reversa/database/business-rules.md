# Regras de Negócio no Banco de Dados

> Gerado pelo **Data Master** (Reversa) em 2026-08-28.
> Regras implementadas na camada do banco (triggers, funções, constraints, RLS). Complementa `_reversa_sdd/permissions.md` e `_reversa_sdd/state-machines.md`.

## Triggers

### 1. `on_auth_user_created` → `handle_new_user()` 🟢

- **Evento:** AFTER INSERT em `auth.users`
- **Ação:** cria automaticamente a linha em `public.profiles` com `id`, `email` e `full_name` (de `raw_user_meta_data`)
- **Regra:** todo usuário autenticável tem perfil desde o signup; o papel nasce como `colaborador` (default da coluna)

### 2. `trg_cancel_requests_on_profile_deactivation` → `cancel_requests_on_profile_deactivation()` 🟢

- **Evento:** AFTER UPDATE OF `status` em `profiles`, quando o status muda
- **Condição:** `OLD.status = 'active'` e `NEW.status <> 'active'` (desativação ou deleção lógica)
- **Ação:** cancela (`status = 'cancelled'`) todos os `feedback_requests` em `pending`/`draft` de ciclos **abertos** em que a pessoa participa como giver **ou** receiver
- **Regra de negócio:** pessoa desativada sai imediatamente do ciclo corrente, sem deixar pendências fantasma; requests já `submitted` são preservados (histórico intocado)
- **Nota de projeto:** a função é `SECURITY DEFINER` deliberadamente — com SECURITY INVOKER o RLS bloquearia o update em requests de terceiros (dois bugs anteriores documentados no comentário da migration)

## Check constraints com lógica de negócio

| Tabela | Constraint | Regra |
|--------|-----------|-------|
| `profiles` | `profiles_status_check` | `status IN ('active', 'inactive', 'deleted')` — deleção de usuário é lógica, nunca física 🟢 |

## Funções com regra de negócio

### `can_insert_public_client_feedback_details(p_feedback_id)` 🟢

Portão do fluxo público de avaliação de cliente. Permite que o papel `anon` insira respostas e tags **somente** quando o `client_feedback` pai:

1. tem `token` não nulo (nasceu do fluxo "solicitado por link");
2. está com `status = 'submitted'` e `submitted_at` preenchido;
3. foi submetido **há no máximo 15 minutos**.

**Regra:** a janela de 15 minutos limita o tempo em que um anônimo pode anexar linhas-filhas a uma avaliação, impedindo inserções tardias em avaliações antigas com token vazado.

### `is_admin(uid)` / `is_admin_or_rh(uid)` 🟢

Predicados `SECURITY DEFINER` usados nas políticas RLS (evitam recursão de RLS sobre `profiles`). Definem os dois níveis administrativos: `admin` e `admin ∪ rh`.

## Grants de coluna ao papel `anon` 🟢

O `anon` **não** tem UPDATE irrestrito em `client_feedbacks`: o grant é por coluna, limitado a
`client_name, client_whatsapp, client_email, contact_motivation, contact_motivation_text, overall_rating, recommendation_rating, has_negative, status, submitted_at, tracking_data`.
Colunas de controle (`token`, `token_expires_at`, `target_user_id`, `form_id`, `flow_type`, `requested_by`) ficam fora do alcance do cliente anônimo. Também há grant de INSERT ao `anon` em `client_feedback_answers` e `client_feedback_tags` (filtrado pela função acima via RLS).

## Políticas RLS por tabela (resumo de negócio)

### Identidade

| Tabela | Regra efetiva |
|--------|--------------|
| `profiles` | todos autenticados veem todos os perfis; cada um edita o próprio; admin edita/insere/deleta qualquer um |
| `departments` | leitura para autenticados; gestão total só admin |
| `profile_departments` | leitura para autenticados; gestão só admin |
| `coordinator_members` | coordenador vê os próprios membros; admin/rh vê e gerencia tudo |
| `team_requests` | solicitante vê as próprias; gestor vê todas (para aprovar); admin/rh gerencia; qualquer autenticado insere como ele mesmo |

### Feedback interno

| Tabela | Regra efetiva |
|--------|--------------|
| `feedback_forms` / `feedback_form_questions` / `feedback_cycles` | leitura para autenticados; gestão só admin |
| `feedback_permissions` | leitura para autenticados (a matriz de quem-avalia-quem é pública internamente); gestão só admin |
| `feedback_requests` | giver e receiver veem os próprios; giver atualiza (responder); **receiver também pode UPDATE** (política "Receiver can mark as read" — sem restrição de coluna, receiver tecnicamente pode alterar qualquer campo do request ⚠️); admin gerencia tudo |
| `feedback_answers` | giver gerencia as próprias respostas; giver e receiver leem; admin tudo |
| `cycle_notes` | 🔴 políticas não estão no repositório (tabela criada via dashboard) |
| `feedback_ai_analysis` / `feedback_ai_cycle_analysis` | 🔴 políticas não estão no repositório |

### Feedback livre (`free_feedbacks`)

- Qualquer autenticado insere (WITH CHECK `true` — permite `giver_id` de terceiros, viabilizando o anonimato ⚠️).
- Receiver vê apenas os **não sensíveis** endereçados a ele.
- Gestor direto (`manager_id`) e coordenador (via `coordinator_members`) veem os feedbacks do time — **inclusive os sensíveis**.
- Receiver marca como lido; gestores/coordenadores também podem atualizar os do time; admin gerencia tudo.
- **Regra central:** `is_sensitive = true` esconde o feedback do próprio receiver; só a cadeia de gestão vê.

### Feedback de clientes (fluxo público)

- `anon` pode UPDATE em `client_feedbacks` **apenas** de linhas com `token` válido, `status = 'pending'` e `token_expires_at > now()`; o WITH CHECK força a transição para `status = 'submitted'` com `submitted_at` preenchido — ou seja, o único movimento permitido ao cliente é **submeter**. 🟢
- `anon` insere respostas/tags só dentro da janela de 15 min pós-submissão (função-portão). 🟢
- Fluxo espontâneo (INSERT anon em `client_feedbacks`, SELECT anon em formulários/perguntas/tags/perfis ativos): 🔴 políticas não estão no repositório, mas o código exige que existam.

### Plataforma

| Tabela | Regra efetiva |
|--------|--------------|
| `company_settings` | leitura para autenticados; gestão admin/rh; 🟡 leitura anon da chave `client_feedback_motivations` é usada pelo fluxo público (política não presente no repo) |
| `feedback_contacts` | autenticado insere como ele mesmo; vê os próprios; admin/rh vê e atualiza todos |
| `audit_logs` | qualquer autenticado insere (política aberta ⚠️) e **qualquer autenticado lê tudo** ⚠️ — trilha de auditoria visível a todos os funcionários |
| `platform_updates` | publicados visíveis a todos autenticados; rascunhos (`draft = true`) só autor e admins; escrita só admin |
| `notifications` | 🔴 políticas não estão no repositório; o código insere via `anon` (página pública) e via service role (functions), e o usuário lê/atualiza as próprias |
| `storage.objects` (bucket `company-assets`) | leitura pública; escrita/edição/deleção admin/rh |

## Regras de dados semânticas (documentadas em comments)

- `feedback_cycles.evaluated_start/evaluated_end` 🟢: quando NULL, o período avaliado exibido é o **mês-calendário anterior ao `start_date`** (regra automática `getEvaluatedPeriod` do app); quando preenchidos, funcionam como override manual — usados por ciclos de extensão (ex.: "Extensão Ciclo Junho").
- `platform_updates.notified_count` 🟢: número de emails enviados com sucesso no momento da publicação.
- `platform_updates.draft` 🟢: rascunho auto-salvo; publicar = `draft := false` (só então dispara notificação).

## Automação agendada

- Extensões `pg_cron` e `pg_net` habilitadas 🟢 — o banco dispara chamadas HTTP agendadas para edge functions (`auto-cycle-manager`, `google-calendar-sync` etc.).
- 🔴 **LACUNA:** as definições dos jobs (`cron.schedule(...)`) não constam de nenhuma migration; estão só no banco de produção.

## Scripts operacionais ad-hoc (fora de migration)

| Script | Propósito |
|--------|-----------|
| `cleanup-requests-usuarios-inativos.sql` | Limpeza manual retroativa: cancela requests `pending`/`draft` de ciclos abertos com giver/receiver inativo (a regra virou o trigger da migration `20260716120000`) |
| `supabase/fix_extensao_ciclo_junho_evaluated_period.sql` | Correção pontual: grava `evaluated_start/end` no ciclo "Extensão Ciclo Junho" replicando o período do ciclo de referência |

## Pontos de atenção (⚠️ achados do Data Master)

1. **`audit_logs` legível e gravável por qualquer autenticado** — não é uma trilha de auditoria confiável nem confidencial.
2. **Política "Receiver can mark as read" em `feedback_requests` sem restrição de coluna** — receiver pode, em teoria, alterar `response_data`/`status` de um request que recebeu.
3. **`feedback_answers` sem FK física** — deletar ciclo/requests deixa respostas órfãs.
4. **Tokens OAuth do Google em texto claro** em `google_calendar_tokens` (padrão comum em Supabase, mas sensível).
5. **`feedback_permissions.cycle_id ON DELETE SET NULL`** — deletar um ciclo transforma permissões escopadas em permanentes silenciosamente.
