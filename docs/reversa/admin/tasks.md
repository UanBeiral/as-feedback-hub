# Unidade: Administração, Tarefas de Implementação

## Pré-requisitos

- [ ] Dependências da unit listadas em `design.md` estão disponíveis.
- [ ] Schema e migrations do Supabase são compatíveis com perfis, ciclos, permissões, formulários, auditoria e configurações.
- [ ] Variáveis de ambiente do Supabase e configuração de deploy estão documentadas.
- [ ] Políticas RLS e contratos das Edge Functions foram confirmados. 🔴

## Tarefas

- [ ] T-01, Implementar proteção das rotas administrativas e seleção do papel ativo.
  - Origem no legado: `src/App.tsx`, `src/components/ProtectedRoute.tsx`, `src/contexts/AuthContext.tsx`
  - Critério de pronto: rotas administrativas rejeitam sessão ausente e papéis não autorizados; papéis múltiplos podem selecionar contexto.
  - Confiança: 🟢

- [ ] T-02, Implementar listagem, criação, edição e inativação de perfis com departamentos e flags.
  - Origem no legado: `src/pages/admin/AdminUsuarios.tsx`, `src/components/admin/UserForm.tsx`
  - Critério de pronto: alterações de perfil persistem, flags reaparecem após recarregar e usuários inativos não acessam rotas protegidas.
  - Confiança: 🟢

- [ ] T-03, Implementar CRUD de departamentos e associação de perfis.
  - Origem no legado: `src/pages/admin/AdminDepartamentos.tsx`, `src/pages/admin/AdminUsuarios.tsx`
  - Critério de pronto: departamentos podem ser listados e associados sem perder o fallback de `department_id` quando aplicável.
  - Confiança: 🟢

- [ ] T-04, Implementar permissões de avaliação e reversão automática de relações peer-to-peer.
  - Origem no legado: `src/pages/admin/AdminPermissoes.tsx`
  - Critério de pronto: salvar A→B cria ou preserva B→A e gera request do ciclo aberto quando previsto.
  - Confiança: 🟢

- [ ] T-05, Implementar ciclo de vida de ciclos e geração de requests.
  - Origem no legado: `src/pages/admin/AdminCiclos.tsx`, `src/lib/generateFeedbackRequests.ts`
  - Critério de pronto: criar, abrir, fechar, publicar e arquivar respeita estados, concorrência de frequência e permissões ativas.
  - Confiança: 🟢

- [ ] T-06, Implementar gestão de formulários, perguntas e ordem de perguntas.
  - Origem no legado: `src/pages/admin/AdminFormularios.tsx`
  - Critério de pronto: formulários 360° e de cliente podem ser criados/editados e suas perguntas persistem na ordem apresentada.
  - Confiança: 🟢

- [ ] T-07, Implementar dashboard administrativo e relatórios operacionais.
  - Origem no legado: `src/pages/AdminDashboard.tsx`, `src/pages/admin/AdminRelatorios.tsx`
  - Critério de pronto: cards, filtros, agregações, preview e CSV exibem/exportam dados compatíveis com o filtro ativo.
  - Confiança: 🟢

- [ ] T-08, Implementar relatório executivo em PDF e envio por email.
  - Origem no legado: `src/pages/admin/AdminRelatorioFeedback.tsx`
  - Critério de pronto: os três escopos válidos calculam métricas, geram PDF A4 e informam falhas de geração ou email sem travar a tela.
  - Confiança: 🟢

- [ ] T-09, Implementar configurações globais, auditoria, atualizações e notificações administrativas.
  - Origem no legado: `src/pages/admin/AdminConfiguracoes.tsx`, `src/pages/admin/AdminAuditoria.tsx`, `src/pages/admin/AdminAtualizacoes.tsx`
  - Critério de pronto: configurações e eventos reaparecem após recarregar e operações críticas registram ator, ação e detalhes.
  - Confiança: 🟢

- [ ] T-10, Confirmar e implementar contratos server-side das Edge Functions e políticas RLS.
  - Origem no legado: `supabase/functions/`, `supabase/migrations/`
  - Critério de pronto: payloads, autorização, erros e isolamento de dados estão cobertos por testes de integração.
  - Confiança: 🔴

## Tarefas de Teste

- [ ] TT-01, Testar acesso permitido e negado às rotas administrativas.
- [ ] TT-02, Testar criação de ciclo, geração de requests e bloqueio de concorrência indevida.
- [ ] TT-03, Testar criação da permissão reversa peer-to-peer.
- [ ] TT-04, Testar filtros, ordenação, preview e exportação CSV dos relatórios.
- [ ] TT-05, Testar geração de PDF nos escopos individual e geral e falha de email.
- [ ] TT-06, Testar RLS e autorização das Edge Functions com perfis de cada papel.

## Tarefas de Migração de Dados (se aplicável)

- [ ] TM-01, Validar migrations e compatibilidade das tabelas administrativas antes de qualquer migração.

## Ordem Sugerida

1. Implementar autenticação, papéis e perfis, pois as demais telas dependem do contexto de acesso.
2. Implementar departamentos, permissões, formulários e ciclos antes dos dashboards e relatórios.
3. Implementar relatórios e PDF após estabilizar requests, respostas e ciclos.
4. Implementar auditoria, configurações e integrações server-side junto aos testes de segurança.

## Lacunas Pendentes (🔴)

- Confirmar políticas RLS por tabela e por papel.
- Confirmar contratos, limites, autenticação e formatos de erro das Edge Functions.
- Confirmar estratégia de migração e retenção dos dados administrativos.
