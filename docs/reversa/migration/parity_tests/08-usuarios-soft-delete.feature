# language: pt
# spec-id: PAR-08
# rastreabilidade: target_business_rules.md BR-MIGRAR-016/018; domain.md § Validação humana; identity (target_domain_model.md)
# paradigma alvo: soft-delete no aggregate Profile + revogação de sessão na auth própria (AD-03)

@paridade @critico
Funcionalidade: Remoção de usuário com histórico preservado

  @paridade
  Cenário: Soft-delete preserva o histórico
    Dado um usuário com feedbacks enviados e recebidos
    Quando o administrador remove o usuário
    Então o perfil passa a status "deleted"
    E todos os feedbacks, requests e registros de auditoria do usuário permanecem consultáveis

  @paridade @critico
  Cenário: Acesso revogado imediatamente
    Dado um usuário removido com sessão ativa
    Quando ele tenta usar a sessão ou renovar o token
    Então o acesso é negado

  @paridade
  Cenário: Usuário inativo não acessa rotas protegidas
    Dado um usuário com status "inactive"
    Quando ele tenta autenticar ou usar sessão existente
    Então o acesso é negado, como no legado

  @paridade
  Cenário: Usuário removido não participa de novos ciclos
    Dado um usuário "deleted" com permissões de feedback antigas
    Quando um novo ciclo é aberto
    Então nenhum request é gerado para ele
