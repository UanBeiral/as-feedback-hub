# Desvios em relação às specs de migração

> As specs de `docs/reversa/migration/` são a fonte da verdade. Este arquivo registra os
> pontos em que o código **não** as segue ao pé da letra, com o motivo — para que ninguém
> "conserte" um desvio deliberado de volta, e para que a spec seja corrigida na próxima
> revisão.
>
> Origem: revisão do gate R-06 (contexto de referência `identity`), 2026-09-01.

## DEV-A01 — `profiles.job_title` existe, apesar de ausente no DDL da spec

- **Spec**: `target_data_model.md` § DDL não lista a coluna em `profiles`.
- **Código**: `profiles.job_title text` (migration `0001`, `identity/models.py`).
- **Motivo**: "Cargo" é coluna visível em quatro telas do subset **literal** —
  tabela de usuários do admin, Minha Equipe (gestor e coordenador), Meu Perfil e a busca
  de Solicitar Avaliação (`docs/reversa/*/screens.md`). O legado tem `profiles.job_title`
  (`docs/reversa/database/data-dictionary.md`), e o `discard_log.md` não registra
  descarte. Sem a coluna, o dado morre no cutover e quatro telas perdem paridade.
- **Ação na spec**: incluir `job_title text` no DDL de `profiles`.

## DEV-A02 — `profiles.hired_at` foi removida

- **Spec**: não existe.
- **Código**: existia na primeira versão da fundação; foi removida.
- **Motivo**: não aparece no DDL alvo, nem no dicionário do legado, nem em tela alguma.
  Coluna sem origem.
- **Ação na spec**: nenhuma.

## DEV-A03 — `profiles.id = users.id` virou invariante do banco

- **Spec**: `target_data_model.md` diz `id uuid PRIMARY KEY -- = users.id (1:1)`;
  `data_migration_plan.md` § Princípios 4 exige UUIDs preservados do legado (onde
  `profiles.id` **é** o `auth.users.id`).
- **Código**: `profiles.id` sem default, `CHECK (id = user_id)`, e `Profile.for_user()`
  como construtor.
- **Motivo**: a versão anterior gerava uuid novo na aplicação. Isso produziria uma base
  meio a meio — linhas migradas com `profile.id == user.id`, linhas criadas pelo app
  sem — e todo FK para `profiles(id)` nos outros contextos herdaria a inconsistência.
  O CHECK cobra a promessa de ETL e aplicação por igual.
- **Ação na spec**: nenhuma; o código passou a seguir a spec.

## DEV-A04 — a sessão é revalidada contra o banco a cada requisição

- **Spec**: AD-03 define JWT curto (15 min) com papel e flags nas claims.
- **Código**: `core/tenancy.assert_session_active` consulta `users`/`profiles`/`tenants`
  em toda requisição autenticada; papel e flags continuam vindo do token.
- **Motivo**: PAR-08 § "Acesso revogado imediatamente" é `@critico`, e o handoff trata
  cenário `@critico` como bloqueador de cutover. Sem a consulta, um usuário
  soft-deletado continuaria trabalhando por até 15 minutos.
- **Custo aceito**: uma leitura indexada por requisição. Se um dia incomodar, o
  substituto natural é uma denylist em Redis com TTL igual ao do access token — não
  remover a checagem.
- **Ação na spec**: registrar em AD-03 que revogação de **acesso** é imediata, enquanto
  papel e flags têm janela de 15 minutos.

## DEV-A05 — o IP do cliente vem de `X-Real-IP`, não de `X-Forwarded-For`

- **Spec**: AD-06 fala em Nginx à frente da API; não especifica o header.
- **Código**: `core/di.client_ip` lê `X-Real-IP`.
- **Motivo**: o Nginx usa `$proxy_add_x_forwarded_for`, que **anexa** o endereço da
  conexão ao valor mandado pelo cliente — o primeiro elemento do XFF é escrito por quem
  está do outro lado. `X-Real-IP` é sobrescrito a cada salto do nosso proxy.
- **Ação na spec**: nenhuma.

## DEV-A06 — `outbox_messages.last_error`

- **Spec**: `target_data_model.md` § DDL não lista a coluna.
- **Código**: `last_error text` (migration `0002`), preenchida por `OutboxService.mark_failed`.
- **Motivo**: uma DLQ sem o motivo da morte não é operável. Quando alguém for investigar
  por que quatro mensagens estão em `dead`, a alternativa sem esta coluna é correlacionar
  log de aplicação por horário — que é exatamente o tipo de arqueologia que a migração
  existe para não repetir.
- **Ação na spec**: incluir a coluna no DDL de `outbox_messages`.

## DEV-A07 — auditoria é gravada na transação do comando, não via outbox

- **Spec**: `target_domain_model.md` § AuditLog diz "gravado via outbox pós-commit";
  BR-MIGRAR-026 idem.
- **Código**: `AuditService.record` insere em `audit_logs` na mesma transação; só a
  *notificação* dos envolvidos vira mensagem de outbox.
- **Motivo**: a mensagem de outbox seria igualmente um `INSERT` na mesma transação, com
  o mesmo perfil de falha — o outbox não protege contra nada aqui. O que ele protege é a
  chamada externa (email, push), e essa continua no outbox. Em troca, a tela de Auditoria
  mostra a ação no instante em que ela acontece, sem depender de o worker estar de pé, e
  não existe janela em que a ação já aconteceu mas a trilha ainda não registra.
- **Risco aceito**: se o `INSERT` em `audit_logs` falhar (ex.: constraint violada por
  bug), a operação principal cai junto. Como a inserção não tem constraint além das FKs,
  o cenário é hipotético — e falhar alto é preferível a auditar errado.
- **Ação na spec**: registrar a escolha em BR-MIGRAR-026, mantendo o outbox para a parte
  de notificação.

## DEV-A08 — o pacote do worker se chama `worker`, não `app`

- **Spec**: `target_architecture.md` § Honra à topologia desenha
  `apps/worker/app/{consumers,scheduler,jobs}/`.
- **Código**: `apps/worker/worker/{consumers,scheduler,jobs}/`.
- **Motivo**: dois pacotes regulares com o mesmo nome no mesmo interpretador não
  coexistem — o primeiro do `PYTHONPATH` sombreia o outro. Com os dois chamados `app`,
  o `CMD ["python", "-m", "app.main"]` do `worker.Dockerfile` subiria a **API** dentro
  do container do worker, e nada no boot denunciaria a troca. O worker continua
  importando `app.*` como biblioteca, que é o ponto que a spec queria garantir.
- **Ação na spec**: corrigir a árvore para `apps/worker/worker/`.

## DEV-A09 — o catálogo de settings tem 11 chaves, não 8

- **Spec**: BR-MIGRAR-027 fixa "catálogo de 8 chaves".
- **Código**: as 8 do legado mais `client_eval_spontaneous_enabled`,
  `client_eval_negative_keywords` e `client_eval_negative_rating_max`.
- **Motivo**: as oito são o inventário do que existia, não um limite do sistema novo.
  AMB-002 exige o fluxo espontâneo atrás de flag **por tenant**, e BR-MIGRAR-021 pede
  palavras negativas **configuráveis por tenant** — sem chave, as duas viravam constante
  no código e o cliente dependeria de deploy para ajustar. Todas nascem no default
  conservador: fluxo desligado, lista de palavras vazia.
- **Ação na spec**: registrar em BR-MIGRAR-027 que o catálogo cresce com o sistema, e
  incluir as três chaves.

## DEV-A10 — a submissão pública aceita `in_progress`, não só `pending`

- **Spec**: `target_data_model.md` § Concorrência descreve o guard como
  `UPDATE ... WHERE status='pending' AND token=... AND token_expires_at > now()`.
- **Código**: o mesmo UPDATE condicional, com `status IN ('pending','in_progress')`.
- **Motivo**: a máquina de estados da própria spec (`pending → in_progress → submitted`)
  passa por `in_progress` quando o cliente **abre** o formulário. Com o guard literal,
  todo cliente que abrisse a página antes de enviar seria recusado no envio — o guard
  recusaria exatamente o caminho normal. A intenção do guard é "ainda não respondida e
  dentro da validade", e é isso que o código implementa.
- **Ação na spec**: corrigir o SQL de exemplo.

## Pendências abertas do gate R-06

Corrigidas nesta rodada: B1 (revogação desfeita pelo rollback), B2 (PAR-08 `@critico`),
B3 (repositório fora do isolamento passava no CI), C1 (`/auth/my-team` truncava em 500).

Ainda abertas (`engagement` e `feedback` já foram implementados por cima desta base):

- (fechado) Os comandos de `Profile` e `TeamScope`, `Department`/`ProfileDepartment`/
  `TeamRequest` e o papel ativo (BR-MIGRAR-016) foram implementados.
- Nenhum passo de codegen do cliente OpenAPI no CI (AD-08).
- Os testes de service usam dublês; falta a camada de integração contra Postgres que
  exercite os `.feature` de PAR-05, PAR-07 e PAR-08 ponta a ponta.
- O scheduler tem três jobs (fechamento de ciclo, expiração de requests e expiração de
  tokens públicos). O inventário do `pg_cron` de produção (AMB-008) continua aberto — é
  ele que diz o que mais precisa existir ali.
- `apps/web` tem a fundação e 14 rotas (login, início, meus feedbacks + formulário,
  minha equipe, notificações, avaliações de clientes, relatórios, admin de
  usuários/ciclos/configurações, fale conosco e a página pública por token). Das 43
  telas de `target_screens.md`, faltam as secundárias — histórico de equipe, caderno
  do ciclo, feedback livre, formulários e permissões de admin, auditoria, comunicados,
  triagem de contatos e o detalhe de avaliação de cliente.
- **A comparação com o oráculo não foi feita.** As 35 telas do subset literal precisam
  ser conferidas contra os screenshots de `docs/reversa/screens/golden/` — é a validação
  que `parity_specs.md` exige e que depende de olho humano ou de um runner visual.
- `feedback` não tem leitura pelo destinatário (`read_at`/`read_by` em `feedback_requests`
  existem no schema, sem endpoint), nem as telas de histórico de equipe.
- Provedor de email: só `console`. Resend e SMTP levantam erro explícito, e a mensagem
  vai para a DLQ com o motivo — entram junto com o envio de relatórios (BR-MIGRAR-029/030).
