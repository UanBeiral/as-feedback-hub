# Telas — unit `admin`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA
>
> **Menu lateral do admin (ordem observada):** Anotações (▸ Minhas Anotações, Realizadas), Relatórios (▸ Dados e Filtros, Emitir Relatório), Dashboard, Minha Equipe, Histórico da Equipe, Usuários, Departamentos, Ciclos, Permissões, Diagnóstico, Formulários, Auditoria, Fale Conosco, Agenda, Atualizações, Configurações, Meu Perfil, Sair 🟢

---

## Painel Administrativo (Dashboard)

- **Rota:** `/admin` · **Arquivo:** `src/pages/admin/AdminDashboard.tsx`
- **Screenshots:** `screenshots/dashboard.png` (topo), `dashboard-2.png` (gráficos), `dashboard-3.png` (status/resumo), `dashboard-4.png` (saúde do sistema)
- **Estados capturados:** ciclo sem atividade ("Nenhum ciclo aberto" / "Nenhum feedback enviado neste ciclo") e listas preenchidas nas seções inferiores

### Estrutura (ordem vertical)

1. **Banner "Dar Feedback para alguém"** — call-to-action amarelo: "Envie um feedback livre para qualquer colaborador a qualquer momento." 🟢
2. **4 cards KPI** (com tooltip ⓘ): Usuários Ativos (clicável → equipe), Ciclo Atual, Taxa de Conclusão ("Precisa de atenção"), Pendências ("Tudo em dia!") 🟢
3. **Conclusão por Departamento** — gráfico de barras agrupadas (2 séries) por departamento: Controladoria, Juri…, Marketing, TI, Relações Instituci…, Financeiro 🟢
4. **Atividade no Ciclo Atual** — lista; estado vazio: "Nenhum feedback enviado neste ciclo." 🟢
5. **Status dos Usuários** — donut: Ativo 15 (verde), Inativo 7 (amarelo), Deletado 4 (vermelho) 🟢
6. **Resumo Geral** — tabela de indicadores: Total de feedbacks 954, Enviados 364, Pendentes 91, Feedbacks atrasados 0, Departamentos 9, Total de ciclos 14, Formulários 2 🟢
7. **Saúde do Sistema** — dois painéis:
   - *Atividade Recente*: eventos com tipo técnico (`user_updated`, `user_created`, `cycle_closed`, `feedback_360_submitted`) e timestamp 🟢
   - *Atenção Necessária*: Feedbacks atrasados (0), Usuários inativos (7), Ciclos sem formulário (2) — cada linha com contador e seta de navegação 🟢

---

## Anotações Realizadas

- **Rota:** `/admin/anotacoes-realizadas` · **Arquivo:** `src/pages/admin/AnotacoesRealizadas.tsx`
- **Screenshots:** `screenshots/anotacoes-realizadas.png`, `anotacoes-realizadas-2.png` (rolagem)
- **Estado capturado:** preenchido (60 anotações)
- **Propósito:** visão administrativa de todas as anotações da equipe, "organizadas por ciclo e pessoa avaliada" 🟢

### Elementos

- **3 cards KPI:** Total 60, Autores 3, Avaliados 11 🟢
- **Filtros:** busca "por nome ou conteúdo", dropdown "Todos os ciclos", dropdown "Todos os autores" 🟢
- **Agrupamento hierárquico:** ciclo ("360 Feedback - Segunda Quinzena (agosto/2026)", badge "4 anotações") → pessoa avaliada (avatar + nome + "N anotações de N autor", colapsável) → anotação individual 🟢
- **Anotação:** autor, timestamp (25/08, 09:48), texto livre; badge **"Áudio"** em algumas anotações — indica anotação com origem em áudio/transcrição 🟡

---

## Minha Equipe

- **Rota:** `/admin/equipe` · **Arquivo:** `src/pages/admin/AdminEquipe.tsx`
- **Screenshots:** `screenshots/minha-equipe.png`, `minha-equipe-modal-adicionar-membro.png`
- **Estados capturados:** tabela com 1 membro; modal de adição aberto

### Tabela

| Coluna | Observação |
|---|---|
| Nome | — |
| Cargo | — |
| Status | badge "Ativo" verde |
| Pendentes de Enviar ⓘ | numérico |
| Enviados ⓘ | numérico |
| Pendentes de Leitura ⓘ | numérico |
| Progresso ⓘ | barra percentual |
| Ações | ✕ (remover da equipe) 🟡 |

- Rodapé: "Progresso geral da equipe" (barra + "0 de 0 feedbacks enviados (0%)") e "Total de membros na equipe: 1" 🟢
- Ações de topo: **Exportar Excel**, **+ Adicionar Membro** 🟢

### Modal "Adicionar Membro"

- Busca por nome + lista de usuários com checkbox (nome + cargo à direita) 🟢
- Rodapé: contador "0 selecionados", botões Cancelar / Adicionar (desabilitado sem seleção) 🟢

---

## Histórico da Equipe

- **Rota:** `/admin/historico-equipe` · **Arquivo:** `src/pages/admin/AdminHistoricoEquipe.tsx`
- **Screenshots:** `screenshots/historico-equipe.png`, `historico-equipe-2.png` (rolagem)
- **Estados capturados:** seção Feedback Livre preenchida (1 resultado); Avaliações de Clientes (0) e 360° (0) vazias

### Estrutura — 3 seções colapsáveis por tipo de feedback

1. **Feedback Livre da Equipe** — filtros (busca, dropdown, ordenação por Data); card com: Para/De, Pontos Positivos (verde), Pontos de Melhoria (vermelho), Mensagem, badge verde de ciência ("✅ Ciente em 27/04/2026 14:45 por …"), botão "Ver Detalhes" 🟢
2. **Avaliações de Clientes (0)** — colapsada 🟢
3. **360° — Ciclos de Feedback (0)** — filtros: Status, toggle "Cancelados/Ocultos", De/Até (datas), busca "Avaliador ou avaliado", ordenação A-Z / Data; estado vazio "Nenhum histórico encontrado." 🟢
- Filtro global no topo: "Exibir: Todos os tipos" 🟢

---

## Usuários

- **Rota:** `/admin/usuarios` · **Arquivo:** `src/pages/admin/AdminUsuarios.tsx`
- **Screenshots:** `screenshots/usuarios.png`, `usuarios-modal-novo-usuario.png`
- **Estados capturados:** tabela preenchida; modal de criação aberto

### Tabela

- Filtros: Todos Departamentos, Todos Papéis, Todos Status 🟢
- Colunas ordenáveis: Nome, E-mail, Cargo, Departamento (com badge "+8" para múltiplos), Papel (Admin / Gestor…), Status (Ativo), Ações 🟢
- Ações de topo: **Exportar Excel**, **+ Novo Usuário** 🟢

### Modal "Novo Usuário" (rolável)

| Campo | Tipo |
|---|---|
| Nome Completo | text |
| E-mail | email |
| WhatsApp (opcional) | tel, máscara `(XX) XXXXX-XXXX` |
| Senha Temporária | password com toggle 👁 |
| Cargo | text |
| Departamentos | seleção (múltipla 🟡, cortada no screenshot) |

- 🔴 LACUNA: campos abaixo de "Departamentos" (papel, status…) não capturados.

---

## Departamentos

- **Rota:** `/admin/departamentos` · **Arquivo:** `src/pages/admin/AdminDepartamentos.tsx`
- **Screenshots:** `screenshots/departamentos.png`, `departamentos-modal-novo.png`
- **Estados capturados:** tabela preenchida; modal aberto

- Tabela: Nome, Descrição (— quando vazia), Ações (Editar, ícone de download/exportação) 🟢
- Departamentos visíveis: Administrativo, Comercial, Controladoria Jurídica, Financeiro, Inteligência/BI/Estratégia, Marketing… (9 no total, conforme Resumo Geral do dashboard) 🟢
- Ações de topo: **Exportar Excel**, **+ Novo Departamento** 🟢
- Modal "Novo Departamento": Nome (text), Descrição (textarea), Cancelar/Salvar 🟢

---

## Ciclos de Feedback

- **Rota:** `/admin/ciclos` · **Arquivo:** `src/pages/admin/AdminCiclos.tsx` (unit compartilhada com `feedback/` no domínio)
- **Screenshots:** `screenshots/ciclos.png`, `ciclos-modal-novo.png`, `ciclos-modal-editar.png`
- **Estados capturados:** tabela preenchida; wizard de criação; modal de edição

### Listagem

- Descrição da página: "Ciclos são períodos definidos para coleta de feedbacks. Cada ciclo tem uma data de início, fim e um formulário associado." 🟢
- Ações de topo: **Arquivados (3)** (toggle de visibilidade), **+ Novo Ciclo** 🟢
- Colunas: Nome, Frequência (Quinzenal/Mensal), Início, Fim, Formulário, Status (badge "Aberto" verde / "Fechado" vermelho + tooltip ?), Ações 🟢
- **Ações por status:** ciclo Aberto → **Fechar** (vermelho) + Editar + arquivar; ciclo Fechado → **Publicar** + Editar + arquivar 🟢 — confirma máquina de estados aberto → fechado → publicado 🟡 (ver `_reversa_sdd/state-machines.md`)

### Modal "Novo Ciclo" — wizard de 3 passos

- Passo 1 "Informações básicas": aviso "Este ciclo será **recorrente** — ao terminar, o sistema abrirá automaticamente o próximo com o mesmo formulário e frequência." 🟢
- Campos: Nome do ciclo ⓘ, Descrição ⓘ, Frequência ⓘ ("Quinzenal — renova a cada 15 dias"), Formulário de perguntas ⓘ (dropdown) 🟢
- Capturas adicionais: `ciclos-modal-novo-2.png` (validação nativa "Preencha este campo." no Nome) e `ciclos-modal-novo-3.png` (rodapé do passo 1 com Cancelar / **Próximo →**) 🟢
- 🔴 LACUNA: passos 2 e 3 do wizard não capturados.

### Modal "Editar Ciclo"

- Campos: Nome ⓘ, Descrição ⓘ, Frequência ⓘ, Data Início ⓘ, Data Fim ⓘ, **Período avaliado (início/fim)** ⓘ (par de datas separado do período do ciclo), Formulário ⓘ 🟢

---

## Permissões de Feedback

- **Rota:** `/admin/permissoes` · **Arquivo:** `src/pages/admin/AdminPermissoes.tsx` (unit compartilhada com `feedback/` no domínio)
- **Screenshots:** `screenshots/permissoes.png`, `permissoes-modal-nova.png`
- **Estados capturados:** lista agrupada preenchida; modal aberto

- Descrição: "Permissões definem quem pode avaliar quem. Sem uma permissão ativa, o feedback não será gerado automaticamente nos ciclos." 🟢
- Ações de topo: ordenação A-Z, **Exportar CSV**, **Importar em Massa**, **+ Nova Permissão** 🟢
- Filtros: busca por nome, Todos os tipos, Todos os status, Todos os ciclos 🟢
- Lista agrupada por avaliador: avatar + nome + badge "N ativas" + ação CSV por linha + expansor 🟢
- Modal "Nova Permissão": Avaliador (select), Avaliado (select), Tipo (select), Ciclo (opcional, default "Todos os ciclos"), Cancelar/Salvar 🟢
- Tipos de permissão observados no Diagnóstico: `manager_to_report`, `peer_to_peer` 🟢

---

## Diagnóstico de Permissões

- **Rota:** `/admin/diagnostico` · **Arquivo:** `src/pages/admin/AdminDiagnostico.tsx`
- **Screenshots:** `screenshots/diagnostico.png` (topo), `diagnostico-2.png`, `diagnostico-3.png`, `diagnostico-4.png` (rolagens)
- **Estado capturado:** preenchido (137 pontos de atenção)
- **Propósito:** "Identifica inconsistências, desequilíbrios e antecipa problemas no próximo ciclo." 🟢

### Estrutura

1. **Banner-resumo:** "137 pontos de atenção — Ciclo ativo: … · 158 permissões · 15 usuários · Fecha em 6 dias" 🟢
2. **5 cards de categoria:** Sem request (67, vermelho), Par reverso (0, verde), Sem cobertura (2, amarelo), Inativo (67, cinza), Sobrecarga (0, roxo) 🟢
3. **Preview: Próximo Ciclo** — nome, período, "Requests a criar: 158", "Ciclo atual fecha em 6 dias"; aviso: "Quando o ciclo encerrar, o próximo será criado com 158 requests. Ajuste permissões antes do fechamento." 🟢
4. **Seções detalhadas por categoria**, cada uma com banner explicativo + ação sugerida + lista `avaliador → avaliado` com badge do tipo de permissão:
   - *Permissões sem request no ciclo ativo (67)*: "Essas pessoas NÃO veem o feedback em 'Meus Feedbacks' e não receberão lembretes. → Clique em 'Criar requests faltantes' para corrigir." 🟢
   - *Usuários sem cobertura (2)*: "fora do processo. Não avaliam e não são avaliadas. → Vá em Permissões → Importar em Massa" 🟢
   - *Permissões com usuários inativos (67)*: "Não causam erro, mas geram requests desnecessários e poluem relatórios."; botão em massa **"Desativar 67 permissão(ões) com inativos"** 🟢
   - *Equilíbrio de carga (5)*: médias avaliador/avaliado, listas "Avaliadores com poucas (≤2)" e "Avaliados com poucas recebidas (≤2)" 🟢
5. Ação de topo: **Exportar** 🟢

---

## Auditoria

- **Rota:** `/admin/auditoria` · **Arquivo:** `src/pages/admin/AdminAuditoria.tsx`
- **Screenshots:** `screenshots/auditoria.png` (topo), `auditoria-2.png`, `auditoria-3.png` (rolagens)
- **Estado capturado:** preenchido (500 logs)
- **Propósito:** "Registro completo de todas as ações realizadas no sistema." 🟢

### Estrutura

1. **4 cards KPI:** Ações hoje (0), Últimos 7 dias (2), Ações sensíveis 7d (0), usuário mais ativo ("Andress Amadeus — 2 ações (7d)") 🟢
2. **Gráfico de barras "Atividade — últimos 14 dias"** com séries Normal (azul) / Sensível (vermelho) 🟢
3. **Usuários Removidos (4)** — seção colapsável destacada em vermelho 🟢
4. **Logs de Auditoria (500)** — filtros: tipo ("Todas"), data, usuário, busca no resumo, botão "Sensíveis"; agrupados por dia ("ONTEM", "QUINTA-FEIRA, 20 DE AGOSTO"…) 🟢
   - Entrada: hora, badge do tipo (Usuário Atualizado, Usuário Criado, Fechamento de Ciclo, Feedback 360° Enviado), badge extra **SENSÍVEL** quando aplicável, resumo em linguagem natural, autor, expansor 🟢
   - Exemplos: "Fechou o ciclo '360 Feedback - Primeira Quinzena (agosto/2026)'. Taxa: 33%. (automático)" — fechamentos automáticos às 08:00 🟢
5. Ação de topo: **Exportar CSV (500)** 🟢

---

## Fale Conosco

- **Rota:** `/admin/faleconosco` · **Arquivo:** `src/pages/admin/AdminFaleConosco.tsx`
- **Screenshot:** `screenshots/fale-conosco.png`
- **Estado capturado:** preenchido
- **Propósito:** "Mensagens de sugestões e críticas enviadas pelos usuários." 🟢

- Filtros: Todos os tipos, Todos os status 🟢
- Tabela: Data, Contato, E-mail, Tipo (badge "Sugestão" azul / "Crítica" vermelho), Status (badge "Resolvido" verde), Ações (Ver) 🟢
- 🔴 LACUNA: tela de envio da mensagem pelo usuário final não capturada; status além de "Resolvido" desconhecidos.

---

## Agenda (Checklist de Compromissos)

- **Rota:** `/admin/agenda` · **Arquivo:** `src/pages/admin/AdminAgenda.tsx`
- **Screenshot:** `screenshots/agenda.png`
- **Estado capturado:** vazio / não conectado
- **Propósito:** "Verifique se todos os compromissos do dia (audiências, atendimentos, entregas) tiveram feedback solicitado ao cliente." 🟢

- Estado não conectado: card central "Conecte sua Google Agenda" + botão **"Conectar Google Agenda"** (OAuth → `src/pages/GoogleCallback.tsx` 🟡) 🟢
- 🔴 LACUNA: estado conectado (lista de compromissos e checklist) não capturado.

---

## Central de Atualizações

- **Rota:** `/admin/atualizacoes` · **Arquivo:** `src/pages/admin/AdminAtualizacoes.tsx`
- **Screenshot:** `screenshots/atualizacoes.png`
- **Estado capturado:** formulário vazio
- **Propósito:** "Publique novidades da plataforma e notifique todos os usuários ativos por email e notificação." 🟢 (consome a edge function `notify-platform-update` 🟡; página de leitura correspondente: `src/pages/Novidades.tsx` 🟡)

- Formulário "Nova atualização": Título (placeholder "Ex: Novos relatórios de feedback disponíveis"), Conteúdo (textarea; "Quebras de linha são preservadas no email e na página de novidades. O texto é salvo automaticamente como rascunho enquanto você digita.") 🟢
- Rodapé: "15 usuário(s) ativo(s) serão notificados" + botão **"Publicar e notificar"** 🟢
- 🔴 LACUNA: histórico de atualizações publicadas (abaixo da dobra) e botão "reenviar notificações" (existente no git log) não capturados.
