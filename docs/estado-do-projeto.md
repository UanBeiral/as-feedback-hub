# Estado do projeto — onde paramos

> Escrito em 02/09/2026, ao fim da sessão que construiu o sistema.
> Atualizado em 06/09/2026, no fecho da conferência contra o oráculo.
> Serve para quem chegar depois (pessoa ou agente) entender em uma leitura o que existe,
> o que falta e por que certas coisas são do jeito que são.

## O que este repositório é

A reconstrução do protótipo `aesfeedbackinterno` (Lovable + Supabase) como sistema
próprio, seguindo as specs de migração em [`docs/reversa/migration/`](reversa/migration/).
O protótipo **não é referência de implementação**: quando o código antigo e a spec
divergem, a spec vence.

Leitura obrigatória antes de mexer, nesta ordem:

1. [`docs/reversa/migration/handoff.md`](reversa/migration/handoff.md) — porta de entrada
2. `paradigm_decision.md` — OO com DI (FastAPI) + event-driven; inegociável
3. `topology_decision.md` — monorepo por bounded context; **papel de usuário é
   autorização, nunca pasta**
4. [`docs/spec-deviations.md`](spec-deviations.md) — os pontos em que o código
   deliberadamente não segue a spec, com o motivo. **Confira aqui antes de "consertar"
   algo que parece divergente.**

## O que está pronto

| Parte | Estado |
|---|---|
| API (FastAPI) | 5 contextos, 104 rotas, 30 tabelas |
| Worker | despacho do outbox + 3 jobs agendados |
| Front (Next.js) | 32 rotas, client tipado gerado do OpenAPI; fluxo público em wizard |
| Testes | 385, todos verdes |
| Migrations | 0001→0008, aplicam do zero |
| CI | lint + testes + migrations + build do front |

Os cinco contextos: `identity` (sessão, pessoas, equipe, papel ativo), `engagement`
(outbox, notificações, settings, auditoria), `feedback` (ciclos, requests, progresso),
`client_eval` (avaliação pública por token) e `reporting` (relatórios e exportações).

As 30 regras BR-MIGRAR têm implementação e teste. As 7 BR-DESCARTAR foram descartadas
como decidido.

## O que falta

**Bloqueia o cutover, e depende de acesso à produção** (nenhum eu consigo fazer daqui):

- **AMB-008** — inventariar os jobs `pg_cron` do Supabase. O passo a passo está em
  [`runbook_pre_cutover.md`](reversa/migration/runbook_pre_cutover.md).
- **AMB-010** — `pg_dump --schema-only` da produção. O schema real é a fonte da verdade,
  e 12 das 28 tabelas do legado nunca tiveram DDL versionado.
- **AMB-013** — confirmar o formato dos hashes do Supabase Auth. Se não forem
  exportáveis, a redefinição de senha em massa precisa ser planejada com antecedência.

**Não bloqueia, mas está aberto:**

- **A comparação com o oráculo terminou.** As 18 telas literais foram conferidas e
  renderam **90 divergências e 8 defeitos próprios**, todos registrados em
  [`docs/conferencia-resultado.md`](conferencia-resultado.md). 87 divergências foram
  implementadas; 3 ficaram como desvio deliberado, com o motivo escrito (#2 logo no
  login, #43 e #67 modais que revelam o que já está na tela). Os 8 defeitos foram
  corrigidos — e dois deles justificam a conferência sozinhos: recarregar a página
  deslogava, e `can_view_team_history` decidia o menu sem que a rota a exigisse.
  Cinco telas nasceram dela: Feedbacks Pendentes da equipe, a aba de Formulários de
  Cliente Externo, Meu Histórico, Reset de Senha e Dar Feedback.
- **Os 10 arquivos `.feature` de paridade não rodam.** Os cenários estão cobertos por
  testes de service, mas o roteiro formal da homologação ainda não é executável.
- **Telas: 42 das 43.** Falta só a **Agenda**, fora do corte por decisão (AMB-007,
  fase 2) — com ela ficam de fora o callback do Google (SCR-0040) e a agenda conectada
  (SCR-0045), que só existem para servi-la.
- **Três pontos do wizard público dependem do cliente, não de código**: qual pergunta era
  a Q6 do legado, qual pergunta alimenta a coluna "Nota Geral" dos relatórios e o que
  fazer com o chip "+ Outro…" do tipo de serviço. Estão em `spec-deviations.md`
  (DEV-A12, DEV-A13) e no roteiro de conferência.
- **O provedor de email está implementado, mas não configurado.** `console`, `resend` e
  `smtp` funcionam; o `.env` de desenvolvimento aponta para `console`, que só escreve no
  log. Falta escolher o provedor de produção e verificar o domínio — é o que R-11 pede, e
  `deploy/testar_email.py` existe para validar isso antes do corte.
- **Análises de IA** (AMB-005) e **status `reviewed`** (AMB-003) ficaram fora por decisão
  registrada, não por esquecimento.

## Fila de trabalho

Em ordem de valor, para quem for continuar. Cada item diz o que fazer e onde olhar.

A conferência contra o oráculo saiu da fila: terminou em 06/09/2026, com as 90
divergências resolvidas ou registradas como desvio. O que ela rendeu está em
[`docs/conferencia-resultado.md`](conferencia-resultado.md), e vale ler antes de mexer em
qualquer tela — a maioria das decisões de comportamento do sistema está justificada lá.

1. **Escolher e verificar o provedor de email em produção.** O código está pronto
   (`resend` e `smtp`, com o teste de fumaça em `deploy/testar_email.py`); o que falta é
   decisão e domínio: chave do Resend com o remetente verificado, ou host SMTP do
   cliente. Enquanto o `.env` de produção disser `console`, ninguém recebe nada — e isso
   inclui o link de redefinição de senha, que é a única forma de alguém recuperar o
   acesso sozinho.
2. **Tornar os `.feature` executáveis.** Os 10 arquivos em
   `docs/reversa/migration/parity_tests/` são o roteiro formal da homologação e hoje não
   rodam. Os cenários estão cobertos por testes de service, mas o cliente vai homologar
   pelo roteiro, não pela suíte.
3. **Perguntar ao cliente os três pontos em aberto do wizard público**: qual era a Q6,
   qual pergunta alimenta a "Nota Geral" e o que fazer com o chip "+ Outro…". Não é
   código — é decisão que muda o que a tela pergunta.
4. **Os três itens do runbook** — dependem de acesso à produção e bloqueiam o cutover,
   não o desenvolvimento. Detalhe abaixo.

Antes de qualquer entrega grande, subir o Postgres e rodar os fluxos de ponta a ponta.
A seção seguinte explica por quê.

## Coisas que só aparecem rodando

Estes defeitos não foram pegos por teste nenhum — apareceram ao rodar contra Postgres de
verdade, ou ao comparar a tela com o screenshot do legado. Vale saber que essa é a classe
de erro que escapa:

- Escrita seguida de `raise` era desfeita pelo rollback do request, e o detector de reúso
  de refresh token virava enfeite. Corrigido com transação autônoma.
- O mesmo detector, depois de consertado, passou a **derrubar a sessão em todo F5**: o
  boot do front pedia `/auth/me` e `/settings` em paralelo, os dois renovavam com o
  mesmo refresh token, e a rotação lia-decidia-gravava sem atomicidade. Duas
  apresentações simultâneas de um token roubado também passavam as duas. Corrigido dos
  dois lados — renovação única no front, UPDATE condicional na API.
- `NULL <= now()` é NULL, não falso: mensagens de outbox sem `next_attempt_at` ficavam
  invisíveis para o worker **para sempre**, sem erro em lugar nenhum.
- Autoflush invertia a ordem de dois INSERTs com FK entre si.
- `vars()` não funciona em dataclass com `slots` — e o erro ficou escondido enquanto as
  listas estavam vazias.
- Altura em porcentagem sem altura definida no pai resolve para zero: o gráfico da
  auditoria renderizava **vazio com dados**, sem erro em lugar nenhum.
- Duas classes do Tailwind em conflito (`w-full` e `w-auto`) são decididas pela ordem no
  CSS gerado, não pela ordem na string — a barra de filtros empilhava por causa disso.

Três só apareceram porque alguém finalmente **usou** o caminho inteiro:

- O relatório executivo em escopo **geral** era aceito pela API com 202 e recusado pelo
  worker até a DLQ, dizendo que exigia ciclo e pessoa. As duas metades da mesma regra
  discordavam, e nada acusava porque nenhuma tela chegava a pedir o relatório.
- O PDF gerado **nascia no disco do worker e a API devolvia 500** ao tentar servi-lo: os
  dois containers não compartilhavam `data/`. O download de exportação nunca tinha
  funcionado no compose.
- E o volume, se criado sem `data/` existir na imagem, nasceria de root — o processo sem
  privilégio não gravaria nada.

Um veio de ler o código no rastro de outra coisa: `/client-eval/evaluations` devolvia
**todas as avaliações do escritório para qualquer autenticado** — quem tinha login via
quais clientes reclamaram de quem. Passava despercebido porque a tela parecia certa; o
recorte é que não existia.

E dois vieram da conferência, que é outra forma de rodar: o histórico da equipe mostrava
feedback **sensível**, que a rota de recebidos esconde do destinatário desde sempre, e
`can_view_team_history` decidia o menu sem que a rota a exigisse — quem soubesse a URL
entrava. Nenhum teste podia pegá-los, porque os dois estavam consistentes consigo mesmos.

Por isso os smokes contra o banco real existem, e por isso vale rodá-los antes de
qualquer entrega grande.

## Como rodar

Instruções completas no [README](../README.md). O essencial:

```bash
cp .env.example .env                    # preencha JWT_SECRET e POSTGRES_PASSWORD
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build
alembic upgrade head
PYTHONPATH=apps/api python deploy/seed_tenant.py --slug <empresa> --nome "<Empresa>" \
    --email admin@empresa.com.br --senha "..."
```

Depois ajuste `DEFAULT_TENANT_SLUG` no `.env` para o slug criado e reinicie a API —
enquanto houver um escritório só, é essa chave que o login usa para achar o tenant.

Para **olhar** o sistema — conferir tela, demonstrar, reproduzir bug — use o outro seed:

```bash
PYTHONPATH=apps/api python deploy/seed_demo.py --senha "..." --recriar
```

Ele cria o escritório fictício Braga & Duarte com nove pessoas, dois ciclos, avaliações
de cliente respondidas e uma matriz de permissões **suja de propósito** — sem par
recíproco, com gente sem cobertura. Contra tabela vazia, metade das telas renderiza
estado vazio e não prova nada; foi ele que tornou a conferência possível.

O front sobe em `http://localhost:3000`.

## Reversa

O framework está instalado (`.claude/skills/`, `.agents/`, `.reversa/`) e liberado a
escrever em `apps/`, `packages/`, `alembic/`, `deploy/` e `docs/` — ver
`.reversa/reversa-config.json`.

`[output] folder` aponta para `docs/reversa`, e não para a pasta padrão `_reversa_sdd`:
as specs já vivem ali, e duplicá-las criaria duas verdades que divergem em semanas.

Fluxos úteis: `/reversa-forward` (evoluir com specs), `/reversa-debugger` (bugs com
rastreabilidade), `/reversa-docs` (mini-site da documentação), `/reversa-refactor`
(dívida que vale a pena pagar). Para pedidos em linguagem normal, nada disso é
necessário.

## Onde está o resto da história

O raciocínio de cada decisão está nas **mensagens de commit** — elas são longas de
propósito. `git log` deste repositório explica por que o `profiles.id` é o `users.id`,
por que a auditoria não passa pelo outbox, por que o pacote do worker não se chama `app`
e por que o catálogo de settings tem 11 chaves em vez das 8 da spec.
