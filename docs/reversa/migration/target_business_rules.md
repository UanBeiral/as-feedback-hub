---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: target_business_rules
producedBy: curator
hash: "sha256:29038327b17b3e9db7abdac6a7b02bb1d3af7caf41e72f71b6cd0c5fc42d521a"
---

# Target Business Rules

> Catálogo das regras de negócio do legado com decisão de migração: MIGRAR, DESCARTAR ou DECISÃO HUMANA.
> Cada item rastreia para a origem em `_reversa_sdd/` e respeita o `paradigm_decision.md` (escolha 1, apetite `transformational`).

## Resumo
- Total de regras analisadas: 44
- MIGRAR: 30
- DESCARTAR: 7 (detalhe em `discard_log.md`)
- DECISÃO HUMANA: 7

## Regras MIGRAR

### Núcleo de ciclos e requests

### BR-MIGRAR-001
- **Origem**: `_reversa_sdd/domain.md` § Regras de negócio; `_reversa_sdd/feedback/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: A abertura de um ciclo gera requests a partir das permissões ativas em `feedback_permissions`; somente usuários ativos participam da geração.
- **Justificativa de migração**: regra central do produto, confirmada em código.
- **Compatibilidade com paradigma alvo**: vira invariante do aggregate `FeedbackCycle` no service de abertura (`POST /cycles/{id}/open`), com escopo de `tenant_id`.

### BR-MIGRAR-002
- **Origem**: `_reversa_sdd/feedback/requirements.md` § Regras; `_reversa_sdd/admin/requirements.md` § RF-03
- **Confiança original**: 🟢
- **Descrição**: Permissão `peer_to_peer` cria (ou preserva) a relação reversa automaticamente.
- **Justificativa de migração**: comportamento confirmado (`ensureReversePeerPermission`).
- **Compatibilidade com paradigma alvo**: efeito colateral transacional dentro do service de permissões, não mais em componente de tela.

### BR-MIGRAR-003
- **Origem**: `_reversa_sdd/state-machines.md` § Request de feedback interno
- **Confiança original**: 🟢 (exceto `reviewed`, tratado em BR-HUMANA-003)
- **Descrição**: Máquina de estados do request: `pending → draft → submitted`, com `waived` (abdicar/retomar), `cancelled` (com justificativa) e `expired` (prazo + carência).
- **Justificativa de migração**: máquina confirmada em múltiplas telas.
- **Compatibilidade com paradigma alvo**: transições validadas no domínio (service), nunca por update livre; `expired` vira estado derivado ou job (ver BR-MIGRAR-007).

### BR-MIGRAR-004
- **Origem**: `_reversa_sdd/state-machines.md` § Ciclo de feedback
- **Confiança original**: 🟢
- **Descrição**: Máquina de estados do ciclo: `draft → open → closed → published → archived`, com `draft → archived` direto.
- **Justificativa de migração**: confirmada nas operações de `AdminCiclos`.
- **Compatibilidade com paradigma alvo**: transições como métodos do aggregate; gatilhos automáticos (fechamento) via job agendado no worker.

### BR-MIGRAR-005
- **Origem**: `_reversa_sdd/domain.md` § Decisões e sinais do histórico
- **Confiança original**: 🟢
- **Descrição**: Carência (tolerância) de 3 dias antes do fechamento automático do ciclo.
- **Justificativa de migração**: decisão operacional confirmada por commit e telas de atraso.
- **Compatibilidade com paradigma alvo**: parâmetro do job de fechamento no worker (substitui pg_cron — ver BR-DESCARTAR-003).

### BR-MIGRAR-006
- **Origem**: `_reversa_sdd/domain.md` § Glossário e Decisões
- **Confiança original**: 🟢
- **Descrição**: O período avaliado pode divergir das datas básicas do ciclo, com extensão manual da janela de resposta.
- **Justificativa de migração**: capacidade confirmada no histórico de commits e telas.
- **Compatibilidade com paradigma alvo**: campo próprio no modelo do ciclo, validado no domínio.

### BR-MIGRAR-007
- **Origem**: `_reversa_sdd/domain.md` § Regras; `_reversa_sdd/gestor/requirements.md` § Regras; `_reversa_sdd/coordenador/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Requests `pending`/`draft` ficam expirados/atrasados após prazo + tolerância configurada; a janela de atraso considera até 3 dias.
- **Justificativa de migração**: regra confirmada nas visões de pendências.
- **Compatibilidade com paradigma alvo**: no legado o cálculo era visual (na UI); no alvo vira derivação server-side (query/serviço), garantindo consistência entre telas e relatórios.

### BR-MIGRAR-008
- **Origem**: `_reversa_sdd/domain.md` § Regras; `_reversa_sdd/feedback/requirements.md` § RF-04
- **Confiança original**: 🟢
- **Descrição**: O envio de feedback exige respostas válidas conforme o formulário e registra `submitted_at`.
- **Justificativa de migração**: contrato de submissão confirmado.
- **Compatibilidade com paradigma alvo**: validação Pydantic contra o formulário no endpoint de submissão.

### BR-MIGRAR-009
- **Origem**: `_reversa_sdd/domain.md` § Regras; `_reversa_sdd/gestor/requirements.md`, `_reversa_sdd/coordenador/requirements.md`
- **Confiança original**: 🟢
- **Descrição**: Progresso do ciclo exclui requests `cancelled` e `waived` do denominador; `submitted` conta como concluído.
- **Justificativa de migração**: regra de métrica confirmada em três módulos.
- **Compatibilidade com paradigma alvo**: única implementação server-side (service de métricas), eliminando a duplicação por tela do legado.

### BR-MIGRAR-010
- **Origem**: `_reversa_sdd/feedback/requirements.md` § RNF Consistência
- **Confiança original**: 🟡
- **Descrição**: Requests devem ser únicos por par (avaliador, avaliado) / ciclo / formulário.
- **Justificativa de migração**: inferida de `generateFeedbackRequests.ts`; essencial para integridade.
- **Compatibilidade com paradigma alvo**: constraint UNIQUE no schema novo + idempotência na geração. ⚠️ Validar semântica exata na codificação.

### BR-MIGRAR-011
- **Origem**: `_reversa_sdd/admin/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Ciclos da mesma frequência têm limite de concorrência; janela ocupada gera alerta.
- **Justificativa de migração**: regra operacional confirmada.
- **Compatibilidade com paradigma alvo**: invariante verificada no service de abertura, por tenant.

### BR-MIGRAR-012
- **Origem**: `_reversa_sdd/feedback/requirements.md` § RF-05
- **Confiança original**: 🟢
- **Descrição**: Rascunho pode ser salvo e retomado sem perda das respostas existentes.
- **Justificativa de migração**: capacidade confirmada.
- **Compatibilidade com paradigma alvo**: persistência parcial validada de forma branda (draft) vs. estrita (submit).

### Autorização, papéis e escopo

### BR-MIGRAR-013
- **Origem**: `_reversa_sdd/permissions.md` § Validação humana
- **Confiança original**: 🟢
- **Descrição**: Negar por padrão: escopo vazio/nulo, flag ausente ou parâmetro fora do escopo não concede acesso; parâmetros de URL não ampliam escopo.
- **Justificativa de migração**: contrato canônico validado pelo usuário.
- **Compatibilidade com paradigma alvo**: princípio da camada de autorização da API (dependencies FastAPI), agora com `tenant_id` obrigatório.

### BR-MIGRAR-014
- **Origem**: `_reversa_sdd/permissions.md` § Rotas por papel; `_reversa_sdd/admin/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Matriz RBAC por papel (colaborador, gestor, coordenador, admin/RH): gestão administrativa exclusiva de admin/RH; gestão de equipe para gestor+; dashboard próprio para todos.
- **Justificativa de migração**: matriz confirmada.
- **Compatibilidade com paradigma alvo**: roles + policies na API; a matriz de `permissions.md` vira especificação dos guards.

### BR-MIGRAR-015
- **Origem**: `_reversa_sdd/permissions.md` § Flags por perfil; `_reversa_sdd/colaborador/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Flags de capacidade por perfil (`can_request_client_feedback`, `can_view_feedback_answers`, `can_view_team_history`, `can_generate_reports`, `can_view_manager_dashboard`, `is_coordinator`) controlam capacidades individuais.
- **Justificativa de migração**: comportamento confirmado por flag.
- **Compatibilidade com paradigma alvo**: claims/permissões do perfil avaliadas server-side, não mais como redirecionamento de componente.

### BR-MIGRAR-016
- **Origem**: `_reversa_sdd/auth/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Usuário inativo não acessa rotas protegidas; usuários multi-papel escolhem `activeRole` e a navegação respeita a escolha; o papel permitido pode ser o persistido ou o ativo.
- **Justificativa de migração**: contrato de sessão confirmado.
- **Compatibilidade com paradigma alvo**: status verificado na emissão/validação do token de sessão; `activeRole` vira claim de contexto. ⚠️ Autorização final sempre server-side.

### BR-MIGRAR-017
- **Origem**: `_reversa_sdd/gestor/requirements.md` § Regras; `_reversa_sdd/coordenador/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Escopo de equipe: gestor vê membros por `manager_id`; equipe do coordenador é a união deduplicada de subordinados diretos e `coordinator_members`; histórico respeita `view_history_of`.
- **Justificativa de migração**: regra de escopo confirmada e validada pelo usuário.
- **Compatibilidade com paradigma alvo**: resolução de escopo no service (team resolver), aplicada a toda query de equipe.

### BR-MIGRAR-018
- **Origem**: `_reversa_sdd/domain.md` § Validação humana; `_reversa_sdd/colaborador/requirements.md` § Validação humana
- **Confiança original**: 🟢
- **Descrição**: Remoção de usuário é soft-delete (`status = 'deleted'`): histórico preservado, acesso revogado.
- **Justificativa de migração**: decisão validada pelo usuário.
- **Compatibilidade com paradigma alvo**: soft-delete no modelo + revogação de sessão/credenciais no serviço de auth próprio.

### Avaliação pública de cliente

### BR-MIGRAR-019
- **Origem**: `_reversa_sdd/public/requirements.md` § Regras e Validação humana
- **Confiança original**: 🟢
- **Descrição**: Token público só é aceito com registro `pending` e dentro da validade; a submissão é atualização atômica condicionada (`status='pending'` + validade + `UNIQUE(token)`); segunda submissão retorna confirmação idempotente.
- **Justificativa de migração**: guard atômico confirmado e validado.
- **Compatibilidade com paradigma alvo**: endpoint público próprio com validação de token, update condicional e resposta idempotente; adicionar rate limiting (nota do `paradigm_decision.md`).

### BR-MIGRAR-020
- **Origem**: `_reversa_sdd/public/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Formulário público é dinâmico: perguntas de `client_feedback_forms`/`client_feedback_form_questions` na ordem persistida.
- **Justificativa de migração**: confirmado.
- **Compatibilidade com paradigma alvo**: schema de formulário servido pela API; render no Next.js.

### BR-MIGRAR-021
- **Origem**: `_reversa_sdd/domain.md` § Regras; `_reversa_sdd/public/requirements.md` § RF-04
- **Confiança original**: 🟢
- **Descrição**: Avaliações de cliente podem ser sinalizadas por nota baixa ou palavras negativas configuradas.
- **Justificativa de migração**: triagem confirmada.
- **Compatibilidade com paradigma alvo**: análise no service de submissão (ou job assíncrono), com palavras-chave configuráveis por tenant.

### BR-MIGRAR-022
- **Origem**: `_reversa_sdd/colaborador/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Estados da avaliação de cliente para exibição: `pending`/`in_progress` = pendente, `submitted` = respondido, `expired` = expirado; WhatsApp mascarado na listagem.
- **Justificativa de migração**: mapeamento e privacidade confirmados.
- **Compatibilidade com paradigma alvo**: mapeamento no serializer da API; mascaramento server-side (o dado bruto não sai da API sem permissão).

### Notificações, auditoria e operações auxiliares

### BR-MIGRAR-023
- **Origem**: `_reversa_sdd/notifications/requirements.md` § Validação humana
- **Confiança original**: 🟢
- **Descrição**: Notificação não lida = `read_at IS NULL` (sem coluna booleana); notificação tem destinatário, tipo, título, mensagem e link opcional.
- **Justificativa de migração**: contrato validado.
- **Compatibilidade com paradigma alvo**: modelo idêntico no schema novo.

### BR-MIGRAR-024
- **Origem**: `_reversa_sdd/notifications/requirements.md` § Validação humana
- **Confiança original**: 🟢
- **Descrição**: Comunicações de ciclo usam outbox persistente por destinatário com chave de idempotência `update_id + user_id`.
- **Justificativa de migração**: padrão outbox validado pelo usuário.
- **Compatibilidade com paradigma alvo**: nativo no paradigma — outbox + worker consumindo fila Redis; a chave de idempotência é preservada.

### BR-MIGRAR-025
- **Origem**: `_reversa_sdd/domain.md` § Decisões; `_reversa_sdd/gestor/requirements.md` § Critérios; `_reversa_sdd/coordenador/requirements.md` § RNF
- **Confiança original**: 🟢
- **Descrição**: Falha de efeito auxiliar (notificação, auditoria, email) não desfaz a operação principal já persistida; a falha auxiliar é informada.
- **Justificativa de migração**: contrato de resiliência confirmado.
- **Compatibilidade com paradigma alvo**: absorvido por construção — efeitos auxiliares viram jobs enfileirados após commit da transação principal (transactional outbox).

### BR-MIGRAR-026
- **Origem**: `_reversa_sdd/coordenador/requirements.md` § Regras e Validação humana; `_reversa_sdd/admin/requirements.md` § RF-06
- **Confiança original**: 🟢
- **Descrição**: Ações sensíveis (remoção de membro, cancelamento com justificativa) registram auditoria em `audit_logs` com `actor_id` (não `user_id`) e tentam notificar envolvidos.
- **Justificativa de migração**: contrato de auditoria confirmado e validado.
- **Compatibilidade com paradigma alvo**: auditoria como evento pós-commit processado pelo worker; nomenclatura `actor_id` preservada.

### Configurações e relatórios

### BR-MIGRAR-027
- **Origem**: `_reversa_sdd/company-settings/requirements.md` § Validação humana; `_reversa_sdd/permissions.md` § Configurações globais
- **Confiança original**: 🟢
- **Descrição**: Configurações são key/value com catálogo de 8 chaves (nome, logo, motivações públicas, template WhatsApp, palavras-chave de calendário e 3 toggles globais: `gestor_can_access_reports`, `gestor_can_access_agenda`, `colaborador_can_generate_own_report`); toggles são globais por escritório e aplicados por papel.
- **Justificativa de migração**: catálogo validado pelo usuário.
- **Compatibilidade com paradigma alvo**: settings por **tenant** (era "por escritório" — o conceito generaliza); upsert por chave com concorrência otimista (`updated_at`) e `updated_by` populado (dívida 🟡 do legado sanada no alvo).

### BR-MIGRAR-028
- **Origem**: `_reversa_sdd/reports/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Engajamento calcula apenas sobre ciclos fechados e exclui pessoas sem requests do denominador; relatório executivo exige ciclo e pessoa (salvo escopo geral) e avaliador quando escopo específico.
- **Justificativa de migração**: regras de cálculo confirmadas.
- **Compatibilidade com paradigma alvo**: cálculos server-side no service de relatórios (no legado eram feitos no cliente).

### BR-MIGRAR-029
- **Origem**: `_reversa_sdd/reports/requirements.md` § Regras; `_reversa_sdd/colaborador/requirements.md` § Regras
- **Confiança original**: 🟢
- **Descrição**: Exportações refletem exatamente os filtros ativos; CSV usa separador `;`; preview limita 50 linhas e tabela 100; relatório de cliente respeita `can_generate_reports`.
- **Justificativa de migração**: contratos de exportação confirmados.
- **Compatibilidade com paradigma alvo**: filtros aplicados na query da API; geração de arquivos grandes vira job assíncrono no worker (PDF/XLSX), com download por link.

### BR-MIGRAR-030
- **Origem**: `_reversa_sdd/reports/requirements.md` § Validação humana; `_reversa_sdd/domain.md` § Decisões
- **Confiança original**: 🟢 (contrato `send-report-email`) / 🟡 (compatibilidade)
- **Descrição**: Relatório executivo em PDF pode ser enviado por email; validação, configuração ausente e falha do provedor (Resend) têm tratamentos distintos; falha de email não invalida o relatório gerado.
- **Justificativa de migração**: capacidade explícita do produto.
- **Compatibilidade com paradigma alvo**: job de email no worker com retry; provedor de email vira adapter configurável (Resend ou SMTP próprio da VPS).

## Regras DESCARTAR (resumo)

| ID | Origem | Motivo curto | Vínculo a paradigma? |
|---|---|---|---|
| BR-DESCARTAR-001 | `domain.md`, `permissions.md` | RLS como mecanismo de autorização | sim |
| BR-DESCARTAR-002 | `domain.md` § Decisões | Edge Functions Deno + `waitUntil` para envio em background | sim |
| BR-DESCARTAR-003 | `database/procedures.md`, checkpoint Data Master | Jobs `pg_cron`/`pg_net` não versionados | sim |
| BR-DESCARTAR-004 | `inventory.md`, `architecture.md` | Acesso direto do cliente ao banco (`supabase.from`) e anon key | sim |
| BR-DESCARTAR-005 | `auth/requirements.md` | Supabase Auth como provedor de identidade | não (restrição do brief) |
| BR-DESCARTAR-006 | `architecture.md` § Riscos | Rotas duplicadas de coordenador no `App.tsx` | não (defeito) |
| BR-DESCARTAR-007 | checkpoint Design System | 657 cores hardcoded + ~270 linhas de overrides `.dark !important` | não (dívida) |

> Detalhe completo em `discard_log.md`. Nenhuma regra de negócio foi descartada — todos os descartes são mecanismos ou defeitos; as regras que eles serviam migram com novo mecanismo.

## Regras DECISÃO HUMANA

### BR-HUMANA-001
- **Origem**: `_reversa_sdd/domain.md` § Regras (🔴); `_reversa_sdd/gaps.md` § Moderadas
- **Tipo de ambiguidade**: 🔴 GAP + dependência de stakeholder
- **Descrição**: Política de retenção, anonimização e exportação de dados sensíveis (feedbacks anônimos, avaliações de clientes, contatos) não foi definida.
- **Opções**: (a) definir política agora com o cliente e modelar no schema novo; (b) migrar sem política formal e tratar depois; (c) adotar default conservador (retenção indefinida, anonimização de feedback anônimo por design, exportação só por admin).
- **Recomendação do Curator**: (c) como base já modelada no schema + agendar (a) com o cliente antes da homologação — LGPD torna isso não-adiável num SaaS multi-tenant.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-002
- **Origem**: `_reversa_sdd/public/requirements.md` § Validação humana (🔴)
- **Tipo de ambiguidade**: 🔴 GAP
- **Descrição**: O fluxo público espontâneo (sem token, via anon key) existe em produção mas suas policies nunca foram auditadas. Migrar esse fluxo para o alvo?
- **Opções**: (a) migrar com endpoint público próprio + rate limiting + captcha; (b) descontinuar — só avaliação por convite/token; (c) manter atrás de flag por tenant.
- **Recomendação do Curator**: (c) — o fluxo tem valor comercial mas risco de abuso; flag por tenant permite ligar só onde o cliente pedir.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-003
- **Origem**: `_reversa_sdd/state-machines.md` § Request (🟡 `reviewed`)
- **Tipo de ambiguidade**: ⚠️ AMBÍGUA
- **Descrição**: O status `reviewed` aparece no mapa de status de relatórios, mas nenhum gatilho foi localizado no código. Incluir no modelo novo?
- **Opções**: (a) incluir `reviewed` com transição explícita `submitted → reviewed`; (b) omitir do modelo novo até haver caso de uso.
- **Recomendação do Curator**: (b) — sem gatilho confirmado, incluir seria especular; adicionar depois é migração trivial de schema.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-004
- **Origem**: `_reversa_sdd/domain.md` § Validação humana (🟡); `_reversa_sdd/state-machines.md` § Validação humana
- **Tipo de ambiguidade**: 🔴 GAP parcial
- **Descrição**: `team_requests` tem aprovação/rejeição confirmadas, mas cancelamento, expiração e demais transições não têm contrato. `feedback_contacts` (`novo → em_andamento → resolvido`) está confirmada.
- **Opções**: (a) migrar só o confirmado (aprovação/rejeição) e definir o resto no design; (b) completar a máquina agora com o usuário.
- **Recomendação do Curator**: (a) — o Designer fecha as transições faltantes como decisão de design documentada.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-005
- **Origem**: `_reversa_sdd/reports/requirements.md` § Validação humana (🔴)
- **Tipo de ambiguidade**: 🔴 GAP
- **Descrição**: As Edge Functions de IA (`analyze-feedback`, `analyze-cycle`) existem em produção mas contratos e fontes não estão versionados. Migrar a análise de IA?
- **Opções**: (a) reimplementar como jobs no worker chamando API de IA, com contrato novo; (b) adiar para pós-homologação; (c) descartar.
- **Recomendação do Curator**: (b) — não é bloqueante para paridade de homologação; reimplementar depois com contrato limpo.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-006
- **Origem**: `_reversa_sdd/notifications/requirements.md` § Regras (🔴 retry/entrega)
- **Tipo de ambiguidade**: 🔴 GAP
- **Descrição**: Política de retry, confirmação de entrega e catálogo completo de notificações nunca foram definidos no legado.
- **Opções**: (a) definir política padrão de fila (retry exponencial, DLQ, sem confirmação de leitura além de `read_at`); (b) levantar catálogo completo com o cliente antes.
- **Recomendação do Curator**: (a) — a infraestrutura alvo (Redis + workers) já traz semântica de retry/DLQ; o catálogo de tipos emerge das telas na fase do Screen Translator.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

### BR-HUMANA-007
- **Origem**: `_reversa_sdd/architecture.md` § C4 (Google Calendar); `_reversa_sdd/admin/requirements.md` § MoSCoW (Could)
- **Tipo de ambiguidade**: dependência de stakeholder
- **Descrição**: Integração com Google Calendar (agenda, tokens OAuth em `google_calendar_tokens`) é funcionalidade complementar condicionada a configuração. Migrar no primeiro corte?
- **Opções**: (a) migrar junto; (b) adiar para fase 2 pós-homologação; (c) descartar.
- **Recomendação do Curator**: (b) — é "Could" no MoSCoW do legado e não afeta a paridade dos fluxos de feedback; reduz o escopo do cutover.
- **Status**: RESOLVIDA (recomendação do Curator aceita integralmente — decisor: Uan, 2026-08-28)

## Notas
- A granularidade do inventário reflete a qualidade alta do `_reversa_sdd/` (10 units com requirements completos + validações humanas de 2026-08-25).
- Todos os itens DECISÃO HUMANA foram replicados em `ambiguity_log.md` com status PENDENTE.
- Regras multi-tenant: nenhuma regra do legado menciona tenant porque o sistema era single-tenant por design; o Designer deve aplicar `tenant_id` transversalmente a **todas** as regras MIGRAR (nota herdada do `paradigm_decision.md`).
