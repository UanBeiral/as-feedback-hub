---
schemaVersion: 1
generatedAt: 2026-08-28T00:00:00Z
reversa:
  version: "1.2.60"
kind: risk_register
producedBy: strategist
hash: "sha256:a3a84345e60b860966a1b955611a40ce18641ccf34c10a66672eab0d05eec424"
---

# Risk Register

> Riscos da migração A&S Feedback Hub → SaaS multi-tenant (Next.js + FastAPI + Postgres em VPS).
> Escala: probabilidade e impacto em baixa/média/alta.

## Riscos da estratégia (Big Bang + homologação comparativa)

### R-01 — Cutover falho por migração de dados incompleta
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: 12 das 28 tabelas do legado não têm DDL versionado (criadas via dashboard — gap do Data Master); o script de migração pode omitir colunas/constraints que só existem em produção.
- **Mitigação**: extrair schema real do banco de produção (`pg_dump --schema-only`) como fonte, não as migrations versionadas; ensaiar a migração completa ≥2 vezes em staging com dados reais; validar contagens e checksums por tabela.
- **Contingência**: rollback para o protótipo (que permanece intocado); janela de corte fora de horário de uso.
- **Owner**: Uan (executor da migração de dados).

### R-02 — Paridade funcional reprovada na homologação
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: confiança agregada das specs é 78,2% (`confidence-report.md`); regras 🟡 podem ter sido inferidas errado e só aparecerão na homologação com o cliente.
- **Mitigação**: parity specs do Inspector como roteiro de homologação; priorizar cedo na reconstrução os fluxos 🟡 (unicidade de requests BR-MIGRAR-010, concorrência de settings); homologação comparativa lado a lado com o protótipo.
- **Contingência**: ciclo de correção pós-homologação antes do cutover; o protótipo continua em produção nesse meio-tempo.
- **Owner**: Uan + cliente do projeto (validador).

### R-03 — Janela sem entrega de valor durante a reconstrução
- **Probabilidade**: alta · **Impacto**: médio
- **Descrição**: Big Bang não entrega incrementos; sem prazo definido no brief, a reconstrução pode se estender e desgastar a relação com o cliente.
- **Mitigação**: escopo do primeiro corte já reduzido (IA e Calendar adiados — AMB-005/007); demonstrações intermediárias em staging para o cliente acompanhar.
- **Contingência**: repriorizar módulos "Should/Could" para pós-cutover.
- **Owner**: Uan (gestão do projeto).

## Riscos da mudança de paradigma (gap alto — registro obrigatório)

### R-04 — Reimplementação incorreta da autorização
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: a matriz efetiva de RLS de produção nunca foi extraída (`permissions.md` 🟡); a camada de guards da API pode conceder mais (vazamento entre tenants/papéis) ou menos (bloqueio de fluxo legítimo) que o comportamento real.
- **Mitigação**: extrair policies RLS do banco de produção antes do design final dos guards; testes de autorização por papel × recurso derivados de `permissions.md`; testes de isolamento de tenant obrigatórios no CI.
- **Contingência**: auditoria de acesso pós-homologação; negar por padrão garante que erros tendam a bloqueio (visível) e não a vazamento (silencioso).
- **Owner**: Uan (design/implementação da API).

### R-05 — Semântica assíncrona diverge do comportamento síncrono percebido
- **Probabilidade**: baixa · **Impacto**: médio
- **Descrição**: ao mover notificações/relatórios para fila + worker, comportamentos que o usuário via como imediatos passam a ser eventualmente consistentes (ex.: notificação que aparecia ao recarregar a tela).
- **Mitigação**: manter operações principais síncronas (só efeitos auxiliares vão para a fila — BR-MIGRAR-025); idempotência preservada (outbox `update_id + user_id`, BR-MIGRAR-024).
- **Contingência**: ajustar polling/latência do worker se a homologação apontar percepção de atraso.
- **Owner**: Uan (design dos jobs).

### R-06 — Time sem experiência consolidada na stack alvo
- **Probabilidade**: média · **Impacto**: médio
- **Descrição**: risco organizacional padrão de gap alto: FastAPI com DI disciplinada, workers e operação de VPS (backup, TLS, monitoramento) exigem práticas que o protótipo nunca demandou.
- **Mitigação**: fundação (fase 1) com esqueleto de referência revisado antes da escala; observabilidade desde o início (a definir — lacuna do brief); backups automatizados do Postgres testados com restore.
- **Contingência**: reduzir superfície operacional (ex.: um único nó Docker Compose) até maturidade.
- **Owner**: Uan (infra/operacional).

## Riscos de dados

### R-07 — Perda de credenciais de usuários (Supabase Auth)
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: hashes de senha ficam no Supabase Auth (AMB-009); se não forem exportáveis no formato esperado, usuários perdem acesso no corte.
- **Mitigação**: verificar exportabilidade dos hashes (bcrypt) cedo, na fase 1; plano B: fluxo de redefinição de senha em massa no primeiro login pós-corte, comunicado com antecedência.
- **Contingência**: reset assistido pelo admin do tenant.
- **Owner**: Uan (auth própria).

### R-08 — Jobs pg_cron de produção desconhecidos
- **Probabilidade**: alta · **Impacto**: médio
- **Descrição**: os jobs agendados de produção não estão versionados (AMB-008); algum comportamento automático (fechamento de ciclo, expiração de tokens) pode não ser reproduzido no worker.
- **Mitigação**: inventariar `cron.job` do banco de produção antes do design final dos jobs (pré-requisito do cutover); mapear cada job para um job do worker.
- **Contingência**: monitorar pós-corte por comportamentos ausentes (ciclos que não fecham, tokens que não expiram).
- **Owner**: Uan (extração) + Designer (mapeamento).

### R-09 — Conversão single-tenant → multi-tenant corrompe escopo de dados
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: injetar `tenant_id` em 28 tabelas durante a migração de dados; erro de atribuição vazaria dados entre tenants futuros.
- **Mitigação**: no corte existe apenas 1 tenant (o cliente atual) — toda a base migra para ele, eliminando ambiguidade; constraints NOT NULL + FK de `tenant_id` desde a primeira migration; testes de isolamento antes de aceitar o 2º tenant.
- **Contingência**: enquanto houver 1 tenant, o risco é latente, não ativo; auditoria antes do onboarding do 2º cliente.
- **Owner**: Uan (schema/migração).

## Riscos operacionais

### R-10 — LGPD: dados sensíveis sem política formal
- **Probabilidade**: média · **Impacto**: alto
- **Descrição**: feedbacks anônimos e avaliações de clientes são dados sensíveis; a política de retenção/anonimização segue pendente de formalização com o cliente (AMB-001, default conservador adotado).
- **Mitigação**: default conservador já decidido (anonimização por design, exportação restrita a admin); formalizar com o cliente **antes da homologação** (decisão registrada).
- **Contingência**: ajustar schema/endpoints se a política formal divergir do default.
- **Owner**: Uan + cliente do projeto.

### R-11 — Dependência do Resend para email no corte
- **Probabilidade**: baixa · **Impacto**: baixo
- **Descrição**: o envio de relatório por email depende do Resend (`send-report-email`); chave/domínio precisam ser reconfigurados fora do Supabase.
- **Mitigação**: adapter de email configurável (BR-MIGRAR-030); validar domínio/DKIM na VPS antes do corte.
- **Contingência**: SMTP alternativo.
- **Owner**: Uan (infra).

## Resumo

| ID | Risco | Prob. | Impacto | Criticidade |
|---|---|---|---|---|
| R-01 | Migração de dados incompleta | média | alto | 🔴 crítico |
| R-02 | Paridade reprovada na homologação | média | alto | 🔴 crítico |
| R-04 | Autorização reimplementada errada | média | alto | 🔴 crítico |
| R-07 | Perda de credenciais | média | alto | 🔴 crítico |
| R-09 | Corrupção de escopo multi-tenant | média | alto | 🔴 crítico |
| R-10 | LGPD sem política formal | média | alto | 🔴 crítico |
| R-03 | Janela sem entrega de valor | alta | médio | 🟡 |
| R-08 | Jobs pg_cron desconhecidos | alta | médio | 🟡 |
| R-05 | Semântica assíncrona divergente | baixa | médio | 🟢 |
| R-06 | Curva da stack alvo | média | médio | 🟡 |
| R-11 | Dependência Resend | baixa | baixo | 🟢 |
