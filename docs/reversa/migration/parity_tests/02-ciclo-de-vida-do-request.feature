# language: pt
# spec-id: PAR-02
# rastreabilidade: state-machines.md § Request; target_business_rules.md BR-MIGRAR-003/008/012; target_domain_model.md FeedbackRequest
# paradigma alvo: OO com DI — transições apenas via comandos do aggregate; status "reviewed" omitido (AMB-003)

@paridade @critico
Funcionalidade: Ciclo de vida do request de feedback interno

  Contexto:
    Dado um request "pending" de um ciclo aberto, com formulário de perguntas obrigatórias

  @paridade
  Cenário: Rascunho preserva respostas
    Quando o avaliador salva um rascunho com respostas parciais
    Então o request passa a "draft"
    E ao retomar, as respostas salvas estão presentes sem perda

  @paridade
  Cenário: Envio exige respostas válidas e grava submitted_at
    Quando o avaliador envia respostas válidas conforme o formulário
    Então o request passa a "submitted" com "submitted_at" registrado
    E as respostas ficam persistidas em feedback_answers

  @paridade
  Cenário: Envio com respostas inválidas é recusado
    Quando o avaliador envia respostas que violam as regras do formulário
    Então a API recusa, o request permanece no estado anterior e nada é persistido

  @paridade
  Cenário: Abdicar e retomar
    Quando o avaliador abdica do request
    Então o request passa a "waived" e sai do denominador de progresso
    Quando o avaliador retoma o request
    Então o request volta a "pending"

  @paridade
  Cenário: Cancelamento exige justificativa e audita
    Quando o gestor cancela o request com uma justificativa
    Então o request passa a "cancelled" com a justificativa associada
    E um evento de auditoria com "actor_id" do gestor é registrado

  @paridade
  Cenário: Transição inválida é recusada
    Dado um request "submitted"
    Quando qualquer transição para "draft" ou "cancelled" é solicitada
    Então a API recusa e o estado não muda
