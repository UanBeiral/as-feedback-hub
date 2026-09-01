# Runbook — Fechar AMB-008, AMB-010 e AMB-013

> Passo a passo operacional para responder as três lacunas que o `handoff.md` manda atacar **cedo**.
> Destinatário: Uan (execução manual contra o Supabase de produção) + agente de codificação (consumo do resultado).
> Produzido em 2026-09-01. Não é artefato do pipeline de migração: é um guia de execução.

## Contexto apurado no repositório

| Achado | Consequência |
|---|---|
| `supabase/config.toml` → `project_id = pdipcjyuzlqwnnanpfsf`; projeto já linkado (`supabase/.temp/linked-project.json`) | não precisa descobrir o ref nem relinkar |
| Postgres de produção: **17.6.1.104**; GoTrue (Auth): **v2.193.0** | qualquer `pg_dump` precisa ser **≥ 17**, senão falha por incompatibilidade de versão |
| `pg_cron` e `pg_net` são criados em `supabase/migrations/20260407103459_*.sql`, mas **nenhum `cron.schedule(...)` está versionado** | confirma AMB-008: os agendamentos existem só dentro do banco, criados pelo SQL Editor |
| As 22 migrations versionadas criam **16 tabelas**; nenhuma cria `client_feedback_forms`, `client_feedback_questions`, `client_feedback_answers`, `client_feedback_service_tags`, `client_feedback_tags`, `feedback_ai_analysis`, `feedback_ai_cycle_analysis` ou `google_calendar_tokens` | confirma AMB-010: o módulo de avaliação de cliente inteiro está sem DDL versionado |
| `supabase`, `psql` e `pg_dump` **não estão instalados** nesta máquina | Passo 0.2 é obrigatório para o AMB-010 |

**Regra de higiene:** a senha do banco e a `service_role key` não entram em arquivo do repositório nem em mensagem de chat. Use variável de ambiente da sessão e limpe o histórico do shell se colar a URL inteira.

---

## Passo 0 — Acesso (uma vez, serve para os três)

### 0.1 Caminho rápido (resolve AMB-008 e AMB-013 sem instalar nada)

Dashboard do Supabase → projeto `pdipcjyuzlqwnnanpfsf` → **SQL Editor**. Todas as consultas dos Passos 1 e 2 rodam aí.

### 0.2 Caminho completo (necessário só para o `pg_dump` do Passo 3)

Pegue em **Project Settings → Database → Connection string** a URL do **Session pooler** (host `...pooler.supabase.com`, porta **5432**).

- Use o **session pooler**, não a conexão direta: `db.<ref>.supabase.co` é IPv6-only na maioria dos projetos e o Docker não alcança por padrão.
- **Não** use o transaction pooler (porta 6543): `pg_dump` não funciona nele.

```bash
export PGURL='postgresql://postgres.pdipcjyuzlqwnnanpfsf:<SENHA>@<host>.pooler.supabase.com:5432/postgres'
```

Ferramenta, escolha uma:

```bash
# Opção A — Docker (recomendada: garante pg_dump 17 sem instalar nada no Windows)
docker run --rm postgres:17 pg_dump --version

# Opção B — Supabase CLI (o projeto já está linkado)
#   Windows: scoop install supabase   |   npm i -g supabase
supabase --version
```

---

## Passo 1 — AMB-008: inventariar os jobs `pg_cron` (≈15 min)

**Pergunta a responder:** quais agendamentos rodam hoje dentro do banco, com que frequência, e o que cada um dispara?

Rode no SQL Editor, uma consulta por vez:

```sql
-- 1.1 Os jobs agendados. É ESTE o inventário que falta.
select jobid, jobname, schedule, command, nodename, database, username, active
from cron.job
order by jobid;
```

```sql
-- 1.2 Histórico recente: mostra o que realmente executa e o que falha em silêncio.
select jobid, status, return_message, start_time, end_time
from cron.job_run_details
order by start_time desc
limit 100;
```

```sql
-- 1.3 Taxa de falha por job nos últimos 30 dias.
select jobid,
       count(*) filter (where status = 'succeeded')  as ok,
       count(*) filter (where status <> 'succeeded') as falhas,
       max(start_time) as ultima_execucao
from cron.job_run_details
where start_time > now() - interval '30 days'
group by jobid
order by falhas desc;
```

```sql
-- 1.4 Triggers e funções do schema public — cron não é o único agendador possível.
select event_object_table, trigger_name, action_timing, event_manipulation
from information_schema.triggers
where trigger_schema = 'public'
order by event_object_table, trigger_name;

select p.proname, pg_get_function_identity_arguments(p.oid) as args
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
order by p.proname;
```

**Como ler o resultado:**

- O `command` de cada job normalmente é um `select net.http_post(...)` apontando para uma Edge Function. Anote **qual função** e **qual expressão cron**. O candidato óbvio é `auto-cycle-manager` (fechamento automático com carência de 3 dias — BR-MIGRAR-005), mas confirme contra a lista real; podem aparecer também `send-feedback-reminder` e `send-weekly-summary`.
- **Zero linhas em `cron.job` é uma resposta válida e boa**: significaria que o agendamento vive fora do banco (ex.: um cron externo chamando as Edge Functions) e o risco R-08 cai. Nesse caso, procure em Dashboard → Edge Functions → Schedules, e no resultado de 1.4, triggers que façam o trabalho.

**Feito quando:** existir uma tabela `job → schedule → alvo → job equivalente no worker` para cada linha de `cron.job`. Registre o resultado e mova AMB-008 no `ambiguity_log.md`.

---

## Passo 2 — AMB-013 / AMB-009: credenciais do Supabase Auth (≈30 min)

**Pergunta a responder:** os hashes de senha são exportáveis e reutilizáveis na auth própria (FastAPI), ou vai ser preciso redefinição em massa?

### 2.1 Inspecionar o formato (SQL Editor)

```sql
-- Formato e cost do hash, sem expor o hash inteiro.
select left(encrypted_password, 7) as prefixo, count(*)
from auth.users
group by 1
order by 2 desc;
```

Leitura do prefixo:

| Prefixo | Significado |
|---|---|
| `$2a$10$`, `$2b$10$`, `$2y$10$` | **bcrypt, cost 10** — cenário bom: reaproveitável direto em Python |
| `$argon2` | argon2 — também reaproveitável, mas exige `argon2-cffi` no alvo |
| vazio / `NULL` | usuário **sem senha** (só OAuth) — ver 2.2 |

```sql
-- 2.2 Quantos usuários realmente têm senha, e quantos entram só por provedor externo.
select count(*) as total,
       count(*) filter (where encrypted_password is not null and encrypted_password <> '') as com_senha,
       count(*) filter (where encrypted_password is null or encrypted_password = '')       as sem_senha,
       count(*) filter (where last_sign_in_at > now() - interval '90 days')                as ativos_90d
from auth.users;
```

```sql
-- 2.3 Provedores em uso. Se houver 'google', esses usuários precisam de plano próprio.
select provider, count(*) from auth.identities group by 1 order by 2 desc;
```

```sql
-- 2.4 Não confirmados / banidos / deletados — decidir se migram.
select count(*) filter (where email_confirmed_at is null) as nao_confirmados,
       count(*) filter (where banned_until is not null)   as banidos,
       count(*) filter (where deleted_at is not null)     as deletados
from auth.users;
```

> Se alguma consulta der erro de permissão, rode pelo SQL Editor (ele já usa o papel `postgres`). O schema `auth` pertence ao `supabase_auth_admin`, mas `postgres` tem leitura.

### 2.5 Provar que o hash valida em Python (o teste que fecha o item)

Crie um usuário descartável com senha conhecida — **não use o hash de um usuário real** neste teste:

```sql
select encrypted_password from auth.users where email = 'teste-migracao@exemplo.com';
```

```bash
pip install bcrypt
```

```python
import bcrypt
senha = b"a-senha-que-voce-definiu"
hash_ = b"$2a$10$...cole-aqui..."
print(bcrypt.checkpw(senha, hash_))   # precisa imprimir True
```

`True` aqui é a prova de que a auth própria aceita as senhas existentes sem redefinição. É o mesmo algoritmo que `passlib`/`pwdlib` usarão no FastAPI — o prefixo `$2a$` verifica normalmente.

### 2.6 Exportar (só depois do teste passar)

```sql
select id, email, encrypted_password, email_confirmed_at, created_at, last_sign_in_at,
       raw_user_meta_data
from auth.users
where deleted_at is null
order by created_at;
```

Trate o CSV como **material de credencial**: fora do repositório, apagado após o ensaio da migração.

**Feito quando:** você souber (a) o algoritmo, (b) quantos usuários têm senha reaproveitável, (c) quantos precisam de outro caminho (OAuth ou redefinição) e (d) o `checkpw` tiver retornado `True`. Se o resultado for "não reaproveitável", o plano de redefinição em massa entra **agora** no `cutover_plan.md`, não depois.

---

## Passo 3 — AMB-010 / 011 / 012: o schema real (≈1h)

**Pergunta a responder:** qual é o DDL verdadeiro das tabelas de produção, já que 8 tabelas do plano não têm `CREATE TABLE` versionado?

### 3.1 O dump do schema (fonte da verdade)

```bash
# Opção A — Docker
docker run --rm -v "$PWD:/out" postgres:17 \
  pg_dump --schema-only --no-owner --no-privileges \
  -n public -f /out/schema_prod.sql "$PGURL"

# Opção B — Supabase CLI (projeto já linkado, dispensa PGURL)
supabase db dump --linked -f schema_prod.sql
```

Guarde `schema_prod.sql` **fora** do repositório legado (ex.: no repositório novo, em `deploy/migrate/reference/`). Ele é o insumo nº 1 dos scripts de migração.

### 3.2 Conferir contra o plano

```sql
-- 3.2.1 Tabelas que existem de fato, com contagem estimada de linhas.
select c.relname as tabela, c.reltuples::bigint as linhas_estimadas
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by 1;
```

Compare com as 16 tabelas versionadas. **Toda tabela que aparecer aqui e não estiver nas migrations é dívida oculta** — em especial o bloco `client_feedback_*`, que o `target_data_model.md` renomeia para `client_eval_*`.

```sql
-- 3.2.2 Colunas reais das tabelas do mapeamento (procure colunas extras).
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;
```

```sql
-- 3.2.3 FKs físicas — o plano assume uuid órfão sem FK em alguns pontos. Confirme.
select tc.table_name, kcu.column_name, ccu.table_name as referencia
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu     on kcu.constraint_name = tc.constraint_name
join information_schema.constraint_column_usage ccu on ccu.constraint_name = tc.constraint_name
where tc.constraint_type = 'FOREIGN KEY' and tc.table_schema = 'public'
order by 1, 2;
```

### 3.3 AMB-012 — valores reais de `feedback_cycles.status`

O DDL documenta `open|closed`; as telas operam 5 estados. Quem manda são os dados:

```sql
select status, count(*), min(created_at) as primeiro, max(created_at) as ultimo
from feedback_cycles
group by status
order by 2 desc;
```

Todo valor que aparecer aqui e não couber no CHECK do modelo novo precisa de regra explícita de mapeamento **ou** vai para quarentena em `_migration_rejects`. Decida agora, não dentro do script.

### 3.4 AMB-011 — reconciliação `response_data` × `feedback_answers`

A regra do plano ("explodir o jsonb quando não houver linhas em answers") só vale se os dados confirmarem:

```sql
-- Quantos requests estão em cada situação?
select
  count(*) filter (where rd_ok and ans > 0)     as ambos,
  count(*) filter (where rd_ok and ans = 0)     as so_jsonb,
  count(*) filter (where not rd_ok and ans > 0) as so_answers,
  count(*) filter (where not rd_ok and ans = 0) as nenhum
from (
  select r.id,
         (r.response_data is not null and r.response_data::text not in ('null','{}','[]')) as rd_ok,
         (select count(*) from feedback_answers a where a.request_id = r.id) as ans
  from feedback_requests r
) t;
```

```sql
-- Amostra do formato do jsonb, para saber se dá para explodir em linhas.
select id, jsonb_pretty(response_data)
from feedback_requests
where response_data is not null and response_data::text not in ('null','{}','[]')
limit 3;
```

```sql
-- Divergência: os dois preenchidos com contagens diferentes = conflito real.
select r.id,
       jsonb_array_length(coalesce(r.response_data->'answers', '[]'::jsonb)) as no_jsonb,
       (select count(*) from feedback_answers a where a.request_id = r.id)   as em_answers
from feedback_requests r
where r.response_data is not null
limit 50;
```

> Ajuste o nome da FK (`request_id`) e a chave do jsonb (`answers`) conforme o que 3.2.2 e a amostra mostrarem — o plano infere esses nomes, o dump confirma.

**Feito quando:** `schema_prod.sql` existir e estiver guardado; a lista de tabelas não-versionadas estiver fechada; os valores de `status` estiverem enumerados com mapeamento decidido; e a regra de reconciliação estiver confirmada ou corrigida no `data_migration_plan.md`.

---

## Ordem sugerida

1. **Passo 1** (SQL Editor, 15 min) — barato e desbloqueia o design dos jobs do worker.
2. **Passo 2** (SQL Editor + teste local, 30 min) — maior consequência: se os hashes não servirem, muda o plano de comunicação com o cliente.
3. **Passo 3** (precisa do Passo 0.2, ~1h) — o mais longo, mas é pré-requisito de qualquer linha de script de migração.

## Ao terminar

Atualize `_reversa_sdd/migration/ambiguity_log.md` movendo AMB-008, AMB-010, AMB-011, AMB-012 e AMB-013 de "REFERIDOS À CODIFICAÇÃO" para uma seção "RESOLVIDOS NA APURAÇÃO", com a resposta encontrada. Riscos R-01, R-07 e R-08 do `risk_register.md` podem ser reavaliados na sequência.
