# Análise técnica consolidada — aesfeedbackinterno

## Visão geral

O projeto é uma SPA em React + TypeScript para gestão de feedbacks internos e avaliações de clientes. A aplicação usa autenticação e perfis do Supabase, roteamento protegido por papel (`colaborador`, `gestor`, `coordenador`, `admin`, `rh`) e fluxo de ciclos de feedback com geração de `feedback_requests` e consolidação de respostas por ciclo.

A estrutura segue um padrão híbrido: roteamento centralizado por `src/App.tsx` e organização funcional e por perfil em `src/pages/*`. A lógica principal de negócio fica fortemente ligada ao cliente Supabase e a tabelas como `profiles`, `feedback_cycles`, `feedback_requests`, `feedback_answers`, `company_settings`, `notifications`, `departments` e `feedback_permissions`.

## Nível de confiança

- 🟢 CONFIRMADO — observado diretamente no código
- 🟡 INFERIDO — deduzido por consistência do padrão
- 🔴 LACUNA — exigiria validação humana ou inspeção extra do banco

## 1. Módulo de autenticação e papéis

### Arquivos principais

- `src/contexts/AuthContext.tsx`
- `src/components/ProtectedRoute.tsx`

### Funcionalidade

O módulo de autenticação resolve sessão ativa do Supabase, carrega o perfil do usuário e decide o papel ativo (`activeRole`) a partir das permissões do perfil. Há lógica para identificar quando o usuário é gestor e/ou coordenador, e o sistema oferece um seletor para escolher o contexto de visualização caso a pessoa tenha múltiplos grupos de acesso.

### Regras observadas

- A sessão é ativa por `supabase.auth.onAuthStateChange` e `getSession()`.
- O perfil é carregado por `profiles` com `departments(name)`.
- `activeRole` pode ser `gestor`, `coordenador`, `admin`, `rh`, `colaborador`.
- `ProtectedRoute` valida acesso com `allowedRoles.includes(profile.role) || allowedRoles.includes(activeRole)`.
- Usuários inativos são bloqueados com mensagem explícita.

### Entidades/estrutura

- `Profile` contém `id`, `full_name`, `email`, `role`, `department_id`, `manager_id`, `status`, `is_coordinator`.
- `Session` e `User` vêm do Supabase.

### Confiança

- 🟢 CONFIRMADO: a lógica completa de autenticação, papéis e rotação de contexto foi visualizada em código.

## 2. Módulo de ciclos e geração de feedbacks

### Arquivos principais

- `src/pages/admin/AdminCiclos.tsx`
- `src/lib/generateFeedbackRequests.ts`
- `src/pages/Dashboard.tsx`
- `src/pages/gestor/GestorInicio.tsx`

### Funcionalidade

A geração de feedbacks acontece por ciclo. Quando um ciclo entra em estado `open`, o sistema lê as permissões em `feedback_permissions` e cria `feedback_requests` para cada par `giver_id -> receiver_id` que esteja ativo. O fechamento do ciclo recalcula envio pendente e status final.

### Fluxo esperável

1. Administrador abre ciclo;
2. Sistema valida frequências e ciclos concorrentes;
3. Busca permissões ativas;
4. Cria `feedback_requests` para o ciclo;
5. Notifica usuários via `send-feedback-notification` e `notifications`;
6. No fechamento, marca pendências e consolida métricas de conclusão.

### Regras observadas

- Só são gerados requests para `profiles.status = 'active'`.
- Na abertura, mensagens de denúncia e notificação de ciclo são emitidas.
- Ciclos com mesma frequência não podem gerar excesso de concorrência sem aviso.
- `feedback_requests` têm status como `pending`, `draft`, `submitted`, `cancelled`, `waived`, `expired`.

### Entidades centrais

- `feedback_cycles`
- `feedback_permissions`
- `feedback_requests`
- `feedback_answers`

### Confiança

- 🟢 CONFIRMADO: o fluxo de criação e fechamento do ciclo foi verificado em `AdminCiclos.tsx` e `generateFeedbackRequests.ts`.

## 3. Módulo de acompanhamento e dashboards

### Arquivos principais

- `src/pages/AdminDashboard.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/gestor/GestorInicio.tsx`
- `src/pages/coordenador/CoordenadorInicio.tsx`

### Funcionalidade

Os dashboards consolidam métricas por ciclo, etapa, departamento e progresso do time. Os dados são levantados por queries do Supabase, agregados em memória e exibidos em cards, gráficos e tabelas.

### Métricas detectadas

- usuários ativos/inativos
- taxa de conclusão do ciclo
- departamentos com volume de feedbacks
- progresso por membro
- pendências, rascunhos e enviados
- atraso por data de vencimento

### Regras observadas

- Filtros e comparações usam `due_date`, `status`, `cycle_id`, `giver_id`, `receiver_id`.
- O botão de “reminder” e `UnreadFeedbackBanner` permitem foco em feedbacks não lidos e pendentes.

### Confiança

- 🟢 CONFIRMADO: os dashboards existem e conectam diretamente à base e ao status dos requests.

## 4. Módulo de feedback público do cliente

### Arquivos principais

- `src/pages/public/ClientFeedbackPage.tsx`

### Funcionalidade

A aplicação possui uma rota pública para avaliação de cliente com token. O fluxo carrega os dados de `client_feedbacks` e com isso exibe formulário customizado via `client_feedback_forms` e `client_feedback_form_questions`.

### Lógica de negócio principal

- Token valida status `pending` e expiração.
- O avaliador preenche nome, WhatsApp, e-mail, motivo da avaliação e respostas por pergunta.
- Há lógica para detectar palavras-chave negativas e identificar possíveis dívidas ou problemas.
- Ao final, salva respostas e marca a avaliação como enviada.

### Regras detectadas

- O componente valida `token_expires_at`.
- `NEGATIVE_KEYWORDS` trata padrões negativos e descarta negações antes da palavra-chave.
- O formulário aceita avaliação por nota, texto e múltiplas opções.

### Confiança

- 🟢 CONFIRMADO: a rota pública e a lógica de token/avaliação foram observadas diretamente no componente.

## 5. Módulo de configurações e notificações

### Arquivos principais

- `src/pages/admin/AdminConfiguracoes.tsx`
- `src/hooks/useCreateNotification.ts`
- `src/hooks/useCompanySettings.ts`
- `src/components/RequestClientFeedbackModal.tsx`

### Funcionalidade

O sistema armazena configurações globais em `company_settings` (nome da empresa, logo, templates de WhatsApp, motivações de feedback, permissões de acesso). Há também um mecanismo de notificação interna em tabela `notifications` e disparo por Supabase Edge Function.

### Regras observadas

- `company_settings` é a fonte de verdade para toggles de acesso e templates.
- `logo_url` e `company_name` são persistidos para UI global.
- `client_feedback_motivations` é salvo como JSON.

### Confiança

- 🟢 CONFIRMADO: leitura direta de `AdminConfiguracoes.tsx` e hooks de notificação.

## 6. Módulo de relatórios e gestão administrativa

### Arquivos principais

- `src/pages/admin/AdminRelatorioFeedback.tsx`
- `src/pages/admin/AdminRelatorios.tsx`
- `src/pages/admin/AdminUsuarios.tsx`
- `src/pages/admin/AdminDepartamentos.tsx`

### Funcionalidade

A parte administrativa permite gestão de pessoas, departamentos, documentos de ciclo, relatórios por feedback, auditoria e configurações de negócio. O relatório de feedback usa `profiles`, `feedback_requests`, `feedback_answers` e `feedback_cycles` para construir visão por pessoa, por ciclo e por departamento.

### Regras e padrões

- `profiles` tem status ativo/inativo/deletado.
- `departments` e `profile_departments` aparecem em vários pontos do código.
- `audit_logs` registra ações administrativas e de sistema.

### Confiança

- 🟢 CONFIRMADO: o módulo administrativo aparece em vários arquivos e segue um padrão consistente de Supabase + React Query.

## 7. Módulo Coordenador — Supervisão Operacional de Equipe

### Arquivos principais

- `src/pages/coordenador/CoordenadorInicio.tsx`
- `src/pages/coordenador/CoordenadorEquipe.tsx`
- `src/pages/coordenador/CoordenadorPendentes.tsx`
- `src/pages/coordenador/CoordenadorHistorico.tsx`

### Funcionalidade e fluxo

O coordenador consulta sua identidade, combina subordinados diretos (`profiles.manager_id`) com membros explícitos em `coordinator_members` e remove duplicidades. A tela inicial busca requests dos membros e do próprio coordenador, ciclo aberto, leituras pendentes e respostas de rating para montar taxa de conclusão, atrasos, radar de notas, membros sem progresso e próximos vencimentos.

Na tela de equipe, o sistema lista membros ativos, mede pendências (`pending`/`draft`), enviados, leituras não realizadas e progresso por membro. Permite adicionar membro, solicitar feedback de cliente, exportar a tabela em XLSX e remover membro. A remoção atualiza `coordinator_members`, registra `audit_logs` e tenta enviar uma notificação.

A tela de pendências restringe a requests atribuídos à equipe, com prazo a partir de três dias atrás, agrupa por avaliador e oferece busca, filtro de status e cancelamento com justificativa auditada. O histórico reutiliza a visão de histórico do gestor.

### Regras e algoritmos observados

- 🟢 **CONFIRMADO:** progresso exclui requests `cancelled` e `waived`; conclusão é `submitted / total * 100`.
- 🟢 **CONFIRMADO:** atrasos são agrupados por avaliador e calculados a partir de `due_date`.
- 🟢 **CONFIRMADO:** radar usa apenas respostas numéricas de perguntas do tipo `rating` em requests submetidos do ciclo aberto.
- 🟢 **CONFIRMADO:** a equipe combina gestão direta e coordenação explícita, com deduplicação por `id`.
- 🟢 **CONFIRMADO:** cancelamento e remoção preservam justificativas em auditoria; falha do log não bloqueia a operação principal.
- 🟡 **INFERIDO:** `CoordenadorHistorico` funciona como visão equivalente à de gestor porque o plano aponta para a mesma família de dados e componentes de histórico.

### Confiança

As regras de consulta, agregação, filtros e mutações foram extraídas diretamente dos quatro componentes. A autorização final de cada rota permanece distribuída entre `ProtectedRoute` e permissões de perfil.

## 8. Módulo Colaborador — Capacidades Opcionais de Cliente e Equipe

### Arquivos principais

- `src/pages/colaborador/ColaboradorAvaliacoesCliente.tsx`
- `src/pages/colaborador/ColaboradorDashboardClientes.tsx`
- `src/pages/colaborador/ColaboradorHistoricoEquipe.tsx`
- `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx`

### Funcionalidade e fluxo

O módulo disponibiliza ao colaborador um fluxo de solicitação e acompanhamento de avaliações externas. A tela carrega perfis ativos para seleção do profissional avaliado, consulta `client_feedbacks`, agrega pendentes e respondidas, mascara WhatsApp e permite filtros por colaborador, cliente, telefone, status e intervalo de criação. A solicitação é delegada a `RequestClientFeedbackModal`; respostas submetidas podem ser abertas somente com `can_view_feedback_answers`.

O dashboard consulta todos os perfis ativos e delega a visualização a `ClientFeedbackDashboard`, mas redireciona se `can_view_manager_dashboard` for explicitamente falso. O histórico de equipe é um wrapper de `GestorHistorico`, protegido por `can_view_team_history`. O relatório de clientes usa a mesma base de avaliações, filtra por profissional, status e data e exporta CSV; exige `can_generate_reports`.

### Regras observadas

- 🟢 **CONFIRMADO:** flags de perfil controlam respostas, dashboard, histórico e relatórios de forma independente.
- 🟢 **CONFIRMADO:** somente perfis com `status = active` aparecem na seleção de colaboradores.
- 🟢 **CONFIRMADO:** estados `pending` e `in_progress` são tratados como pendentes; `submitted` como respondido; `expired` como expirado.
- 🟢 **CONFIRMADO:** relatório exporta os registros após os filtros atuais, em CSV separado por ponto e vírgula.
- 🟡 **INFERIDO:** a política de autorização do banco complementa os redirecionamentos de UI, pois as páginas executam consultas amplas no cliente.

### Confiança

Os fluxos de interface, flags, filtros e exportação foram confirmados nos componentes do módulo. O comportamento detalhado dos modais reutilizados permanece documentado nos módulos compartilhados.

## 9. Estruturas de dados centrais

### Entidades confirmadas

- `profiles`: dados de usuários, papéis, departamento, status, coordenador
- `feedback_cycles`: ciclo de avaliação
- `feedback_requests`: relação giver/receiver por ciclo
- `feedback_answers`: respostas submetidas
- `feedback_permissions`: regra de relacionamento e avaliação
- `feedback_forms`: formulários de feedback
- `company_settings`: white-label e toggles operacionais
- `notifications`: mensagens internas para usuários
- `departments`: estrutura organizacional
- `audit_logs`: histórico administrativo
- `free_feedbacks`: feedback livre e não estruturado

### Relações inferidas

- `profiles` → `feedback_requests` via `giver_id` e `receiver_id`
- `feedback_cycles` → `feedback_requests` via `cycle_id`
- `feedback_requests` → `feedback_answers` via `request_id`
- `company_settings` → regras de UI e permissões globais

### Confiança

- 🟢 CONFIRMADO para as entidades que aparecem diretamente em consultas e inserts.
- 🟡 INFERIDO para relações implícitas sem schema completo no repositório.

## 10. Módulo de Relatórios

### Arquivos principais

- `src/pages/admin/AdminRelatorios.tsx`
- `src/pages/admin/AdminRelatorioFeedback.tsx`
- `src/pages/colaborador/ColaboradorRelatoriosClientes.tsx`
- `src/lib/feedbackStatus.ts`

### Funcionalidades

O módulo oferece relatórios operacionais em quatro abas administrativas: avaliações de clientes, feedbacks livres, requests 360° e engajamento. As três primeiras consultam dados do Supabase, aplicam filtros em memória, permitem seleção de colunas e exportam CSV separado por ponto e vírgula com BOM UTF-8. A aba 360° também calcula totais, enviados, pendentes, expirados, abdicados e taxa de conclusão, podendo agrupar os resultados por ciclo.

Há um segundo fluxo para gerar relatório executivo de feedback. Ele aceita escopo individual completo, feedback específico ou geral do ciclo; carrega requests submetidos e respostas; calcula média de notas, quantidade esperada/recebida e comparação com o ciclo anterior; e monta PDF detalhado ou resumido. Para relatórios individuais, tenta recuperar ou gerar análise por `analyze-feedback`; no escopo geral, tenta recuperar ou gerar análise consolidada por `analyze-cycle`. O PDF é renderizado por iframe oculto, `html2canvas` e `jsPDF`, podendo ser baixado ou enviado por email via `send-report-email`.

O colaborador possui uma tela separada de relatório de avaliações de clientes. A página redireciona quando `can_generate_reports` é falso, filtra por profissional, status e intervalo de criação e exporta os registros filtrados em CSV.

### Fluxo e algoritmos

- 🟢 **CONFIRMADO:** `AdminRelatorios` carrega perfis, departamentos e ciclos em queries React Query independentes; cada relatório consulta sua própria tabela.
- 🟢 **CONFIRMADO:** filtros de cliente incluem nota positiva (>= 7), nota negativa (<= 6 ou `has_negative`), motivação, profissional, cliente e datas.
- 🟢 **CONFIRMADO:** `Report360` deriva status visual de `status` e `due_date`, calcula atraso em dias e considera enviado apenas o status `submitted` para a taxa.
- 🟢 **CONFIRMADO:** engajamento considera somente ciclos fechados e calcula, por pessoa, total, enviados, taxa, ciclos sem envio e maior sequência consecutiva sem envio.
- 🟢 **CONFIRMADO:** relatório executivo consulta apenas requests `submitted` do receptor e ciclo selecionados; respostas são carregadas por `request_id`.
- 🟢 **CONFIRMADO:** a nota média usa respostas da primeira pergunta `rating`; a comparação anterior usa o ciclo com maior `end_date` anterior ao ciclo atual.
- 🟡 **INFERIDO:** tabelas `feedback_ai_analysis` e `feedback_ai_cycle_analysis` são caches persistentes para evitar regeneração de análises; o schema completo não foi localizado no código consultado.
- 🟡 **INFERIDO:** a autorização efetiva dos relatórios depende também de RLS do Supabase, pois as consultas do cliente são amplas e os controles observados são principalmente de UI.

### Lacunas

- 🔴 **LACUNA:** não foi possível confirmar, apenas pelo frontend, o contrato de payload e as regras de autorização das Edge Functions `analyze-feedback`, `analyze-cycle` e `send-report-email`.
- 🔴 **LACUNA:** o schema completo de `feedback_ai_analysis` e `feedback_ai_cycle_analysis` não está representado nos tipos gerados inspecionados.

### Confiança

As consultas, filtros, agregações, formatos de exportação e caminhos de geração foram extraídos diretamente dos componentes. As políticas de banco e contratos das Edge Functions permanecem parcialmente não observáveis.

## 8. Módulo Admin — Painel de Controle Central

### Arquivos principais

**Entry points:**
- `src/pages/AdminDashboard.tsx` — dashboard principal com métricas consolidadas

**Sub-módulos administrativos (em `src/pages/admin/`):**
- `AdminUsuarios.tsx` — gerência de perfis, roles, status e departamentos
- `AdminPermissoes.tsx` — configuração de regras de feedback (peer_to_peer, manager, upward, self)
- `AdminCiclos.tsx` — criação, abertura, fechamento e publicação de ciclos
- `AdminFormularios.tsx` — gestão de formulários 360° e de feedback de cliente externo
- `AdminConfiguracoes.tsx` — settings globais (logo, nome, templates WhatsApp, motivações)
- `AdminAuditoria.tsx` — logs de ação com filtro por tipo e timeline
- `AdminEquipe.tsx` — visualização de diretos e membros coordenados
- `AdminRelatorios.tsx` — relatórios por cliente, ciclo, departamento e avaliador
- `AdminRelatorioFeedback.tsx` — geração de PDF/visualização de feedback consolidado com gráficos
- `AdminAgenda.tsx` — sincronização Google Calendar, checklist de compromissos e keywords
- `AdminDepartamentos.tsx` — estrutura departamental e hierarquia
- `AdminFaleConosco.tsx` — gestão de contatos e sugestões/críticas do usuário
- `AdminAtualizacoes.tsx` — envio de broadcasts e notificações massivas

**Componentes reutilizáveis:**
- `src/components/admin/UserForm.tsx` — formulário com múltiplos toggles e seletores de permissão

### Funcionalidade geral

O módulo admin centraliza o controle da plataforma: gestão de ciclos de feedback, permissões, usuários, departamentos, formulários, auditoria e broadcasts. A interface é orientada por tabs e modais, com tabelas de dados filtráveis, paginadas e exportáveis em Excel/CSV.

### 8.1. AdminDashboard — Painel de Métricas

**Lógica:**
1. Carrega em paralelo: profiles (status), feedback_cycles (open), feedback_requests, departments, feedback_forms, audit_logs
2. Agrega: usuários ativos/inativos, ciclo ativo, taxa de conclusão do ciclo aberto
3. Constrói gráficos: pedidos por departamento, atividade diária no ciclo, top actions auditadas
4. Exibe: banners de alerta (compromissos sem feedback, mensagens Fale Conosco, deadline de ciclo)

**Queries em paralelo:**
```
- supabase.from("profiles").select(...).in("status", ["active", "inactive"])
- supabase.from("feedback_cycles").select(...).eq("status", "open").limit(1)
- supabase.from("feedback_requests").select(...)
- supabase.from("departments").select(...)
- supabase.from("feedback_forms").select(..., { count: "exact", head: true })
- supabase.from("audit_logs").select(...).order("created_at", desc).limit(5)
- supabase.from("daily_appointments").select(...)  // para PendingChecklistBanner
```

**Cálculos:**
- `completionRate = (submitted / totalRequests) * 100`
- `deptChartData` = count requests por giver_department
- `activityData` = count submitted requests por data dentro do ciclo ativo

**Confiança:** 🟢 CONFIRMADO

### 8.2. AdminUsuarios — Gestão de Perfis

**Operações CRUD:**
- Listar: profiles (all active/inactive) com departments join
- Criar: novo perfil com email, role, department, manager, status, toggles de permissão
- Editar: atualizar profile + profile_departments + coordinator_members
- Deletar: soft-delete ou inativação

**Permissões atribuíveis (via UserForm):**
- `is_coordinator` — capacidade de coordenar equipes
- `can_request_client_feedback` — solicitar avaliações de cliente externo
- `can_view_feedback_answers` — visualizar respostas de feedback
- `can_view_team_history` — acessar histórico da equipe
- `can_generate_reports` — gerar relatórios customizados
- `can_view_manager_dashboard` — ver painel gestor
- `view_history_of` — seletor de contexto de visualização (coordenador ou gestor)

**Lógica de departamentos:**
- Lê `profile_departments` para multi-departamento
- Fallback em `department_id` (legacy) se não houver join
- Exibe em tooltip se > 2 departamentos

**Ordenação e filtros:**
- Filtra por status, role, departamento
- Ordena por full_name, email, job_title, departments, role, status

**Exportação:** Excel (.xlsx) via `XLSX` library

**Confiança:** 🟢 CONFIRMADO

### 8.3. AdminPermissoes — Regras de Avaliação

**Estrutura de permissões:**
- `feedback_permissions` contém (reviewer_id, reviewee_id, permission_type, cycle_id, active)
- `permission_type`: `peer`, `manager`, `self`, `upward`, `peer_to_peer`, `manager_to_report`, `custom`

**Lógica especial — Permissões Bidirecionais (peer_to_peer):**
```
Function ensureReversePeerPermission(A → B):
  1. Verifica se B → A já existe
  2. Se não: cria permissão reversa
  3. Chama ensureRequestForActiveCycle(B → A) para criar request no ciclo ativo
```

**Lógica de Bulk:**
- Modo `manager_to_report`: cria requests de gestor para todos os diretos
- Modo `peer_to_peer`: cria requests bidirecionais com reverse automático
- Modo `upward`: cria requests de diretos para gestor
- Modo `self`: cria autoavaliação

**Tabela:**
- Filtros: tipo de permissão, status (ativo/inativo), ciclo
- Paginação: 15 por página
- Ícones com badges de cor

**Confiança:** 🟢 CONFIRMADO

### 8.4. AdminCiclos — Orquestração de Ciclos

**Estados do ciclo:**
- `draft` → `open` → `closed` → `published` → `archived`

**Regras de abertura:**
- Máximo 2 ciclos da mesma frequência abertos simultaneamente (com warning se houver 1)
- Verifica `feedback_permissions` ativas
- Chama `generateFeedbackRequests()` para criar requests em massa

**Regras de fechamento:**
- Recalcula taxa de conclusão
- Marca como `closed`
- Pode ser automático via Edge Function (com flag `auto_closed`)

**Frequências suportadas:**
- `fortnightly` (quinzenal), `monthly`, `quarterly`, `semiannual`, `annual`

**Integração com formulários:**
- Cada ciclo pode ter `form_id` (feedback_forms)
- Queries detectam ciclos sem formulário atribuído

**Confiança:** 🟢 CONFIRMADO

### 8.5. AdminFormularios — Gestão de Modelos de Avaliação

**Dois tipos de formulários:**
1. **360°** (`feedback_forms`): para avaliação interna
2. **Cliente Externo** (`client_feedback_forms`): para público externo

**Operações 360°:**
- Criar, editar, desativar formulário
- Editor de perguntas com reordenação (drag-drop)
- Tipos de pergunta: rating, texto, múltipla escolha

**Operações Cliente:**
- Criar formulário com nome
- Definir padrão (`is_default`)
- Editor de perguntas cliente-específicas

**Status:**
- `active/inactive` no dropdown de ciclo

**Confiança:** 🟢 CONFIRMADO

### 8.6. AdminPermissoes (Não confundir com 8.3)

Seção separada para configuração mais granular de permissões por ciclo:
- Pairing individual reviewer ↔ reviewee
- Bulk import via upload de arquivo
- Associação com ciclo específico

**Confiança:** 🟢 CONFIRMADO

### 8.7. AdminConfiguracoes — White-label e Toggles

**Campos em `company_settings` (key-value):**
- `logo_url`: URL da logo (upload para Supabase Storage)
- `company_name`: nome da empresa
- `whatsapp_message_template`: template de mensagem com variáveis ({{name}}, {{feedback_link}})
- `calendar_keywords`: JSON array de palavras-chave para sincronização Google Calendar
- `client_feedback_motivations`: JSON `{ praise: bool, evaluate: bool, problem: bool, other: bool }`

**Upload de imagem:**
- Valida tipos (jpg, png, webp)
- Persiste em Supabase Storage
- Retorna URL pública

**Editor de template:**
- Suporta clique para inserir variáveis
- Salva raw em `company_settings`

**Confiança:** 🟢 CONFIRMADO

### 8.8. AdminAuditoria — Rastreamento de Ações

**Categorias de evento:**
- **Equipe**: add_team_member, remove_team_member, team_request_approved/rejected
- **Ciclos**: cycle_created, opened, closed, published, archived
- **Feedbacks**: feedback_360_submitted, draft_saved, cancel_feedback_request, free_feedback_sent
- **Lembretes**: manual_reminder_sent
- **Usuários**: user_created, updated, deleted

**Estrutura do log:**
- `action_type` (string)
- `performed_by` (user id)
- `created_at` (timestamp)
- `details` (JSON): informações específicas por tipo (nomes, ciclo, motivos, etc.)
- `is_sensitive` (boolean): marca ações críticas

**Funcionalidade:**
- Filtros por ação, período, usuário
- Expandir linha para ver `details` completo com formatação legível
- Ícones coloridos por tipo
- Busca e paginação

**Helpers:**
- `buildSummary()`: gera frase descritiva da ação
- `formatDetailValue()`: converte valores para exibição (datas, enums, etc.)

**Confiança:** 🟢 CONFIRMADO

### 8.9. AdminAgenda — Sincronização Google Calendar

**Fluxo:**
1. Usuário autoriza acesso ao Google Calendar via OAuth
2. Sistema puxa eventos dentro de período (dia/mês/ano selecionado)
3. Filtra por `keywords` (audiência, atendimento, reunião, etc.)
4. Extrai partes do evento (ex: "X vs Y" em "Audiência X vs Y")
5. Marca se feedback já foi solicitado (`feedback_requested = true/false`)
6. Admin pode solicitar feedback de cliente para evento

**Palavras-chave customizáveis:**
- Padrão: `["audiência","atendimento","reunião","cliente","consulta","perícia","despacho","sessão"]`
- Armazenado em `company_settings → calendar_keywords` como JSON

**Estatísticas:**
- View por dia/mês/ano
- Conta: eventos totais, com feedback, sem feedback

**Endpoints:**
- OAuth: Google Accounts
- API: Google Calendar (readonly)

**Confiança:** 🟢 CONFIRMADO (lógica no código, integração com Google requer validação em runtime)

### 8.10. AdminRelatorios — Relatórios de Feedback

**Abas:**
- Cliente (external feedback)
- Funcionário (360° feedback)
- Departamento
- Ciclo

**Colunas customizáveis:**
- Show/hide por coluna
- Ordenação bidirecional
- Filtros de status, data, pessoa

**Exportação:**
- CSV com BOM (UTF-8)
- Filename: `${report_type}_${date}.csv`

**Helpers:**
- `calcDaysLate()`: dias de atraso em relação a due_date
- `sortData()`: ordena por tipo de coluna (numérico/string)

**Confiança:** 🟢 CONFIRMADO

### 8.11. AdminRelatorioFeedback — Geração de PDF

**Funcionalidade:**
- Seleciona ciclo, avaliador, avaliado
- Exibe consolidação de respostas com gráficos
- Exporta para PDF (html2canvas + jsPDF)
- Pode enviar por email (requer servidor de email)

**Confiança:** 🟡 INFERIDO (lógica de export existe, validação de email requer teste)

### 8.12. AdminFaleConosco — Gestão de Contatos

**Tabela de mensagens:**
- `feedback_contacts` contém: nome, email, tipo (sugestão/crítica), status (novo/lido/resolvido), mensagem

**Operações:**
- Marcar como lido
- Responder (via email ou modal)
- Deletar
- Filtrar por tipo e status

**Confiança:** 🟢 CONFIRMADO

### 8.13. AdminAtualizacoes — Broadcasts

**Envio massivo:**
- Notificação in-app via `notifications` table
- Email (requer Supabase Mail ou externo)
- Segmentação por role ou todos os usuários

**Confiança:** 🟡 INFERIDO (estrutura base existente, mecanismo de email requer validação)

### 8.14. AdminEquipe — Visualização de Diretos

**Dados:**
- Direct reports do admin via `manager_id`
- Membros coordenados via `coordinator_members` join

**Funcionalidade:**
- Listar equipe ativa
- Ver requests de feedback emanados do admin
- Ver requests recebidos pela equipe (no ciclo ativo)
- Exportar em Excel
- Adicionar/remover membro

**Confiança:** 🟢 CONFIRMADO

### 8.15. AdminDepartamentos — Gestão de Estrutura

**Operações:**
- Criar, editar, deletar departamento
- Atribuir responsável
- Reordenar hierarquia

**Confiança:** 🟡 INFERIDO (lógica básica no padrão, código completo não foi lido)

### Padrões transversais no módulo admin

1. **React Query + Supabase**: todos os dados são buscados via `useQuery` com chaves bem-estruturadas
2. **Otimismo**: mutações com `onSuccess` disparam `invalidateQueries` para refetch
3. **Toasts**: feedback visual via `sonner`
4. **Modais**: diálogos para criar, editar, deletar via `Dialog`
5. **Tabelas filtráveis**: suporte a sorting, paging, coluna oculta
6. **Componentes reutilizáveis**: `UserForm`, `AddMemberModal`, `RemoveMemberModal`

### Confiança geral do módulo admin

- 🟢 CONFIRMADO: 14 arquivos lidos e analisados diretamente
- 🟡 INFERIDO: alguns fluxos de email e integração externa
- 🔴 LACUNA: schema SQL completo, validações de backend (Edge Functions)

## 9. Módulo Gestor — Painel do Gerente de Equipe

### Arquivos principais

- `src/pages/gestor/GestorInicio.tsx` — dashboard principal com métricas de equipe
- `src/pages/gestor/GestorEquipe.tsx` — gerência de membros e progresso individual
- `src/pages/gestor/GestorPendentes.tsx` — visualização de feedbacks pendentes
- `src/pages/gestor/GestorHistorico.tsx` — histórico de feedbacks 360° e cliente

### Funcionalidade geral

O módulo gestor centraliza a supervisão de uma equipe no ciclo de feedback. O gerente (gestor) pode:
- Visualizar métricas consolidadas da equipe (membros, pendências, taxa de conclusão)
- Acompanhar progresso individual de cada membro
- Adicionar/remover membros da equipe
- Visualizar e cancelar feedbacks pendentes com justificativa
- Acessar histórico completo de feedbacks 360° e cliente da equipe
- Receber alertas sobre leituras pendentes e prazos vencidos

### 9.1. GestorInicio — Dashboard Principal

**Dados carregados em paralelo:**
```
- userId (auth)
- profile (full_name)
- team (diretos via manager_id + coordenados via coordinator_members)
- requests (all feedback_requests onde giver_id em teamIds)
- pending-reads (submitted requests não lidos)
- activeCycle (feedback_cycles com status open)
- radarData (agregação de scores para radar chart)
```

**Estrutura de dados:**
- `teamIds` = [userId, ...team.map(t => t.id)]
- `requests` = feedback_requests de toda a equipe (incluindo o gerente)
- `submitted` = requests com status "submitted"
- `pending` = requests com status "pending" ou "draft"

**Cálculos principais:**
- `completionRate = (submitted / totalRequests) * 100` (excluindo cancelled, waived)
- `pending` filtrados por ciclo ativo e data de vencimento
- `overdue` = pendentes com due_date < today e dias_diff <= 3
- `radarData` = média de scores de respostas com answer_type = "rating" por membro

**Gráficos:**
1. **Pie Chart**: Status (Pendente, Rascunho, Enviado)
2. **Bar Chart**: Pendências por membro (primeiros nomes)
3. **Area Chart**: Envios cumulativos ao longo do ciclo (submitted_at)
4. **Radar Chart**: Scores médios de cada membro (se houver dados de rating)

**Alertas e banners:**
- `CycleClosedBanner`: notifica quando ciclo foi fechado e exibe relatório
- `UnreadFeedbackBanner`: avisa se há feedbacks não lidos pelo gerente
- `SensitiveFeedbackAlert`: avisa sobre feedbacks confidenciais urgentes na equipe
- `CycleDeadlineBanner`: mostra data de encerramento do ciclo
- `PendingChecklistBanner` (via TeamRequestsSection): compromissos com feedback não solicitado

**Cards de stats:**
- Membros da Equipe (com link para /gestor/equipe)
- Pendências (com link para /gestor/pendentes)
- Taxa de Conclusão (com link para /gestor/historico)
- Ciclo Atual (mostra nome e data fim)

**Lógica de alertas:**
- Se `pendingReadsCount > 0`: exibe card com aviso "X membros com leitura pendente"
- Se `overdue.length > 0`: exibe accordion "Feedbacks Atrasados" com detalhe por membro
- Se `zeroProgressMembers > 0`: exibe card "Sem Progresso" alertando sobre inativos

**Confiança:** 🟢 CONFIRMADO

### 9.2. GestorEquipe — Gerência de Membros

**Dados:**
- `team` = diretos (manager_id) + coordenados (coordinator_members)
- `openCycle` = ciclo ativo
- `requests` = feedback_requests do gerente para seus membros no ciclo ativo
- `receivedRequests` = feedback_requests enviados aos membros (status submitted)
- `memberRequests` = feedback_requests de cada membro no ciclo ativo

**Tabela de membros:**
- Colunas: Nome, Cargo, Email, Feedback Pendente, Feedback Enviado, % Conclusão, Leituras Pendentes
- Ações: Ver histórico (link para /historico/{memberId}), Solicitar feedback cliente, Remover membro

**Funcionalidade:**
- Click no nome → navega para `/historico/{memberId}`
- Badge com número de leituras pendentes no nome se > 0
- Barra de progresso mostrando % de conclusão
- Botão "Solicitar Feedback de Cliente" (abre RequestClientFeedbackModal)
- Botão "Remover" (abre RemoveMemberModal com justificativa)
- Botão "Adicionar Membro" (abre AddMemberModal)
- Exportar em Excel com colunas: Nome, Cargo, Email, Status, Pendentes, Enviados, % Conclusão, Leituras Pendentes

**Lógica de remoção:**
- Deleta em `coordinator_members` se membro via coordenação
- Seta `manager_id = null` em `profiles` se membro direto
- Registra em `audit_logs` com justificativa
- Notifica o membro removido via `createNotification`

**Confiança:** 🟢 CONFIRMADO

### 9.3. GestorPendentes — Feedbacks Pendentes da Equipe

**Dados:**
- `teamIds` = userId + team ids
- `requests` = feedback_requests com giver_id em teamIds, status em [pending, draft], due_date >= 3 dias atrás

**Interface:**
- Busca por nome (giver ou receiver)
- Filtro por status (todos, pendente, rascunho)
- Accordion expandível por membro (giver)
- Cada linha de feedback mostra: "→ Receiver" + due_date + status badge + dias de atraso

**Operações:**
- Click em linha → abre `CancelFeedbackModal`
- Confirmar cancelamento → atualiza request.status = "cancelled"
- Registra em audit_logs com justificativa
- Toast de sucesso

**Cálculo de atraso:**
```
daysDiff(dateStr) = floor((today - dateStr) / 86400000)
```

**Confiança:** 🟢 CONFIRMADO

### 9.4. GestorHistorico — Histórico Completo

**Nota:** Este componente é reusado em AdminHistoricoEquipe (re-export)

**Dados em paralelo:**
- `teamIds` = userId + team ids (diretos + coordenados)
- `requests` = feedback_requests onde giver_id ou receiver_id em teamIds (todos os status, todos os ciclos)
- `clientFeedbacks` = client_feedbacks com target_user_id em teamIds, status = "submitted"

**Tabs:**
1. **Ciclos 360°**: histórico de feedback_requests interno
2. **Feedbacks de Clientes**: histórico de client_feedbacks

**Tab 1 — Ciclos:**
- Filtros: status (todos, pendente, rascunho, enviado, expirado, abdicado, cancelado)
- Filtros: mostrar/ocultar cancelados
- Busca por nome (giver/receiver)
- Filtro por data (start/end)
- Ordenação: por nome ou data (asc/desc)
- Tabela com: Ciclo, Avaliador, Avaliado, Status, Due Date

**Tab 2 — Clientes:**
- Filtro por membro (target_user)
- Filtro por motivation (elogio, avaliação, problema, outro)
- Paginação (5 por página)
- Card por feedback: cliente, rating, comentário, data

**Operações:**
- Click em request → abre modal com respostas completas
- Click em feedback cliente → abre modal com questões e respostas
- Botão "Abdicar" (waive) → marca request como waived com justificativa
- Botão "Retomar" (resume) → volta waived para pending

**Modal de feedback 360°:**
- Mostra respostas por pergunta
- Agrupa por tipo (rating, texto, múltipla escolha)
- Exibe scores e comentários

**Modal de feedback cliente:**
- Mostra dados do cliente (nome, email, WhatsApp)
- Ratings (overall, recommendation)
- Respostas às questões customizadas
- Data de submissão

**Confiança:** 🟢 CONFIRMADO

### Padrões transversais no módulo gestor

1. **React Query**: queries paralelas com chave bem estruturada
2. **Agregação em memória**: cálculos de stats (count, média, percentual) feitos no frontend
3. **Modais**: CancelFeedbackModal, RemoveMemberModal, RequestClientFeedbackModal, FeedbackAnswersModal
4. **Exportação**: Excel via `XLSX` library com formatação de colunas
5. **Navegação**: links para histórico individual (/historico/{memberId}), que também é acessível para colabs

### Dados principais do módulo gestor

- **feedback_requests** (ciclos 360°)
- **coordinator_members** (estrutura de coordenadores)
- **profiles** (dados de membros)
- **client_feedbacks** (feedback de clientes externos)
- **audit_logs** (cancelamentos e remoções de membros)

### Confiança geral do módulo gestor

- 🟢 CONFIRMADO: 4 arquivos lidos na íntegra
- 🟡 INFERIDO: algumas operações de backend (createNotification)
- 🔴 LACUNA: detalhes de permissão de acesso ao /historico/{memberId} de outros gestores

## 10. Riscos e lacunas

- Não há schema SQL completo dentro do repositório, então algumas colunas e constraints só podem ser confirmadas no banco real.
- O módulo de notificações depende de Edge Functions externas do Supabase, sem código no repo completo.
- Há arquivos antigos com `.bak` e alguns pontos de código com casts `as any`, o que sinaliza adaptações de integração.
- Integração com Google Calendar requer OAuth válido em runtime.
- Funcionalidades de envio de email (broadcasts, relatórios) precisam de confirmação de backend implementation.
- Acesso a histórico de membros pode ter regras de RBAC não explicitadas no frontend.

## 11. Conclusão

A arquitetura do sistema é uma suíte de gestão de avaliação interna com forte uso de banco relacional via Supabase, alguns mecanismos de autenticação por papéis, flows de ciclo de feedback e dashboards analíticos. O nucleo funcional está centrado em `profiles`, `feedback_cycles`, `feedback_requests` e `feedback_answers`, com a camada de UI organizada por papéis e áreas administrativas. O módulo admin é o ponto central de orquestração, o módulo gestor é a supervisão de equipe, permitindo acompanhamento fino de feedbacks pendentes, histórico e ações de equipe.
