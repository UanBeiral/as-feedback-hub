# Unidade: Coordenação de Equipe

> Contrato de requisitos extraído do módulo `src/pages/coordenador`. Cada afirmação está classificada por confiança.

## Visão Geral

A unidade de Coordenação permite supervisionar uma equipe formada por subordinados diretos e membros explicitamente associados ao coordenador. 🟢 Ela consolida o andamento dos ciclos de feedback, evidencia pendências e atrasos, disponibiliza histórico de avaliações e integra a visualização de avaliações de clientes. 🟢

## Responsabilidades

- Consolidar subordinados diretos e membros de `coordinator_members`, removendo duplicidades. 🟢
- Exibir métricas de equipe, progresso do ciclo aberto, pendências, atrasos e leituras não realizadas. 🟢
- Consultar e filtrar membros, requests de feedback e histórico de respostas. 🟢
- Permitir ações operacionais sobre requests, incluindo cancelamento com justificativa, abdicação e retomada quando disponíveis. 🟢
- Exibir avaliações de clientes e seus detalhes para os membros do escopo coordenado. 🟢
- Registrar auditoria e tentar notificar o membro quando ele for removido da equipe. 🟢

## Regras de Negócio

- A equipe é a união dos subordinados cujo `manager_id` corresponde ao coordenador com os membros de `coordinator_members`; perfis duplicados são removidos pelo identificador. 🟢 (`src/pages/coordenador/CoordenadorInicio.tsx`)
- O progresso do ciclo exclui requests com status `cancelled` e `waived`; requests `submitted` contam como concluídos. 🟢 (`src/pages/coordenador/CoordenadorEquipe.tsx`)
- Pendências principais correspondem a requests com status `pending` ou `draft`. 🟢 (`src/pages/coordenador/CoordenadorEquipe.tsx`)
- A seção de atrasos considera o ciclo aberto, requests pendentes vencidos e vencimento dentro da janela visual de até três dias. 🟢 (`src/pages/coordenador/CoordenadorInicio.tsx`)
- A remoção de membro grava um evento em `audit_logs` e tenta criar uma notificação para o membro removido. 🟢 (`src/pages/coordenador/CoordenadorEquipe.tsx`)
- O acesso efetivo aos dados depende também das políticas RLS do Supabase. 🟡 (a autorização no banco não é comprovada apenas pelos componentes do módulo)
- O comportamento server-side para cada ação de coordenação não foi confirmado no frontend. 🔴

## Validação humana — 2026-08-25

- 🟢 Auditoria usa `audit_logs.actor_id`, não `user_id`.
- 🟡 Exportações departamentais usam fallback para `profiles.department_id` enquanto `profile_departments` não está consolidado.
- 🔴 O contrato completo do XLSX e todos os campos obrigatórios de justificativa/notificação ainda não foram definidos.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Montar a equipe coordenada a partir de subordinados diretos e membros associados, sem duplicidades. | Must | Dado um coordenador com membros nas duas fontes, quando a equipe carregar, então cada perfil ativo aparece uma única vez. |
| RF-02 | Exibir dashboard com total de membros, pendências, taxa de conclusão e ciclo aberto. | Must | Dado um ciclo aberto e requests da equipe, quando o coordenador abrir o início, então as métricas refletem os registros consultados. |
| RF-03 | Exibir progresso acumulado e identificar membros sem nenhum feedback enviado no ciclo aberto. | Should | Dado um membro com requests não cancelados e nenhum request `submitted`, quando o dashboard carregar, então ele aparece na lista de atenção. |
| RF-04 | Listar membros com status, requests e progresso individual. | Must | Dado um membro no escopo do coordenador, quando a equipe for consultada, então seus requests são agrupados e os status são apresentados. |
| RF-05 | Filtrar pendências por busca, membro e status, incluindo requests `pending` e `draft`. | Must | Dado um conjunto de pendências, quando um filtro for aplicado, então somente requests compatíveis permanecem visíveis. |
| RF-06 | Cancelar uma pendência com justificativa e registrar a operação. | Should | Dado um request pendente, quando o coordenador confirmar o cancelamento com justificativa, então o request deixa de ser pendente e a ação fica auditável. |
| RF-07 | Consultar histórico de feedbacks internos e visualizar respostas detalhadas. | Should | Dado um feedback submetido, quando o coordenador abrir o histórico e selecionar o item, então ciclo, participantes e respostas disponíveis são exibidos. |
| RF-08 | Exibir avaliações de clientes vinculadas aos membros coordenados, com filtros e detalhe. | Should | Dado uma avaliação de cliente no escopo, quando o coordenador filtrar por resultado, então os itens correspondentes aparecem e podem abrir o detalhe. |
| RF-09 | Permitir ações de abdicar e retomar avaliação quando o estado do request permitir. | Could | Dado um request elegível, quando a ação for confirmada, então o status persistido e a mensagem da interface refletem a transição. |
| RF-10 | Remover membro da associação de coordenação. | Should | Dado um membro associado, quando o coordenador confirmar a remoção, então a associação é removida, a equipe é atualizada e a auditoria é tentada. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência no código | Confiança |
|------|--------------------|---------------------|-----------|
| Segurança | A unidade deve ser acessível somente a uma sessão e a um perfil autorizado pela aplicação. | `src/App.tsx`, `src/components/ProtectedRoute.tsx` | 🟡 |
| Performance | Consultas independentes de perfil, equipe, requests, ciclo e métricas devem poder ser carregadas em paralelo/cache. | `src/pages/coordenador/CoordenadorInicio.tsx`, uso de `useQuery` e `Promise.all` | 🟢 |
| Disponibilidade | Falhas auxiliares de auditoria ou notificação devem ser informadas sem mascarar o resultado da ação principal, quando a persistência principal tiver sucesso. | `src/pages/coordenador/CoordenadorEquipe.tsx` | 🟡 |
| Consistência | Métricas de conclusão devem excluir `cancelled` e `waived` conforme a regra do módulo. | `src/pages/coordenador/CoordenadorEquipe.tsx` | 🟢 |

> Os requisitos não funcionais são inferidos do frontend e devem ser validados com a configuração de operação e as políticas do Supabase.

## Critérios de Aceitação

```gherkin
Dado um coordenador autenticado com subordinados diretos e membros associados
Quando ele abrir a área de coordenação
Então a equipe exibida será a união deduplicada dessas fontes

Dado um ciclo aberto com requests da equipe
Quando o dashboard for carregado
Então serão exibidos pendências, taxa de conclusão, atrasos e progresso do ciclo

Dado um request com status pending ou draft e vencimento dentro da janela de pendências
Quando o coordenador abrir a tela de pendências
Então o request aparecerá e poderá ser localizado por busca ou filtro

Dado um request elegível para cancelamento
Quando o coordenador confirmar o cancelamento com justificativa
Então o request será atualizado e a justificativa ficará associada à ação auditada, se o registro auxiliar estiver disponível

Dado um feedback submetido com respostas
Quando o coordenador abrir o histórico e selecionar o feedback
Então o sistema exibirá os dados do ciclo e as respostas autorizadas

Dado uma avaliação de cliente pertencente ao escopo da equipe
Quando o coordenador aplicar filtro positivo, negativo ou abrir o detalhe
Então a lista será filtrada ou o formulário completo será exibido

Dado uma falha de consulta ou mutação
Quando a operação terminar com erro
Então a interface informará a falha e não apresentará a alteração como concluída
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Composição da equipe e dashboard | Must | Caminho central da supervisão coordenada. |
| Pendências, filtros e progresso | Must | Ação operacional recorrente do módulo. |
| Histórico e respostas | Should | Necessário para acompanhamento, mas não inicia o ciclo. |
| Avaliações de clientes | Should | Capacidade funcional integrada ao acompanhamento da equipe. |
| Cancelamento e remoção com auditoria | Should | Ações administrativas relevantes, com dependência de registros auxiliares. |
| Abdicar e retomar avaliação | Could | Fluxos condicionais e menos frequentes. |
| Regras server-side não observadas | Won't | Não há evidência suficiente no frontend para especificar o contrato. |

> A prioridade foi inferida pela frequência de uso, posição no fluxo e dependências identificadas. 🟡

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/coordenador/CoordenadorInicio.tsx` | `CoordenadorInicio`, composição da equipe e métricas | 🟢 |
| `src/pages/coordenador/CoordenadorEquipe.tsx` | listagem, progresso, ações sobre membros e requests | 🟢 |
| `src/pages/coordenador/CoordenadorPendentes.tsx` | pendências, filtros e cancelamento | 🟢 |
| `src/pages/coordenador/CoordenadorHistorico.tsx` | histórico, filtros e detalhe de respostas | 🟢 |
| `src/components/ClientFeedbackDashboard.tsx` | avaliações de clientes no dashboard coordenado | 🟢 |
| `src/components/ClientFeedbackModal.tsx` | detalhe das respostas de cliente | 🟢 |
| `src/components/ProtectedRoute.tsx` | proteção de acesso por sessão/papel | 🟡 |
| `src/lib/createAuditLog.ts` | registro auxiliar de auditoria | 🟢 |
| `src/hooks/useCreateNotification.ts` | notificação auxiliar após ações | 🟢 |
