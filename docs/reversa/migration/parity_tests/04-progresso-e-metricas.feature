# language: pt
# spec-id: PAR-04
# rastreabilidade: target_business_rules.md BR-MIGRAR-009/028; target_domain_model.md CycleProgress; reports/requirements.md
# paradigma alvo: cálculo único server-side (elimina a triplicação por tela do legado)

@paridade @critico
Funcionalidade: Progresso do ciclo e métricas de relatório

  Contexto:
    Dado um ciclo aberto com requests nos estados: 2 "submitted", 1 "pending", 1 "draft", 1 "cancelled", 1 "waived"

  @paridade
  Cenário: Denominador exclui cancelados e abdicados
    Quando o progresso do ciclo é calculado
    Então o denominador é 4 e os concluídos são 2 (50%)

  @paridade
  Cenário: O mesmo valor de progresso aparece para todos os papéis
    Quando o dashboard do gestor, do coordenador e do admin consultam o progresso do mesmo ciclo
    Então os três recebem exatamente o mesmo valor, vindo do mesmo serviço

  @paridade
  Cenário: Atraso é derivação server-side de prazo mais tolerância
    Dado um request "pending" com prazo vencido dentro da janela de 3 dias
    Quando as pendências são consultadas
    Então o request aparece marcado como atrasado de forma idêntica em telas e relatórios

  @paridade
  Cenário: Engajamento usa só ciclos fechados e exclui pessoas sem requests
    Dado dois ciclos fechados e um aberto, e uma pessoa sem nenhum request
    Quando o relatório de engajamento é gerado
    Então apenas os ciclos fechados entram no cálculo
    E a pessoa sem requests não entra no denominador

  @paridade
  Cenário: Relatório executivo valida escopo antes de gerar
    Dado escopo específico selecionado sem avaliador preenchido
    Quando a geração é solicitada
    Então a operação é recusada com a orientação de preenchimento do legado
