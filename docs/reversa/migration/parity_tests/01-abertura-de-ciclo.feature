# language: pt
# spec-id: PAR-01
# rastreabilidade: target_business_rules.md BR-MIGRAR-001/002/010/011; target_architecture.md AD-02/AD-04; state-machines.md § Ciclo
# paradigma alvo: OO com DI — invariantes no aggregate FeedbackCycle, validadas na API (bypass de UI)

@paridade @critico
Funcionalidade: Abertura de ciclo e geração de requests

  Contexto:
    Dado um tenant ativo com usuários ativos e permissões de feedback ativas
    E um ciclo em estado "draft" com formulário e datas válidas

  @paridade
  Cenário: Abrir ciclo gera requests para os pares elegíveis
    Quando o administrador abre o ciclo via "POST /cycles/{id}/open"
    Então o ciclo passa ao estado "open"
    E cada par (avaliador, avaliado) com permissão ativa recebe exatamente um request "pending"
    E usuários com status diferente de "active" não recebem request

  @idempotencia
  Cenário: Reabrir a geração não duplica requests
    Dado que o ciclo já foi aberto e os requests foram gerados
    Quando a geração é executada novamente para o mesmo ciclo
    Então nenhum request duplicado é criado para o mesmo par, ciclo e formulário

  @paridade
  Cenário: Permissão peer_to_peer cria a relação reversa
    Dado uma permissão "peer_to_peer" de A para B sem permissão reversa
    Quando a permissão é salva via API
    Então a permissão de B para A também existe ao fim da transação

  @paridade
  Cenário: Limite de concorrência por frequência bloqueia com alerta
    Dado um ciclo aberto da frequência "mensal" no tenant
    Quando o administrador tenta abrir outro ciclo da mesma frequência
    Então a API recusa com o alerta de janela ocupada equivalente ao do legado

  @paridade
  Cenário: Invariante falha na API, não na UI
    Dado um usuário sem papel "admin" ou "rh"
    Quando ele chama "POST /cycles/{id}/open" diretamente
    Então a API responde com negação de acesso e o ciclo permanece "draft"
