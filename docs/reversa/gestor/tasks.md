# Unidade: Gestor, Tarefas de Implementação

## Pré-requisitos

- [ ] Dependências listadas em `design.md` disponíveis.
- [ ] Schema e migrations compatíveis com perfis, requests, ciclos, respostas, equipe e notificações.
- [ ] Variáveis de ambiente do Supabase e configurações globais documentadas.
- [ ] Escopo de RLS para gestores confirmado. 🔴

## Tarefas

- [ ] T-01, Implementar proteção de rotas e resolução do gestor ativo.
  - Origem no legado: `src/App.tsx`, `src/components/ProtectedRoute.tsx`, `src/contexts/AuthContext.tsx`
  - Critério de pronto: somente sessões autorizadas chegam às telas de gestor e o contexto ativo é consistente.
  - Confiança: 🟢

- [ ] T-02, Implementar consulta de equipe por subordinados diretos.
  - Origem no legado: `src/pages/gestor/GestorInicio.tsx`, `src/pages/gestor/GestorEquipe.tsx`
  - Critério de pronto: membros ativos associados ao gestor aparecem sem incluir pessoas fora do escopo.
  - Confiança: 🟢

- [ ] T-03, Implementar dashboard com agregação de ciclo, requests, prazos, leituras e notas.
  - Origem no legado: `src/pages/gestor/GestorInicio.tsx`
  - Critério de pronto: totais, taxa de conclusão, atrasos e gráficos coincidem com os requests elegíveis.
  - Confiança: 🟢

- [ ] T-04, Implementar listagem de equipe com progresso e ações.
  - Origem no legado: `src/pages/gestor/GestorEquipe.tsx`
  - Critério de pronto: cada membro exibe enviados, pendentes e progresso; inclusão/remoção atualiza a lista.
  - Confiança: 🟢

- [ ] T-05, Implementar pendências agrupadas por avaliador, busca e filtro.
  - Origem no legado: `src/pages/gestor/GestorPendentes.tsx`
  - Critério de pronto: itens `pending`/`draft` são agrupados, filtráveis e classificados visualmente por atraso.
  - Confiança: 🟢

- [ ] T-06, Implementar cancelamento de request com justificativa e auditoria.
  - Origem no legado: `src/pages/gestor/GestorPendentes.tsx`, `src/lib/createAuditLog.ts`
  - Critério de pronto: request passa a `cancelled`, justificativa é preservada e erro é informado sem falso sucesso.
  - Confiança: 🟢

- [ ] T-07, Implementar histórico da equipe e detalhes de feedback.
  - Origem no legado: `src/pages/gestor/GestorHistorico.tsx`
  - Critério de pronto: histórico filtra ciclos/status, exibe respostas permitidas e suporta ações previstas para o ciclo aberto.
  - Confiança: 🟢

- [ ] T-08, Implementar solicitação de avaliação de cliente e lembretes.
  - Origem no legado: `src/components/RequestClientFeedbackModal.tsx`, `src/components/ReminderButton.tsx`
  - Critério de pronto: solicitação/lembrete cria a operação esperada e informa sucesso ou falha.
  - Confiança: 🟢

- [ ] T-09, Implementar visibilidade condicional de relatórios e agenda.
  - Origem no legado: `src/components/layout/AppSidebar.tsx`, `src/pages/admin/AdminConfiguracoes.tsx`
  - Critério de pronto: menus refletem `gestor_can_access_reports` e `gestor_can_access_agenda` sem estados inconsistentes.
  - Confiança: 🟢

- [ ] T-10, Confirmar RLS e contratos de notificações para o escopo de gestor.
  - Origem no legado: `supabase/migrations/`, `supabase/functions/`
  - Critério de pronto: testes com gestor de outra equipe não acessam nem alteram dados indevidos.
  - Confiança: 🔴

## Tarefas de Teste

- [ ] TT-01, Testar dashboard com equipe vazia, requests pendentes e ciclo sem requests.
- [ ] TT-02, Testar cálculo de progresso excluindo `cancelled` e `waived`.
- [ ] TT-03, Testar agrupamento e filtro de pendências por avaliador/status.
- [ ] TT-04, Testar cancelamento com sucesso e falha de persistência.
- [ ] TT-05, Testar visibilidade de relatórios/agenda para configurações true e false.
- [ ] TT-06, Testar isolamento RLS entre gestores.

## Tarefas de Migração de Dados (se aplicável)

- [ ] TM-01, Validar associações históricas `manager_id` antes de migrar dados de equipe.

## Ordem Sugerida

1. Implementar autenticação e escopo da equipe.
2. Implementar dashboard, equipe e pendências sobre o escopo validado.
3. Implementar histórico, cliente, lembretes e navegação opcional.
4. Finalizar RLS, integrações e testes de regressão.

## Lacunas Pendentes (🔴)

- Confirmar se a autorização server-side limita todas as consultas ao time do gestor.
- Confirmar payload, retry e destinatários do lembrete.
- Confirmar política para gestor sem equipe ou com membro inativo.
