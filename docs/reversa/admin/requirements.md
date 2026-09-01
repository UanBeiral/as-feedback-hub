# Unidade: Administração

## Visão Geral

A unidade de administração centraliza o controle operacional do A&S Feedback Hub. Ela permite administrar pessoas, departamentos, formulários, permissões, ciclos de feedback, configurações, auditoria e relatórios.

## Responsabilidades

- Gerenciar usuários, papéis, status, departamentos e flags de capacidade.
- Configurar permissões de avaliação, formulários e ciclos de feedback.
- Acompanhar métricas, auditoria, notificações e relatórios administrativos.
- Controlar configurações globais de acesso, branding e integrações operacionais.

## Regras de Negócio

- Somente rotas com papel `admin` ou `rh` permitem gestão administrativa. 🟢
- A abertura de um ciclo usa permissões ativas para gerar requests de feedback. 🟢
- Ciclos da mesma frequência têm limite operacional de concorrência e geram alerta quando a janela está ocupada. 🟢
- Permissões `peer_to_peer` devem criar a relação reversa quando ela não existir. 🟢
- Usuários podem ser inativados por alteração de status, preservando o histórico. 🟢
- A autorização definitiva de consultas e mutações depende também das políticas RLS do Supabase. 🟡
- O contrato completo de notificações e Edge Functions administrativas não foi confirmado no frontend. 🔴

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Listar e editar usuários com papel, status, departamento e flags de capacidade. | Must | Dado um administrador autenticado, quando salvar um perfil, então os dados e flags ficam persistidos e a lista é atualizada. |
| RF-02 | Criar, abrir, fechar, publicar, arquivar e reabrir ciclos conforme o estado atual. | Must | Dado um ciclo em estado permitido, quando o administrador executar a transição, então o status persistido e os indicadores da tela refletem o novo estado. |
| RF-03 | Gerenciar permissões de feedback por avaliador, avaliado, tipo e ciclo. | Must | Dado um par com permissão peer-to-peer, quando a permissão for criada, então a relação reversa é criada ou preservada. |
| RF-04 | Gerenciar formulários 360° e de cliente, incluindo perguntas e ordenação. | Should | Dado um formulário editável, quando uma pergunta for criada ou reordenada, então a configuração aparece na próxima consulta do formulário. |
| RF-05 | Consultar relatórios administrativos de clientes, feedbacks livres, 360° e engajamento. | Must | Dado um filtro selecionado, quando a consulta terminar, então a tabela contém somente registros compatíveis e a exportação inclui todos os resultados filtrados. |
| RF-06 | Consultar auditoria e filtrar eventos administrativos. | Should | Dado um evento registrado, quando o administrador abrir a auditoria, então o evento aparece com ator, ação, registro e detalhes disponíveis. |
| RF-07 | Configurar nome, logo, templates, motivações e flags globais de acesso. | Should | Dado um administrador, quando salvar uma configuração, então os componentes consumidores passam a usar o valor persistido. |
| RF-08 | Exibir métricas consolidadas do sistema e alertas operacionais. | Must | Dado um ciclo aberto, quando o dashboard carregar, então exibe progresso, usuários, pendências e atividade do ciclo. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência no código | Confiança |
|------|--------------------|---------------------|-----------|
| Segurança | Rotas administrativas exigem autenticação e papel `admin` ou `rh`. | `src/App.tsx`, `src/components/ProtectedRoute.tsx` | 🟢 |
| Performance | Consultas independentes de dashboard e listas devem poder carregar em paralelo/cache. | `src/pages/AdminDashboard.tsx`, uso de React Query | 🟢 |
| Disponibilidade | Falhas de auditoria/notificação não devem necessariamente impedir a operação principal. | `src/pages/admin/AdminEquipe.tsx`, `src/lib/createAuditLog.ts` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um administrador autenticado
Quando ele abre a área administrativa
Então o sistema permite acessar somente funcionalidades compatíveis com admin ou rh

Dado um ciclo em estado draft com permissões ativas
Quando o administrador o abre
Então o ciclo passa para open e requests são gerados para os pares elegíveis

Dado um ciclo com frequência já representada por ciclos abertos
Quando o administrador tenta abrir outro ciclo da mesma frequência
Então o sistema aplica a regra de concorrência e exibe o alerta correspondente

Dado uma permissão peer_to_peer de A para B sem permissão reversa
Quando o administrador salva a permissão
Então o sistema cria também a permissão de B para A

Dado uma tentativa de salvar um perfil ou configuração inválida
Quando a persistência retornar erro
Então o sistema informa a falha e não apresenta a alteração como concluída
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Gestão de usuários e papéis | Must | Controla acesso a toda a aplicação. |
| Ciclos e geração de requests | Must | Caminho central do produto de feedback. |
| Permissões de avaliação | Must | Determina os pares e tipos de feedback. |
| Dashboard administrativo | Must | Visibilidade operacional para administração. |
| Relatórios | Must | Capacidade explícita e usada por múltiplos papéis. |
| Formulários e configurações | Should | Necessários para adaptar a operação, com defaults existentes. |
| Auditoria e broadcasts | Should | Importantes para governança, mas não iniciam o ciclo. |
| Integrações de agenda | Could | Funcionalidade complementar e condicionada a configuração. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/AdminDashboard.tsx` | `AdminDashboard` | 🟢 |
| `src/pages/admin/AdminUsuarios.tsx` | CRUD de perfis | 🟢 |
| `src/pages/admin/AdminPermissoes.tsx` | `ensureReversePeerPermission` e gestão de permissões | 🟢 |
| `src/pages/admin/AdminCiclos.tsx` | transições de ciclo e geração de requests | 🟢 |
| `src/pages/admin/AdminFormularios.tsx` | gestão de formulários e perguntas | 🟢 |
| `src/pages/admin/AdminRelatorios.tsx` | relatórios operacionais | 🟢 |
| `src/pages/admin/AdminRelatorioFeedback.tsx` | relatório executivo PDF/email | 🟢 |
| `src/pages/admin/AdminConfiguracoes.tsx` | configurações globais | 🟢 |
| `src/pages/admin/AdminAuditoria.tsx` | consulta de auditoria | 🟢 |
| `src/components/ProtectedRoute.tsx` | proteção de rotas por papel | 🟢 |
