# Matriz de Permissões

## Rotas por papel

| Capacidade | Colaborador | Gestor | Coordenador | Admin/RH | Confiança |
|---|:---:|:---:|:---:|:---:|---|
| Dashboard próprio e feedbacks | sim | sim | sim | sim | 🟢 CONFIRMADO |
| Gestão de equipe direta | não | sim | sim | sim | 🟢 CONFIRMADO |
| Relatórios operacionais | por flag/config | sim, sujeito a config | sim | sim | 🟢 CONFIRMADO |
| Relatório executivo | próprio por rota; contexto conforme papel | sim | sim | sim | 🟢 CONFIRMADO |
| Gestão de usuários/ciclos/permissões | não | não | não | sim | 🟢 CONFIRMADO |
| Auditoria e configurações | não | não | não | sim | 🟢 CONFIRMADO |
| Avaliação pública de cliente | sem autenticação | sem autenticação | sem autenticação | sem autenticação | 🟢 CONFIRMADO |

## Flags por perfil

| Flag | Efeito observado | Confiança |
|---|---|---|
| `can_request_client_feedback` | Permite solicitar avaliação de cliente. | 🟢 CONFIRMADO |
| `can_view_feedback_answers` | Permite abrir respostas de avaliações de cliente. | 🟢 CONFIRMADO |
| `can_view_team_history` | Permite histórico de equipe ao colaborador. | 🟢 CONFIRMADO |
| `can_generate_reports` | Permite relatório de clientes ao colaborador. | 🟢 CONFIRMADO |
| `can_view_manager_dashboard` | Permite dashboard de gestão ao colaborador. | 🟢 CONFIRMADO |
| `is_coordinator` | Adiciona contexto de coordenador e membros coordenados. | 🟢 CONFIRMADO |

## Configurações globais

- `gestor_can_access_reports` controla a exibição de relatórios para gestores.
- `gestor_can_access_agenda` controla a exibição da agenda para gestores.
- `colaborador_can_generate_own_report` controla a opção de relatório próprio no menu.

🟡 **INFERIDO:** as configurações controlam principalmente navegação e visibilidade; a autorização definitiva precisa ser conferida nas políticas RLS e Edge Functions.

## Observações

`ProtectedRoute` aceita o papel armazenado e o `activeRole`. Admin e RH podem assumir contexto de gestor; coordenadores podem ser habilitados por `is_coordinator`. Há risco de divergência entre a rota acessível e a flag de funcionalidade quando a proteção é feita apenas por redirecionamento de componente.
# Validação humana — 2026-08-25

- 🟢 O contrato canônico é negar por padrão: escopo vazio/nulo, flag ausente ou parâmetro fora do escopo não concede acesso.
- 🟢 O isolamento é server-side + RLS; UI, menu e rota não são controles suficientes isoladamente.
- 🟢 Gestores e coordenadores ficam limitados às equipes autorizadas; colaboradores não acessam rotas de liderança; admin possui escopo global no histórico administrativo.
- 🟡 A matriz completa tabela × papel das policies efetivas ainda precisa ser extraída do banco de produção.
- 🔴 Permanecem ajustes a validar em `team_requests`, `profiles.job_title` e permissões de RH.
