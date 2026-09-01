# Unidade: Colaborador

> Requisitos extraídos dos fluxos de avaliações de clientes, dashboard, histórico de equipe e relatórios disponíveis ao colaborador.

## Visão Geral

A unidade Colaborador oferece recursos opcionais para acompanhar avaliações de clientes e, conforme as flags do perfil, consultar respostas, dashboard, histórico de equipe e relatórios. 🟢 O escopo é controlado por permissões independentes gravadas em `profiles`. 🟢

## Responsabilidades

- Listar avaliações de clientes e seus estados para os perfis permitidos. 🟢
- Solicitar novas avaliações para profissionais ativos. 🟢
- Filtrar avaliações por profissional, cliente, WhatsApp, status e período. 🟢
- Exibir dashboard de avaliações de clientes quando `can_view_manager_dashboard` permitir. 🟢
- Reutilizar o histórico de equipe quando `can_view_team_history` permitir. 🟢
- Gerar CSV com resultados filtrados quando `can_generate_reports` permitir. 🟢
- Restringir a abertura de respostas detalhadas quando `can_view_feedback_answers` estiver desabilitada. 🟢

## Regras de Negócio

- Somente perfis com `status = active` aparecem como opção para solicitar avaliação. 🟢 (`src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx`)
- Estados `pending` e `in_progress` são tratados como pendentes; `submitted` como respondido; `expired` como expirado. 🟢 (`src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx`)
- A flag `can_view_feedback_answers` controla o acesso às respostas submetidas de avaliações de clientes. 🟢
- A flag `can_view_manager_dashboard` controla o acesso ao dashboard de clientes; quando explicitamente falsa, a página redireciona para a raiz. 🟢
- A flag `can_view_team_history` controla o acesso ao histórico da equipe; quando falsa, a página redireciona para a raiz. 🟢
- A flag `can_generate_reports` controla o acesso aos relatórios e à exportação CSV; quando falsa, a página redireciona para a raiz. 🟢
- O WhatsApp é mascarado na apresentação da listagem. 🟢
- A exportação CSV usa os registros após os filtros atuais e separador ponto e vírgula. 🟢
- A autorização efetiva das consultas amplas depende também das políticas RLS do Supabase. 🟡
- O contrato detalhado dos modais reutilizados para solicitar e visualizar avaliações não foi especificado dentro desta unit. 🔴

## Validação humana — 2026-08-25

- 🟢 Remoção de usuário preserva histórico por soft-delete lógico (`status = 'deleted'`).
- 🟢 Acesso a histórico e relatórios respeita escopo server-side; colaborador só acessa o próprio relatório.
- 🟡 Retenção, anonimização e exportação completa de dados sensíveis continuam pendentes.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Listar avaliações de clientes com profissional, cliente, nota, status, data e contato mascarado. | Must | Dado um colaborador autorizado, quando abrir avaliações, então os registros disponíveis são exibidos com seus campos principais e WhatsApp mascarado. |
| RF-02 | Filtrar avaliações por colaborador, cliente, WhatsApp, status e intervalo de criação. | Must | Dado um conjunto de avaliações, quando aplicar filtros, então somente registros compatíveis permanecem na lista e nas contagens. |
| RF-03 | Agregar avaliações pendentes, respondidas e expiradas. | Should | Dado avaliações em diferentes estados, quando a tela carregar, então cada registro é classificado segundo o mapeamento de status observado. |
| RF-04 | Solicitar avaliação de cliente para um perfil ativo. | Must | Dado um colaborador ativo selecionado, quando confirmar a solicitação, então o fluxo de solicitação é aberto e o registro resultante aparece após atualização. |
| RF-05 | Permitir visualizar respostas submetidas somente quando autorizado. | Must | Dado `can_view_feedback_answers = true`, quando abrir uma avaliação submetida, então as respostas ficam disponíveis; caso contrário, a ação é bloqueada ou omitida. |
| RF-06 | Exibir dashboard de avaliações de clientes conforme a permissão do perfil. | Should | Dado `can_view_manager_dashboard = true`, quando abrir o dashboard, então os dados de clientes são carregados; com a flag falsa, o usuário é redirecionado. |
| RF-07 | Exibir histórico de equipe reutilizando a visão de histórico do gestor. | Should | Dado `can_view_team_history = true`, quando abrir o histórico, então filtros e detalhes equivalentes à visão compartilhada ficam disponíveis. |
| RF-08 | Gerar relatório CSV de avaliações de clientes filtradas. | Should | Dado `can_generate_reports = true`, quando exportar, então o arquivo contém somente os registros filtrados e usa separador `;`. |
| RF-09 | Bloquear relatórios para perfil sem permissão de geração. | Should | Dado `can_generate_reports = false`, quando acessar a página de relatórios, então o usuário é redirecionado e nenhum arquivo é gerado. |
| RF-10 | Apresentar estados de loading, vazio e falha para consultas e exportação. | Must | Dado erro ou ausência de registros, quando a operação terminar, então a interface informa o estado sem apresentar dados antigos como resultado atual. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência no código | Confiança |
|------|--------------------|---------------------|-----------|
| Segurança | Acesso às páginas deve exigir sessão e papel autorizado, além das flags funcionais do perfil. | `src/App.tsx`, `src/components/ProtectedRoute.tsx`, páginas de `src/pages/colaborador/` | 🟡 |
| Privacidade | Telefones de clientes devem ser mascarados na interface de listagem. | `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx` | 🟢 |
| Performance | Consultas de perfis e avaliações devem usar cache/estado de carregamento para evitar repetição desnecessária. | `src/pages/colaborador/*.tsx`, uso de React Query | 🟢 |
| Consistência | A exportação deve refletir exatamente os filtros ativos na tela. | `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx` | 🟢 |

> Os requisitos não funcionais são inferidos do frontend; isolamento no banco e retenção de dados precisam ser validados com a equipe responsável pelo Supabase.

## Critérios de Aceitação

```gherkin
Dado um colaborador autorizado com avaliações de clientes
Quando ele abrir a tela de avaliações
Então os registros serão exibidos com status, notas, datas e contatos mascarados

Dado avaliações de diferentes colaboradores, clientes e status
Quando o colaborador aplicar filtros por pessoa, cliente, telefone, status e data
Então a lista e os indicadores mostrarão somente registros compatíveis

Dado um perfil ativo selecionado
Quando o colaborador confirmar uma solicitação de avaliação
Então o fluxo de solicitação será concluído e o novo estado poderá ser consultado

Dado uma avaliação submetida e can_view_feedback_answers igual a true
Quando o colaborador abrir o detalhe
Então as respostas autorizadas serão exibidas

Dado can_view_feedback_answers igual a false
Quando o colaborador tentar abrir respostas
Então o sistema bloqueará ou ocultará o detalhe das respostas

Dado can_generate_reports igual a true e filtros aplicados
Quando o colaborador exportar o relatório
Então o CSV conterá os resultados filtrados separados por ponto e vírgula

Dado uma flag de acesso igual a false
Quando o colaborador acessar a página correspondente
Então será redirecionado para a raiz sem consultar ou exportar dados indevidos
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Listagem, filtros e solicitação de avaliações | Must | Fluxo central da unidade. |
| Controle de respostas por permissão | Must | Regra explícita de privacidade e acesso. |
| Estados de carregamento e erro | Must | Necessários para não indicar resultado incorreto. |
| Dashboard e histórico de equipe | Should | Capacidades úteis, mas condicionais às flags do perfil. |
| Relatórios CSV | Should | Recurso operacional condicionado à permissão. |
| Métricas secundárias de status | Could | Complementam a consulta principal. |
| Contratos server-side não observados | Won't | Não há evidência suficiente nesta unit para especificá-los. |

> A prioridade foi inferida pela centralidade do fluxo de avaliações e pelas flags de capacidade do perfil. 🟡

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx` | listagem, filtros, status, permissão de respostas e solicitação | 🟢 |
| `src/pages/colaborador/ColaboradorDashboardClientes.tsx` | acesso condicionado ao dashboard de clientes | 🟢 |
| `src/pages/colaborador/ColaboradorHistoricoEquipe.tsx` | wrapper do histórico de equipe | 🟢 |
| `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx` | filtros e exportação CSV | 🟢 |
| `src/components/ClientFeedbackDashboard.tsx` | dashboard e agregação de avaliações externas | 🟢 |
| `src/components/RequestClientFeedbackModal.tsx` | solicitação de avaliação | 🟡 |
| `src/pages/gestor/GestorHistorico.tsx` | histórico reutilizado pelo colaborador | 🟡 |
| `src/components/ProtectedRoute.tsx` | proteção de rota e papel ativo | 🟡 |
