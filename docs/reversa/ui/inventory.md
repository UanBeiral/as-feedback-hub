# Inventário de Telas — A&S Feedback Hub

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de **83 screenshots** do sistema em produção (`aesfeedbackinterno.vercel.app`), capturados pelo usuário em 28/08/2026 (sessões 10:11–10:28 e 10:45–10:58).
> Granularidade das units: `hybrid` (conforme `.reversa/config.toml [specs]`). Mapeamentos ambíguos resolvidos com o usuário em 28/08/2026 (Minhas Anotações → `feedback`; Meu Perfil → `auth`).
> Detalhes de cada tela: `_reversa_sdd/<unit>/screens.md`. Originais: `_reversa_sdd/<unit>/screenshots/`.

## Resumo

- **45 telas/etapas distintas** documentadas (30 páginas + 10 modais/painéis + fluxo público em 16 etapas), em **83 capturas**
- **Papéis cobertos:** Administrador ✅, Gestor ✅, Coordenador ✅, Colaborador ✅ (parcial), **fluxo público do cliente ✅ completo**

## Telas documentadas

| # | Tela | Rota | Unit | Capturas | Estados |
|---|------|------|------|----------|---------|
| 1 | Login | `/login` | auth | 1 | vazio |
| 2 | Meu Perfil | `/perfil` | auth | 1 | preenchido |
| 3 | Painel Administrativo | `/admin` | admin | 4 | ciclo vazio + seções preenchidas |
| 4 | Anotações Realizadas | `/admin/anotacoes-realizadas` | admin | 2 | preenchido (60 anotações, badge Áudio) |
| 5 | Minha Equipe (admin) | `/admin/equipe` | admin | 2 | tabela + modal Adicionar Membro |
| 6 | Histórico da Equipe (admin) | `/admin/historico-equipe` | admin | 2 | livre preenchido; clientes/360° vazios |
| 7 | Usuários | `/admin/usuarios` | admin | 2 | tabela + modal Novo Usuário |
| 8 | Departamentos | `/admin/departamentos` | admin | 2 | tabela + modal Novo Departamento |
| 9 | Ciclos de Feedback | `/admin/ciclos` | admin | 5 | tabela + wizard Novo (2 estados extras) e Editar |
| 10 | Permissões de Feedback | `/admin/permissoes` | admin | 2 | lista + modal Nova Permissão |
| 11 | Diagnóstico de Permissões | `/admin/diagnostico` | admin | 4 | preenchido (137 pontos) |
| 12 | Auditoria | `/admin/auditoria` | admin | 3 | preenchido (500 logs) |
| 13 | Fale Conosco | `/admin/faleconosco` | admin | 1 | preenchido |
| 14 | Agenda (Compromissos) | `/admin/agenda` | admin | 1 | não conectado (vazio) |
| 15 | Central de Atualizações | `/admin/atualizacoes` | admin | 1 | formulário vazio |
| 16 | Relatórios — Dados e Filtros | `/admin/relatorios` | reports | 2 | aba Clientes preenchida (49) |
| 17 | Emitir Relatório | `/admin/relatorio-feedback` | reports | 1 | formulário vazio |
| 18 | Formulários | `/admin/formularios` | feedback | 2 | tabela + modal (validação nativa) |
| 19 | Minhas Anotações | `/minhas-anotacoes` | feedback | 1 | vazio |
| 20 | Meus Feedbacks | `/meus-feedbacks` | feedback | 3 | vazio (coordenador, gestor, colaborador) |
| 21 | Meu Histórico | `/historico` | feedback | 3 | vazio (coordenador, gestor, colaborador) |
| 22 | Caderno do Ciclo (painel + widget) | flutuante em todas as telas | feedback | 2 | vazio; com Gravar Áudio |
| 23 | Modal Dar Feedback Livre | banner nos dashboards | feedback | 2 | vazio; anonimato + denúncia grave |
| 24 | Configurações | `/admin/configuracoes` | company-settings | 1 | preenchido |
| 25 | Início (Coordenador) | `/coordenador` | coordenador | 1 | sem pendências |
| 26 | Minha Equipe (Coordenador) | `/coordenador/equipe` | coordenador | 1 | 1 membro |
| 27 | Feedbacks Pendentes (Coord.) | `/coordenador/pendentes` | coordenador | 1 | vazio |
| 28 | Histórico da Equipe (Coord.) | `/coordenador/historico` | coordenador | 1 | livre preenchido |
| 29 | Início (Gestor) | `/gestor` | gestor | 2 | sem pendências; ranking/atenção vazios |
| 30 | Minha Equipe (Gestor) | `/gestor/equipe` | gestor | 1 | 2 membros |
| 31 | Feedbacks Pendentes (Gestor) | `/gestor/pendentes` | gestor | 1 | vazio |
| 32 | Histórico da Equipe (Gestor) | `/gestor/historico` | gestor | 2 | livre preenchido |
| 33 | Início (Colaborador) | `/dashboard` | colaborador | 3 | sem feedbacks |
| 34 | Avaliações de Clientes | `/avaliacoes-clientes` | colaborador | 3 | 1 pendente/49 respondidas + modal Solicitar (com aviso de duplicidade) |
| 35 | Avaliação Pública do Cliente | `/avaliacao?token=…` | public | 16 | fluxo completo: boas-vindas → identificação → motivação (ramos elogio/problema) → 9 perguntas (estrelas 0–10 + textos) → tipo de serviço → agradecimento |

## Padrões transversais observados

- **Shell autenticado:** sidebar azul-escuro (logo + razão social, menu por papel, Sair) e cabeçalho (busca ⌘K, alternador de tema, sino de notificações, nome + badge de papel colorido + avatar) 🟢
- **Badges de papel:** Administrador (cinza), Coordenador (roxo), Gestor (dourado — "Gestor (Admin)" quando admin visualiza como gestor), Colaborador (cinza claro) 🟢
- **Botão flutuante amarelo (📖) = Caderno do Ciclo** — widget global de anotações rápidas com áudio 🟢
- **Padrões de listagem:** filtros + busca, colunas ordenáveis, exportação Excel/CSV, badges de status, estados vazios ilustrados 🟢
- **Modais** para criação/edição; **wizard de 3 passos** (ciclos, com validação nativa HTML5); **wizard público** com barra de progresso e ramos condicionais 🟢
- **Fluxo público:** identidade visual própria (gradiente roxo, card central), sem shell; escala de 10 estrelas = notas 0–10 dos relatórios 🟢

## Telas conhecidas do código SEM captura 🔴

| Tela | Arquivo | Unit provável |
|---|---|---|
| Formulário de resposta 360° | `src/pages/FeedbackForm.tsx` | feedback |
| Histórico por pessoa | `src/pages/HistoricoPessoa.tsx` | feedback |
| Reset de senha | `src/pages/ResetPassword.tsx` | auth |
| Novidades (leitura de atualizações) | `src/pages/Novidades.tsx` | notifications |
| Callback Google OAuth | `src/pages/GoogleCallback.tsx` | admin/agenda |
| Index / NotFound | `src/pages/Index.tsx`, `NotFound.tsx` | auth/shell |
| Colaborador: Dashboard Clientes, Histórico Equipe, Relatórios Clientes | `src/pages/colaborador/Colaborador{DashboardClientes,HistoricoEquipe,RelatoriosClientes}.tsx` | colaborador |
| Editor de perguntas do formulário | (botão "Perguntas" em `/admin/formularios`) | feedback |
| Pergunta 6 de 9 do fluxo público | (entre Q5 e Q7; provável NPS/recomendação) | public |
| Agenda conectada ao Google | `/admin/agenda` estado conectado | admin |
