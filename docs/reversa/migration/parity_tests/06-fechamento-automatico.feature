# language: pt
# spec-id: PAR-06
# rastreabilidade: target_business_rules.md BR-MIGRAR-005/006; BR-DESCARTAR-003; target_architecture.md AD-05; domain.md § Decisões
# paradigma alvo: scheduler do worker substitui pg_cron; comportamento deve ser equivalente ao job legado (inventário AMB-008 confirma)

@paridade @critico
Funcionalidade: Fechamento automático de ciclo com carência

  @paridade
  Cenário: Ciclo não fecha antes da carência
    Dado um ciclo aberto cuja data final venceu há 2 dias
    Quando o job de fechamento executa
    Então o ciclo permanece "open"

  @paridade
  Cenário: Ciclo fecha após a carência de 3 dias
    Dado um ciclo aberto cuja data final venceu há 4 dias
    Quando o job de fechamento executa
    Então o ciclo passa a "closed" com "closed_at" registrado

  @paridade
  Cenário: Período avaliado estendido adia o fechamento
    Dado um ciclo com "evaluated_end" estendido manualmente para além da data final
    Quando o job executa dentro do período estendido
    Então o ciclo permanece "open"

  @idempotencia
  Cenário: Job re-executado não repete efeitos
    Dado um ciclo já fechado pelo job
    Quando o job executa novamente
    Então o estado não muda e nenhuma notificação duplicada é enfileirada

  @paridade
  Cenário: Expiração de tokens públicos pelo scheduler
    Dado uma avaliação pública "pending" com token vencido
    Quando o job de expiração executa
    Então a avaliação passa a "expired" e o token deixa de abrir o formulário
