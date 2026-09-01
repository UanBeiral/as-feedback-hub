---
schemaVersion: 1
generatedAt: 2026-08-28T02:10:00Z
reversa:
  version: "1.2.60"
kind: target_screens
producedBy: screen-translator
mode: hybrid
sourcePlatform: react-spa
targetPlatform: web-nextjs
adapter: adapters/web-spa__web-spa
screenCount: 43
hash: "sha256:7f94cc99ea2f2580914b3ab24c4545a38b9d813026665a16c9fbaeb3b8400a1d"
---

# Target Screens

> Especificação executável de cada tela do sistema novo, derivada do legado segundo o modo aprovado em `screen_modernization_decision.md` (híbrido: 35 literal + 8 modernizado; SCR-0040/0045 fora do corte — AMB-007).
> Conteúdo textual preservado literalmente. Leitura primária para o codificador; o detalhe visual de cada tela literal está em `_reversa_sdd/<unit>/screens.md` + screenshot correspondente (oráculo).
> Todo valor visual referencia tokens de `_reversa_sdd/design-system/tokens.md` (+ `tokens-derived.md`). Literais hex são proibidos (DEV-003).

## Resumo

- **Modo aplicado**: híbrido
- **Telas geradas**: 43
- **Adapter**: `web-spa → web-spa` (`spec.kind: route-component` / `component-tree`)
- **Tokens consumidos**: `tokens.md` (32 semânticos) + `tokens-derived.md` (4 derivados — DEV-008)
- **Golden files**: 35 referências (screenshots do Visor; manifest em `_reversa_sdd/screens/golden/manifest.yaml`)
- **Deviations registradas**: 8 em `screen_deviation_log.md` (todas pendentes de aprovação)

## Layouts compartilhados

### Layout: AuthenticatedShell
**Origem**: `src/components/layout/AppSidebar.tsx` + header global (padrões transversais do `ui/inventory.md`)
**Modo aplicado**: literal

```yaml
spec.kind: component-tree
spec.root:
  component: AuthenticatedShell
  children:
    - component: Sidebar
      tokens: [--sidebar-background, --sidebar-foreground, --sidebar-primary, --sidebar-accent, --sidebar-border]
      children:
        - component: BrandBlock        # logo + razão social do tenant ({{tenant.name}}, {{tenant.logo_url}})
        - component: RoleMenu          # itens por papel/flags — visibilidade resolvida pela API (claims), nunca por lógica local
        - component: SidebarFooter     # botão "Sair"
    - component: Header
      children:
        - component: GlobalSearch      # busca ⌘K
        - component: ThemeToggle       # dark por classe (estratégia preservada)
        - component: NotificationBell  # contagem de read_at IS NULL
        - component: UserChip          # {{user.name}} + RoleBadge + avatar
    - component: PageOutlet
    - component: CycleNotebookFab      # botão flutuante 📖 (SCR-0022), presente em todas as telas autenticadas
spec.notes:
  - "RoleBadge usa tokens derivados --role-* (DEV-008)"
  - "Rotas de papel não duplicadas (DEV-005)"
```

### Layout: PublicWizardLayout
**Origem**: `src/pages/public/ClientFeedbackPage.tsx` (fluxo público, sem shell)
**Modo aplicado**: literal

```yaml
spec.kind: component-tree
spec.root:
  component: PublicWizardLayout
  tokens: [--public-gradient-from, --public-gradient-to]   # tokens-derived (DEV-008)
  children:
    - component: CenteredCard
      children:
        - component: ProgressBar      # "{{step}} de {{total}}"
        - component: StepOutlet
```

---

## Subset LITERAL (35 telas — oráculo: screenshots do Visor)

> Contrato comum do subset: `spec.kind: route-component`, layout `AuthenticatedShell` (salvo indicação), dados exclusivamente via client OpenAPI gerado (DEV-001), textos idênticos ao legado (diff zero), tokens no lugar de qualquer hex (DEV-003/006). O screenshot referenciado no manifest é o critério de paridade visual.

### Tela: Login (SCR-0001)
**Origem**: `src/pages/Login.tsx` · **Rota**: `/login` · **Layout**: próprio (card central, sem shell) · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /login
spec.oracle: golden/auth-login
spec.component:
  component: LoginPage
  children:
    - { component: BrandHeader }
    - component: LoginForm
      fields:
        - { name: email, label: preservar-legado, validation: { required: true, email: true } }
        - { name: password, label: preservar-legado, validation: { required: true } }
      submit_event: auth.login          # POST /auth/login (JWT próprio — DEV-007)
      links: [{ to: /reset-password, label: preservar-legado }]
spec.transitions: [ "sucesso → rota inicial do papel (resolvida pela API)", "falha → mensagem de erro do legado" ]
```

### Tela: Meu Perfil (SCR-0002)
**Origem**: `src/pages/Perfil.tsx` · **Rota**: `/perfil` · **Crítica**: não
```yaml
spec.kind: route-component
spec.route: /perfil
spec.oracle: golden/auth-perfil
spec.component: { component: PerfilPage, data: "GET /me", sections: [dados-pessoais, papel-e-flags-somente-leitura, preferencias-tema] }
```

### Tela: Painel Administrativo (SCR-0003)
**Origem**: `src/pages/AdminDashboard.tsx` · **Rota**: `/admin` · **Papéis**: admin|rh · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin
spec.oracle: golden/admin-dashboard   # 4 capturas: ciclo vazio + seções preenchidas
spec.component:
  component: AdminDashboardPage
  data: "GET /admin/dashboard (métricas consolidadas server-side — substitui agregações client-side)"
  sections: [progresso-ciclo-aberto, usuarios, pendencias, atividade, alertas-operacionais]
spec.interpolations: ["{{cycle.name}}", "{{progress.percent}}", "{{counts.*}}"]
```

### Tela: Anotações Realizadas (SCR-0004)
**Origem**: `src/pages/admin/AdminAnotacoesRealizadas.tsx` · **Rota**: `/admin/anotacoes-realizadas`
```yaml
spec.kind: route-component
spec.route: /admin/anotacoes-realizadas
spec.oracle: golden/admin-anotacoes-realizadas
spec.component: { component: AnotacoesRealizadasPage, data: "GET /cycle-notes?scope=admin", features: [filtros, busca, badge-Áudio] }
```

### Tela: Minha Equipe — Admin (SCR-0005)
**Origem**: `src/pages/admin/AdminEquipe.tsx` · **Rota**: `/admin/equipe`
```yaml
spec.kind: route-component
spec.route: /admin/equipe
spec.oracle: golden/admin-equipe   # tabela + modal Adicionar Membro
spec.component:
  component: AdminEquipePage
  data: "GET /teams/mine"
  modals: [{ component: AdicionarMembroModal, submit_event: "POST /teams/mine/members" }]
```

### Tela: Histórico da Equipe — Admin (SCR-0006)
**Origem**: `src/pages/admin/AdminHistoricoEquipe.tsx` · **Rota**: `/admin/historico-equipe`
```yaml
spec.kind: route-component
spec.route: /admin/historico-equipe
spec.oracle: golden/admin-historico-equipe
spec.component: { component: HistoricoEquipePage, tabs: [livre, clientes, "360"], data: "GET /history/team?tab=…" }
```

### Tela: Usuários (SCR-0007)
**Origem**: `src/pages/admin/AdminUsuarios.tsx` · **Rota**: `/admin/usuarios` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin/usuarios
spec.oracle: golden/admin-usuarios   # tabela + modal Novo Usuário
spec.component:
  component: AdminUsuariosPage
  data: "GET /identity/profiles"
  modals:
    - component: NovoUsuarioModal
      fields: [nome, email, papel, departamento, gestor, flags-de-capacidade, status]
      submit_event: "POST /identity/profiles"
  actions: [editar, inativar (soft-delete BR-MIGRAR-018)]
```

### Tela: Departamentos (SCR-0008)
**Origem**: `src/pages/admin/AdminDepartamentos.tsx` · **Rota**: `/admin/departamentos`
```yaml
spec.kind: route-component
spec.route: /admin/departamentos
spec.oracle: golden/admin-departamentos
spec.component: { component: DepartamentosPage, data: "GET /identity/departments", modals: [NovoDepartamentoModal] }
```

### Tela: Ciclos de Feedback (SCR-0009)
**Origem**: `src/pages/admin/AdminCiclos.tsx` · **Rota**: `/admin/ciclos` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin/ciclos
spec.oracle: golden/admin-ciclos   # 5 capturas: tabela + wizard Novo + Editar
spec.component:
  component: AdminCiclosPage
  data: "GET /cycles"
  wizard:
    component: CicloWizard           # 3 passos, validação nativa HTML5 preservada
    steps: [dados-basicos, formulario-e-datas, revisao]
    submit_event: "POST /cycles"
  actions:
    - { label: Abrir, event: "POST /cycles/{id}/open" }      # invariantes server-side (BR-MIGRAR-001/010/011)
    - { label: Fechar, event: "POST /cycles/{id}/close" }
    - { label: Publicar, event: "POST /cycles/{id}/publish" }
    - { label: Arquivar, event: "POST /cycles/{id}/archive" }
spec.notes: ["alerta de concorrência por frequência vem da API (409 + mensagem do legado)"]
```

### Tela: Permissões de Feedback (SCR-0010)
**Origem**: `src/pages/admin/AdminPermissoes.tsx` · **Rota**: `/admin/permissoes` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin/permissoes
spec.oracle: golden/admin-permissoes
spec.component:
  component: AdminPermissoesPage
  data: "GET /feedback-permissions"
  modals: [{ component: NovaPermissaoModal, fields: [avaliador, avaliado, tipo, ciclo], submit_event: "POST /feedback-permissions" }]
spec.notes: ["reversa peer_to_peer criada server-side (BR-MIGRAR-002); UI apenas exibe o resultado"]
```

### Tela: Diagnóstico de Permissões (SCR-0011)
**Origem**: `src/pages/admin/AdminDiagnostico.tsx` · **Rota**: `/admin/diagnostico`
```yaml
spec.kind: route-component
spec.route: /admin/diagnostico
spec.oracle: golden/admin-diagnostico
spec.component: { component: DiagnosticoPage, data: "GET /feedback-permissions/diagnostics" }
```

### Tela: Auditoria (SCR-0012)
**Origem**: `src/pages/admin/AdminAuditoria.tsx` · **Rota**: `/admin/auditoria`
```yaml
spec.kind: route-component
spec.route: /admin/auditoria
spec.oracle: golden/admin-auditoria
spec.component: { component: AuditoriaPage, data: "GET /audit-logs (paginado server-side)", features: [filtros-por-evento, detalhe-jsonb] }
```

### Tela: Fale Conosco — Admin (SCR-0013)
**Origem**: `src/pages/admin/AdminFaleConosco.tsx` · **Rota**: `/admin/faleconosco`
```yaml
spec.kind: route-component
spec.route: /admin/faleconosco
spec.oracle: golden/admin-faleconosco
spec.component: { component: FaleConoscoAdminPage, data: "GET /contact-messages", state_machine: "novo → em_andamento → resolvido" }
```

### Tela: Agenda — estado não conectado (SCR-0014)
**Origem**: `src/pages/admin/AdminAgenda.tsx` · **Rota**: `/admin/agenda`
```yaml
spec.kind: route-component
spec.route: /admin/agenda
spec.oracle: golden/admin-agenda
spec.component: { component: AgendaPage, variant: "somente estado não-conectado no primeiro corte (AMB-007)", cta: "texto do legado preservado; ação de conectar desabilitada com aviso de fase 2" }
```

### Tela: Central de Atualizações (SCR-0015)
**Origem**: `src/pages/admin/AdminAtualizacoes.tsx` · **Rota**: `/admin/atualizacoes`
```yaml
spec.kind: route-component
spec.route: /admin/atualizacoes
spec.oracle: golden/admin-atualizacoes
spec.component: { component: AtualizacoesPage, form: [titulo, conteudo, rascunho], submit_event: "POST /platform-updates", notes: ["envio de notificações via outbox/worker; botão reenviar preservado"] }
```

### Tela: Relatórios — Dados e Filtros (SCR-0016)
**Origem**: `src/pages/admin/AdminRelatorios.tsx` · **Rota**: `/admin/relatorios` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin/relatorios
spec.oracle: golden/reports-dados-filtros
spec.component:
  component: RelatoriosPage
  tabs: [clientes, "360", engajamento]
  data: "GET /reports/… (agregação server-side — DEV-001)"
  limits: { preview: 50, table: 100 }    # BR-MIGRAR-029
  exports: [{ kind: csv, sync: true, separator: ";" }, { kind: xlsx, async: true, deviation: DEV-002 }]
```

### Tela: Emitir Relatório (SCR-0017)
**Origem**: `src/pages/admin/AdminRelatorioFeedback.tsx` · **Rota**: `/admin/relatorio-feedback`
```yaml
spec.kind: route-component
spec.route: /admin/relatorio-feedback
spec.oracle: golden/reports-emitir
spec.component:
  component: EmitirRelatorioPage
  form: [ciclo, escopo, pessoa, avaliador-condicional]   # validações BR-MIGRAR-028
  actions: [{ label: preservar-legado, event: "POST /reports/executive (job assíncrono + link — DEV-002)" }, { label: enviar-por-email, event: "job send_report_email" }]
```

### Tela: Formulários (SCR-0018)
**Origem**: `src/pages/admin/AdminFormularios.tsx` · **Rota**: `/admin/formularios` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /admin/formularios
spec.oracle: golden/feedback-formularios
spec.component: { component: FormulariosPage, tabs: ["360", cliente], data: "GET /feedback-forms | GET /client-eval-forms", modals: [NovoFormularioModal] }
```

### Tela: Minhas Anotações (SCR-0019)
**Origem**: `src/pages/MinhasAnotacoes.tsx` · **Rota**: `/minhas-anotacoes`
```yaml
spec.kind: route-component
spec.route: /minhas-anotacoes
spec.oracle: golden/feedback-minhas-anotacoes
spec.component: { component: MinhasAnotacoesPage, data: "GET /cycle-notes?scope=mine", empty_state: preservar-legado }
```

### Tela: Meus Feedbacks (SCR-0020)
**Origem**: `src/pages/MeusFeedbacks.tsx` · **Rota**: `/meus-feedbacks` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /meus-feedbacks
spec.oracle: golden/feedback-meus-feedbacks   # 3 capturas (coordenador, gestor, colaborador)
spec.component: { component: MeusFeedbacksPage, data: "GET /feedback-requests?role=giver", actions: [responder → SCR-0036, abdicar, retomar], status_badges: [pending, draft, submitted, waived, cancelled, expired] }
```

### Tela: Meu Histórico (SCR-0021)
**Origem**: `src/pages/Historico.tsx` · **Rota**: `/historico`
```yaml
spec.kind: route-component
spec.route: /historico
spec.oracle: golden/feedback-meu-historico
spec.component: { component: MeuHistoricoPage, data: "GET /history/mine" }
```

### Tela: Caderno do Ciclo (SCR-0022)
**Origem**: `src/components/CadernoCiclo.tsx` · **Tipo**: widget flutuante global
```yaml
spec.kind: component-tree
spec.oracle: golden/feedback-caderno-ciclo   # 2 capturas: vazio; com Gravar Áudio
spec.root:
  component: CycleNotebookFab
  children:
    - component: NotebookPanel
      features: [anotacao-rapida, gravar-audio, lista-anotacoes-do-ciclo]
      submit_event: "POST /cycle-notes"
```

### Tela: Modal Dar Feedback Livre (SCR-0023)
**Origem**: `src/components/FreeFeedbackModal.tsx` · **Gatilho**: banner nos dashboards · **Crítica**: sim
```yaml
spec.kind: component-tree
spec.oracle: golden/feedback-livre-modal   # 2 capturas: vazio; anonimato + denúncia grave
spec.root:
  component: FreeFeedbackModal
  fields: [destinatario, positivos, melhorias, mensagem, toggle-anonimato, toggle-denuncia-grave]
  submit_event: "POST /free-feedbacks"
  notes: ["anônimo ⇒ giver_id nulo por design (AMB-001)", "textos dos toggles preservados literalmente"]
```

### Tela: Configurações (SCR-0024)
**Origem**: `src/pages/admin/AdminConfiguracoes.tsx` · **Rota**: `/admin/configuracoes`
```yaml
spec.kind: route-component
spec.route: /admin/configuracoes
spec.oracle: golden/company-settings
spec.component: { component: ConfiguracoesPage, data: "GET /tenant-settings", form: "as 8 chaves do catálogo (BR-MIGRAR-027)", submit_event: "PUT /tenant-settings/{key} (upsert otimista)" }
```

### Telas: Início / Minha Equipe / Pendentes / Histórico — Coordenador (SCR-0025..0028)
**Origem**: `src/pages/coordenador/Coordenador{Inicio,Equipe,Pendentes,Historico}.tsx` · **Rotas**: `/coordenador`, `/coordenador/equipe`, `/coordenador/pendentes`, `/coordenador/historico` · **Críticas**: Início e Pendentes
```yaml
spec.kind: route-component
spec.oracle: [golden/coordenador-inicio, golden/coordenador-equipe, golden/coordenador-pendentes, golden/coordenador-historico]
spec.shared:
  scope: "TeamScope do coordenador resolvido pela API (BR-MIGRAR-017) — união deduplicada"
  metrics: "GET /teams/coordinated/metrics (CycleProgress único — BR-MIGRAR-009)"
spec.components:
  - { route: /coordenador, component: CoordenadorInicioPage, sections: [membros, pendencias, taxa-conclusao, ciclo-aberto, atrasos≤3d, atencao-sem-feedback] }
  - { route: /coordenador/equipe, component: CoordenadorEquipePage, actions: [remover-membro (audita+notifica — BR-MIGRAR-026)] }
  - { route: /coordenador/pendentes, component: CoordenadorPendentesPage, filters: [busca, membro, status], actions: [cancelar-com-justificativa] }
  - { route: /coordenador/historico, component: CoordenadorHistoricoPage, tabs: [livre, clientes, "360"] }
```

### Telas: Início / Minha Equipe / Pendentes / Histórico — Gestor (SCR-0029..0032)
**Origem**: `src/pages/gestor/Gestor{Inicio,Equipe,Pendentes,Historico}.tsx` · **Rotas**: `/gestor`, `/gestor/equipe`, `/gestor/pendentes`, `/gestor/historico` · **Críticas**: Início e Pendentes
```yaml
spec.kind: route-component
spec.oracle: [golden/gestor-inicio, golden/gestor-equipe, golden/gestor-pendentes, golden/gestor-historico]
spec.shared:
  scope: "equipe por manager_id (BR-MIGRAR-017); relatórios/agenda condicionados a tenant_settings (BR-MIGRAR-027)"
spec.components:
  - { route: /gestor, component: GestorInicioPage, sections: [metricas-ciclo, ranking, atencao], oracle_states: [sem-pendencias, vazios] }
  - { route: /gestor/equipe, component: GestorEquipePage }
  - { route: /gestor/pendentes, component: GestorPendentesPage, actions: [cancelar-com-justificativa, lembrete (job — BR-MIGRAR-025)] }
  - { route: /gestor/historico, component: GestorHistoricoPage }
```

### Tela: Início — Colaborador (SCR-0033)
**Origem**: `src/pages/Dashboard.tsx` · **Rota**: `/dashboard` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /dashboard
spec.oracle: golden/colaborador-dashboard   # 3 capturas
spec.component: { component: DashboardPage, sections: [meus-requests, progresso, banner-feedback-livre → SCR-0023], data: "GET /dashboard" }
```

### Tela: Avaliações de Clientes (SCR-0034)
**Origem**: `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx` · **Rota**: `/avaliacoes-clientes` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /avaliacoes-clientes
spec.oracle: golden/colaborador-avaliacoes-clientes   # 3 capturas incl. modal Solicitar com aviso de duplicidade
spec.component:
  component: AvaliacoesClientesPage
  data: "GET /client-evaluations (WhatsApp mascarado server-side — BR-MIGRAR-022)"
  filters: [profissional, cliente, whatsapp, status, periodo]
  modals: [{ component: SolicitarAvaliacaoModal, warning: "aviso de duplicidade preservado", submit_event: "POST /client-evaluations/requests" }]
  gates: { ver-respostas: can_view_feedback_answers }
```

### Tela: Avaliação Pública do Cliente — wizard 16 etapas (SCR-0035)
**Origem**: `src/pages/public/ClientFeedbackPage.tsx` · **Rota**: `/avaliacao?token=…` · **Layout**: PublicWizardLayout · **Crítica**: sim
```yaml
spec.kind: route-component
spec.route: /avaliacao
spec.oracle: golden/public-fluxo   # 16 capturas — fluxo completo
spec.component:
  component: PublicEvaluationWizard
  entry: "GET /public/evaluations/{token} → 200 formulário | 410 expirado | 404 inválido"
  steps:
    - boas-vindas
    - identificacao
    - motivacao            # ramos condicionais: elogio | problema (preservados)
    - perguntas-1-a-9      # estrelas 0–10 (escala preservada) + textos; Q6 ver SCR-0044
    - tipo-de-servico      # service_tags
    - agradecimento
  submit_event: "POST /public/evaluations/{token} (atômico + idempotente — BR-MIGRAR-019)"
  notes: ["identidade visual própria: tokens --public-gradient-* (DEV-008)", "rate limiting no Nginx (AD-06)"]
```

---

## Subset MODERNIZADO (8 telas — sem oráculo visual; 4 estados obrigatórios)

> Contrato comum: `spec.kind: route-component`, estados `[idle, loading, error, success]` declarados, layout `AuthenticatedShell` (salvo indicação), componentes do design system (shadcn) e tokens. Conteúdo textual copiado do código legado onde existir (diff zero); onde o código não declara texto, o codificador usa o padrão das telas literais vizinhas e registra deviation se criar texto novo.

### Tela: Formulário de Resposta 360° (SCR-0036)
**Origem**: `src/pages/FeedbackForm.tsx` · **Rota**: `/feedback/{requestId}` · **Crítica**: sim
```yaml
spec.kind: route-component
spec.states: [idle, loading, error, success]
spec.component:
  component: FeedbackFormPage
  data: "GET /feedback-requests/{id}/form (perguntas na ordem persistida)"
  fields: "render dinâmico por question_type: rating | textarea (BR-MIGRAR-008)"
  actions:
    - { label: Salvar rascunho, event: "PUT /feedback-requests/{id}/draft" }   # BR-MIGRAR-012
    - { label: Enviar, event: "POST /feedback-requests/{id}/submit" }
spec.state_messages: { loading: skeleton-do-formulario, error: "{{error_message}}", success: "confirmação + retorno a /meus-feedbacks" }
```

### Tela: Histórico por Pessoa (SCR-0037)
**Origem**: `src/pages/HistoricoPessoa.tsx` · **Rota**: `/historico/{personId}`
```yaml
spec.kind: route-component
spec.states: [idle, loading, error, success]
spec.component: { component: HistoricoPessoaPage, data: "GET /history/person/{id} (escopo via view_history_of — BR-MIGRAR-017)", gates: server-side }
```

### Tela: Reset de Senha (SCR-0038)
**Origem**: `src/pages/ResetPassword.tsx` · **Rota**: `/reset-password` · **Layout**: card central (como SCR-0001) · **Crítica**: sim
```yaml
spec.kind: route-component
spec.states: [idle, loading, error, success]
spec.component:
  component: ResetPasswordPage
  flow: "solicitar (email) → link com token → definir nova senha"   # auth própria (DEV-007)
  events: ["POST /auth/reset-password/request", "POST /auth/reset-password/confirm"]
spec.state_messages: { success: "instrução de retorno ao login" }
```

### Tela: Novidades (SCR-0039)
**Origem**: `src/pages/Novidades.tsx` · **Rota**: `/novidades`
```yaml
spec.kind: route-component
spec.states: [idle, loading, error, success]
spec.component: { component: NovidadesPage, data: "GET /platform-updates (publicadas)", marks_read: true }
```

### Tela: Index / NotFound (SCR-0041)
**Origem**: `src/pages/Index.tsx`, `src/pages/NotFound.tsx`
```yaml
spec.kind: route-component
spec.states: [idle]
spec.components:
  - { route: /, component: IndexRedirect, behavior: "autenticado → rota do papel; anônimo → /login" }
  - { route: "*", component: NotFoundPage, tokens: [--muted-foreground] }
```

### Telas: Colaborador — Dashboard Clientes / Histórico Equipe / Relatórios Clientes (SCR-0042)
**Origem**: `src/pages/colaborador/Colaborador{DashboardClientes,HistoricoEquipe,RelatoriosClientes}.tsx`
```yaml
spec.kind: route-component
spec.states: [idle, loading, error, success]
spec.components:
  - { route: /colaborador/dashboard-clientes, component: DashboardClientesPage, gate: can_view_manager_dashboard, data: "GET /client-evaluations/dashboard" }
  - { route: /colaborador/historico-equipe, component: HistoricoEquipeWrapper, gate: can_view_team_history, reuses: GestorHistoricoPage }
  - { route: /colaborador/relatorios-clientes, component: RelatoriosClientesPage, gate: can_generate_reports, export: { kind: csv, separator: ";", reflects_filters: true } }
spec.notes: ["gate falso ⇒ 403 da API + redirect à raiz (comportamento do legado preservado — BR-MIGRAR-015)"]
```

### Tela: Editor de Perguntas do Formulário (SCR-0043)
**Origem**: `src/pages/admin/AdminFormularios.tsx` (botão "Perguntas") · **Crítica**: sim
```yaml
spec.kind: component-tree
spec.states: [idle, loading, error, success]
spec.root:
  component: QuestionEditorModal
  data: "GET /feedback-forms/{id}/questions | GET /client-eval-forms/{id}/questions"
  features: [criar, editar, remover, reordenar (drag ou setas), obrigatoriedade, tipo-de-pergunta]
  submit_event: "PUT …/questions (ordem persistida — BR-MIGRAR-020)"
```

### Tela: Fluxo Público — Pergunta 6 de 9 (SCR-0044)
**Origem**: `src/pages/public/ClientFeedbackPage.tsx` (etapa Q6 — sem captura; provável NPS/recomendação) · **Layout**: PublicWizardLayout · **Crítica**: sim
```yaml
spec.kind: component-tree
spec.states: [idle, error]
spec.root:
  component: PublicStepQ6
  hypothesis: "NPS 0–10 (recommendation_rating em client_evaluations)"   # 🟡 confirmar no código na codificação
  render: "mesmo padrão de estrelas 0–10 das etapas vizinhas"
spec.notes: ["se o código legado revelar outro tipo, seguir o código e atualizar esta seção (deviation se divergir)"]
```

---

## Apêndice: rastreabilidade ao inventário

| Tela | `ui/inventory.md` | `screens/inventory.json` | Modo |
|---|---|---|---|
| Login | #1 | SCR-0001 | literal |
| Meu Perfil | #2 | SCR-0002 | literal |
| Painel Administrativo | #3 | SCR-0003 | literal |
| Anotações Realizadas | #4 | SCR-0004 | literal |
| Minha Equipe (Admin) | #5 | SCR-0005 | literal |
| Histórico da Equipe (Admin) | #6 | SCR-0006 | literal |
| Usuários | #7 | SCR-0007 | literal |
| Departamentos | #8 | SCR-0008 | literal |
| Ciclos de Feedback | #9 | SCR-0009 | literal |
| Permissões de Feedback | #10 | SCR-0010 | literal |
| Diagnóstico de Permissões | #11 | SCR-0011 | literal |
| Auditoria | #12 | SCR-0012 | literal |
| Fale Conosco | #13 | SCR-0013 | literal |
| Agenda (não conectado) | #14 | SCR-0014 | literal |
| Central de Atualizações | #15 | SCR-0015 | literal |
| Relatórios — Dados e Filtros | #16 | SCR-0016 | literal |
| Emitir Relatório | #17 | SCR-0017 | literal |
| Formulários | #18 | SCR-0018 | literal |
| Minhas Anotações | #19 | SCR-0019 | literal |
| Meus Feedbacks | #20 | SCR-0020 | literal |
| Meu Histórico | #21 | SCR-0021 | literal |
| Caderno do Ciclo | #22 | SCR-0022 | literal |
| Modal Dar Feedback Livre | #23 | SCR-0023 | literal |
| Configurações | #24 | SCR-0024 | literal |
| Início (Coordenador) | #25 | SCR-0025 | literal |
| Minha Equipe (Coordenador) | #26 | SCR-0026 | literal |
| Feedbacks Pendentes (Coord.) | #27 | SCR-0027 | literal |
| Histórico da Equipe (Coord.) | #28 | SCR-0028 | literal |
| Início (Gestor) | #29 | SCR-0029 | literal |
| Minha Equipe (Gestor) | #30 | SCR-0030 | literal |
| Feedbacks Pendentes (Gestor) | #31 | SCR-0031 | literal |
| Histórico da Equipe (Gestor) | #32 | SCR-0032 | literal |
| Início (Colaborador) | #33 | SCR-0033 | literal |
| Avaliações de Clientes | #34 | SCR-0034 | literal |
| Avaliação Pública (16 etapas) | #35 | SCR-0035 | literal |
| Formulário de Resposta 360° | § sem captura | SCR-0036 | modernizado |
| Histórico por Pessoa | § sem captura | SCR-0037 | modernizado |
| Reset de Senha | § sem captura | SCR-0038 | modernizado |
| Novidades | § sem captura | SCR-0039 | modernizado |
| Index / NotFound | § sem captura | SCR-0041 | modernizado |
| Colaborador (3 páginas) | § sem captura | SCR-0042 | modernizado |
| Editor de Perguntas | § sem captura | SCR-0043 | modernizado |
| Fluxo Público — Q6 | § sem captura | SCR-0044 | modernizado |
