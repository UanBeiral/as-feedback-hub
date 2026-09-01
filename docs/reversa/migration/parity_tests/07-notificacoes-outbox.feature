# language: pt
# spec-id: PAR-07
# rastreabilidade: target_business_rules.md BR-MIGRAR-023/024/025; BR-DESCARTAR-002; AD-04; notifications/requirements.md § Validação humana
# paradigma alvo: transactional outbox + worker (sincrônico → assíncrono nos efeitos auxiliares — dimensões: ordem, idempotência, falha de fila)

@paridade @critico
Funcionalidade: Notificações via outbox e tolerância a falha auxiliar

  @paridade
  Cenário: Efeito auxiliar não desfaz operação principal
    Dado o worker de notificações indisponível
    Quando um gestor cancela um request com justificativa
    Então o cancelamento é persistido com sucesso
    E a mensagem de outbox fica registrada para despacho posterior

  @idempotencia @critico
  Cenário: Idempotência por chave update_id + user_id
    Dado uma comunicação de ciclo destinada a um usuário
    Quando o worker processa a mesma mensagem de outbox duas vezes
    Então o usuário recebe exatamente uma notificação

  @ordem
  Cenário: Retry com backoff e DLQ
    Dado uma mensagem de outbox cujo despacho falha repetidamente
    Quando o número máximo de tentativas é atingido
    Então a mensagem vai para o estado "dead" (DLQ) sem bloquear as demais
    E a operação principal de origem permanece intacta

  @paridade
  Cenário: Não lida é read_at nulo
    Dado uma notificação criada para um usuário
    Então ela aparece como não lida enquanto "read_at" for nulo
    Quando o usuário a marca como lida
    Então "read_at" é registrado e a contagem do sino diminui

  @paridade
  Cenário: Falha de email não invalida o relatório gerado
    Dado um relatório executivo gerado com sucesso
    Quando o envio por email falha no provedor
    Então o relatório permanece disponível para download
    E a falha de email é informada separadamente, como no legado
