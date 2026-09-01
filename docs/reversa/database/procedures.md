# Stored Procedures e Funções

> Gerado pelo **Data Master** (Reversa) em 2026-08-28.
> Não há stored procedures de negócio (o processamento pesado vive em edge functions Deno). O banco tem 5 funções, todas `SECURITY DEFINER` com `search_path = public`.

## 1. `handle_new_user()` 🟢

| Aspecto | Detalhe |
|---------|---------|
| Tipo | trigger function (plpgsql) |
| Disparo | AFTER INSERT em `auth.users` (trigger `on_auth_user_created`) |
| Lógica | `INSERT INTO profiles (id, email, full_name)` usando `raw_user_meta_data->>'full_name'` (string vazia se ausente) |
| Retorno | `NEW` |
| Por que DEFINER | precisa escrever em `profiles` num contexto sem sessão de usuário |

## 2. `is_admin(uid uuid) → boolean` 🟢

| Aspecto | Detalhe |
|---------|---------|
| Tipo | SQL, STABLE |
| Lógica | existe `profiles` com `id = uid` e `role = 'admin'` |
| Uso | predicado das políticas RLS de gestão (forms, ciclos, permissions, requests, free_feedbacks, platform_updates) |
| Por que DEFINER | evita recursão de RLS ao consultar `profiles` de dentro de uma política sobre `profiles` |

## 3. `is_admin_or_rh(uid uuid) → boolean` 🟢

| Aspecto | Detalhe |
|---------|---------|
| Tipo | SQL, STABLE |
| Lógica | existe `profiles` com `id = uid` e `role IN ('admin', 'rh')` |
| Uso | políticas de `coordinator_members`, `team_requests`, `feedback_contacts`, `company_settings` e bucket `company-assets` |

## 4. `cancel_requests_on_profile_deactivation()` 🟢

| Aspecto | Detalhe |
|---------|---------|
| Tipo | trigger function (plpgsql) |
| Disparo | AFTER UPDATE OF `status` em `profiles`, WHEN status mudou (trigger `trg_cancel_requests_on_profile_deactivation`) |
| Condição interna | `OLD.status = 'active' AND NEW.status <> 'active'` |
| Lógica | `UPDATE feedback_requests SET status = 'cancelled'` para requests `pending`/`draft` em ciclos `open` onde a pessoa é giver ou receiver |
| Retorno | `NEW` |
| Por que DEFINER | obrigatório: com INVOKER o RLS bloquearia o update em requests de outros usuários (dois bugs anteriores no projeto) |

## 5. `can_insert_public_client_feedback_details(p_feedback_id uuid) → boolean` 🟢

| Aspecto | Detalhe |
|---------|---------|
| Tipo | SQL, STABLE; `GRANT EXECUTE TO anon` |
| Lógica | o `client_feedbacks` pai tem `token` não nulo, `status = 'submitted'`, `submitted_at` preenchido e **≤ 15 minutos atrás** |
| Uso | WITH CHECK das políticas de INSERT anon em `client_feedback_answers` e `client_feedback_tags` |
| Regra | janela curta pós-submissão para o cliente anônimo anexar respostas/tags; bloqueia inserções tardias |

## Views e materialized views

Nenhuma view no schema `public` (confirmado por `Views: {}` nos tipos gerados 🟢).

## Lacunas 🔴

- Se existirem funções criadas via dashboard depois da geração do types.ts (mesmo caso das tabelas `client_*`), elas não aparecem aqui. Os tipos listam apenas `is_admin` e `is_admin_or_rh` como RPC expostas; `handle_new_user`, `cancel_requests_on_profile_deactivation` e `can_insert_public_client_feedback_details` são internas (trigger/policy) e estão confirmadas por migration.
- Jobs `pg_cron` que possivelmente invocam edge functions via `pg_net` não estão versionados.
