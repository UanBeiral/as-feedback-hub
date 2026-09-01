# language: pt
# spec-id: PAR-SCR-01
# rastreabilidade: target_screens.md § Subset LITERAL; screens/golden/manifest.yaml; screen_modernization_decision.md (híbrido)
# nota: golden do sistema novo ainda não capturado (v1 sem captura automatizada) — validação manual contra os screenshots do Visor até lá

@paridade-visual @critico
Funcionalidade: Paridade visual do subset literal (35 telas)

  Esquema do Cenário: Tela literal equivale ao screenshot do legado
    Dado a tela "<tela>" implementada no sistema novo com dados de staging equivalentes aos da captura
    Quando a tela é renderizada no viewport de referência (1440x900, tema claro)
    Então o layout, a hierarquia e todos os textos são equivalentes ao golden "<golden>"
    E nenhuma cor renderizada diverge dos tokens do design system (DEV-003/006 aceitas)

    Exemplos:
      | tela                                   | golden                                  |
      | Login                                  | golden/auth-login                       |
      | Meu Perfil                             | golden/auth-perfil                      |
      | Painel Administrativo                  | golden/admin-dashboard                  |
      | Anotações Realizadas                   | golden/admin-anotacoes-realizadas       |
      | Minha Equipe (Admin)                   | golden/admin-equipe                     |
      | Histórico da Equipe (Admin)            | golden/admin-historico-equipe           |
      | Usuários                               | golden/admin-usuarios                   |
      | Departamentos                          | golden/admin-departamentos              |
      | Ciclos de Feedback                     | golden/admin-ciclos                     |
      | Permissões de Feedback                 | golden/admin-permissoes                 |
      | Diagnóstico de Permissões              | golden/admin-diagnostico                |
      | Auditoria                              | golden/admin-auditoria                  |
      | Fale Conosco                           | golden/admin-faleconosco                |
      | Agenda (não conectado)                 | golden/admin-agenda                     |
      | Central de Atualizações                | golden/admin-atualizacoes               |
      | Relatórios — Dados e Filtros           | golden/reports-dados-filtros            |
      | Emitir Relatório                       | golden/reports-emitir                   |
      | Formulários                            | golden/feedback-formularios             |
      | Minhas Anotações                       | golden/feedback-minhas-anotacoes        |
      | Meus Feedbacks                         | golden/feedback-meus-feedbacks          |
      | Meu Histórico                          | golden/feedback-meu-historico           |
      | Caderno do Ciclo                       | golden/feedback-caderno-ciclo           |
      | Modal Dar Feedback Livre               | golden/feedback-livre-modal             |
      | Configurações                          | golden/company-settings                 |
      | Início (Coordenador)                   | golden/coordenador-inicio               |
      | Minha Equipe (Coordenador)             | golden/coordenador-equipe               |
      | Feedbacks Pendentes (Coordenador)      | golden/coordenador-pendentes            |
      | Histórico da Equipe (Coordenador)      | golden/coordenador-historico            |
      | Início (Gestor)                        | golden/gestor-inicio                    |
      | Minha Equipe (Gestor)                  | golden/gestor-equipe                    |
      | Feedbacks Pendentes (Gestor)           | golden/gestor-pendentes                 |
      | Histórico da Equipe (Gestor)           | golden/gestor-historico                 |
      | Início (Colaborador)                   | golden/colaborador-dashboard            |
      | Avaliações de Clientes                 | golden/colaborador-avaliacoes-clientes  |
      | Avaliação Pública (16 etapas)          | golden/public-fluxo                     |
