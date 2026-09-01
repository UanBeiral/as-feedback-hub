# Unidade: Coordenação de Equipe — Tarefas de Implementação

> Sequência para reimplementar a unidade sem acesso ao legado original. 🟢 confirmado; 🟡 inferido; 🔴 depende de validação.

## Pré-requisitos

- [ ] Disponibilizar autenticação Supabase e cliente tipado.
- [ ] Confirmar migrations e políticas RLS para `profiles`, `coordinator_members`, `feedback_requests`, `feedback_answers`, `feedback_form_questions`, `feedback_cycles`, `client_feedbacks`, `audit_logs` e `notifications`. 🔴
- [ ] Disponibilizar React Query, roteamento protegido, componentes de estado vazio/loading e exportação XLSX.
- [ ] Documentar variáveis de ambiente do Supabase e permissões dos papéis `coordenador`, `gestor`, `admin` e `rh`. 🔴

## Tarefas

- [ ] T-01, Implementar a rota protegida e o carregamento da identidade do coordenador.
  - Origem no legado: `src/App.tsx`, `src/components/ProtectedRoute.tsx`, `src/pages/coordenador/CoordenadorInicio.tsx`
  - Critério de pronto: usuário autenticado e perfil autorizado acessam as quatro telas; usuário inativo ou não autorizado recebe o estado de bloqueio; a query não executa sem `userId`.
  - Confiança: 🟢 para o fluxo de sessão; 🟡 para a autorização server-side.

- [ ] T-02, Construir o carregamento da equipe pela união de subordinados diretos e associações explícitas.
  - Origem no legado: `src/pages/coordenador/CoordenadorInicio.tsx`, `src/pages/coordenador/CoordenadorEquipe.tsx`
  - Critério de pronto: perfis ativos de `profiles.manager_id` e `coordinator_members` são combinados, deduplicados por `id` e apresentados uma única vez.
  - Confiança: 🟢

- [ ] T-03, Implementar o dashboard do coordenador com queries remotas e estados de carregamento/vazio.
  - Origem no legado: `src/pages/coordenador/CoordenadorInicio.tsx`
  - Critério de pronto: a tela exibe total de membros, pendências, taxa de conclusão, ciclo aberto, leituras pendentes, próximos vencimentos e mensagens coerentes quando não há dados.
  - Confiança: 🟢

- [ ] T-04, Implementar as agregações de requests, progresso, atraso e membros sem progresso.
  - Origem no legado: `src/pages/coordenador/CoordenadorInicio.tsx`, `src/pages/coordenador/CoordenadorEquipe.tsx`
  - Critério de pronto: `cancelled` e `waived` são excluídos do progresso; `submitted` é contado como concluído; pendências e atrasos respeitam status, ciclo aberto e janela temporal observada.
  - Confiança: 🟢

- [ ] T-05, Implementar gráficos e indicadores de rating do ciclo.
  - Origem no legado: `src/pages/coordenador/CoordenadorInicio.tsx`
  - Critério de pronto: respostas de perguntas do tipo rating são agregadas por membro, os três melhores e membros com média inferior a 3.0 são identificados, e a ausência de respostas produz estado vazio.
  - Confiança: 🟢

- [ ] T-06, Implementar a tela de equipe com progresso individual, leituras pendentes e filtros.
  - Origem no legado: `src/pages/coordenador/CoordenadorEquipe.tsx`
  - Critério de pronto: cada membro exibe status e contagens derivadas dos requests do escopo, com atualização após mutações e sem duplicidade.
  - Confiança: 🟢

- [ ] T-07, Implementar solicitação de feedback de cliente e exportação da equipe.
  - Origem no legado: `src/pages/coordenador/CoordenadorEquipe.tsx`, `src/components/ClientFeedbackDashboard.tsx`
  - Critério de pronto: o coordenador consegue iniciar a solicitação para um membro autorizado e exportar a tabela filtrada no formato esperado; o contrato exato do arquivo deve ser validado. 🔴
  - Confiança: 🟡

- [ ] T-08, Implementar remoção e associação de membros com efeitos auxiliares.
  - Origem no legado: `src/pages/coordenador/CoordenadorEquipe.tsx`, `src/lib/createAuditLog.ts`, `src/hooks/useCreateNotification.ts`
  - Critério de pronto: a associação é persistida, a lista é atualizada, `audit_logs` é tentado e o membro removido recebe notificação quando o serviço estiver disponível.
  - Confiança: 🟢 para a sequência observada; 🟡 para tolerância a falha dos efeitos auxiliares.

- [ ] T-09, Implementar a tela de pendências com agrupamento, busca, status e janela de vencimento.
  - Origem no legado: `src/pages/coordenador/CoordenadorPendentes.tsx`
  - Critério de pronto: somente requests do escopo e da janela de até três dias anteriores aparecem; a lista pode ser agrupada por avaliador e filtrada sem alterar os dados persistidos.
  - Confiança: 🟢

- [ ] T-10, Implementar cancelamento de request com justificativa e auditoria.
  - Origem no legado: `src/pages/coordenador/CoordenadorPendentes.tsx`, `src/lib/createAuditLog.ts`
  - Critério de pronto: confirmação válida altera o request para `cancelled`, registra justificativa conforme o schema disponível, invalida queries e comunica falha sem falsificar sucesso.
  - Confiança: 🟢 para a transição; 🔴 para o campo persistido da justificativa se não estiver confirmado no schema.

- [ ] T-11, Implementar histórico interno e visualização de respostas.
  - Origem no legado: `src/pages/coordenador/CoordenadorHistorico.tsx`, `src/pages/gestor/GestorHistorico.tsx`
  - Critério de pronto: o coordenador visualiza ciclo, avaliador, avaliado, status e respostas autorizadas, com filtros e modal de detalhe equivalentes ao comportamento observado.
  - Confiança: 🟡

- [ ] T-12, Implementar dashboard e modal de avaliações de clientes.
  - Origem no legado: `src/components/ClientFeedbackDashboard.tsx`, `src/components/ClientFeedbackModal.tsx`, `src/pages/coordenador/CoordenadorInicio.tsx`
  - Critério de pronto: avaliações do escopo podem ser filtradas por sinal positivo/negativo, exibem nota e alertas, e o detalhe mostra dados, tags, mensagem e respostas.
  - Confiança: 🟢

- [ ] T-13, Implementar ações condicionais de abdicar e retomar avaliação.
  - Origem no legado: `src/pages/coordenador/CoordenadorPendentes.tsx`
  - Critério de pronto: cada ação aparece somente para o estado elegível, exige confirmação e atualiza o status para o valor observado (`waived` ou `pending`).
  - Confiança: 🟢

- [ ] T-14, Integrar banners e widgets de ciclo, lembrete e comparação.
  - Origem no legado: `src/pages/coordenador/CoordenadorInicio.tsx`, `src/components/CycleClosedBanner.tsx`, `src/components/CycleDeadlineBanner.tsx`, `src/components/ReminderButton.tsx`, `src/components/CycleComparison.tsx`
  - Critério de pronto: os widgets recebem `userId`, `teamIds` e ciclo quando necessário, não bloqueiam o dashboard e respeitam estado vazio/fechado.
  - Confiança: 🟢

- [ ] T-15, Validar isolamento de dados e autorização no banco.
  - Origem no legado: `supabase/migrations`, `src/components/ProtectedRoute.tsx`, `src/pages/coordenador/*.tsx`
  - Critério de pronto: testes com coordenadores distintos comprovam que nenhuma query, mutação ou avaliação de cliente atravessa o escopo autorizado.
  - Confiança: 🔴

## Tarefas de Teste

- [ ] TT-01, Testar composição deduplicada da equipe com membros presentes nas duas fontes.
- [ ] TT-02, Testar dashboard sem usuário, sem equipe, sem ciclo e sem respostas de rating.
- [ ] TT-03, Testar cálculo de progresso excluindo `cancelled` e `waived`.
- [ ] TT-04, Testar filtros de pendências, janela de vencimento e agrupamento por avaliador.
- [ ] TT-05, Testar cancelamento, abdicação, retomada e invalidação das queries.
- [ ] TT-06, Testar falha de auditoria/notificação sem mascarar o resultado principal.
- [ ] TT-07, Testar histórico, detalhe de respostas e avaliações de clientes positivas/negativas.
- [ ] TT-08, Testar RLS e autorização entre coordenadores com equipes diferentes. 🔴

## Tarefas de Migração de Dados (se aplicável)

- [ ] TM-01, Validar índices e chaves estrangeiras para `coordinator_members`, `feedback_requests`, `feedback_answers` e `client_feedbacks`.
- [ ] TM-02, Confirmar compatibilidade dos status legados `pending`, `draft`, `submitted`, `cancelled` e `waived`.
- [ ] TM-03, Definir migração de auditoria e notificações caso o schema de destino não preserve os campos usados pelo frontend. 🔴

## Ordem Sugerida

1. T-01 e T-02, porque sessão e escopo determinam todas as consultas seguintes.
2. T-03 a T-05, para disponibilizar o dashboard e suas agregações.
3. T-06 a T-10, para implementar a operação de equipe e pendências.
4. T-11 a T-14, para histórico, clientes e widgets complementares.
5. T-15 e TT-01 a TT-08, antes de considerar a unidade pronta para produção.

## Lacunas Pendentes (🔴)

- Confirmar políticas RLS e autorização server-side de cada tabela e mutação.
- Confirmar o campo e o contrato persistido da justificativa de cancelamento.
- Confirmar o formato final da exportação XLSX e o escopo de dados exportável.
- Confirmar se o histórico do coordenador deve reutilizar integralmente o histórico do gestor.
