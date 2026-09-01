# language: pt
# spec-id: PAR-03
# rastreabilidade: target_business_rules.md BR-MIGRAR-019/020/021/022; public/requirements.md § Validação humana; target_screens.md SCR-0035
# paradigma alvo: endpoint público próprio com update condicional atômico (AD-06)

@paridade @critico
Funcionalidade: Avaliação pública de cliente por token

  @paridade
  Cenário: Token válido abre o formulário dinâmico
    Dado um registro de avaliação "pending" com token dentro da validade
    Quando o cliente abre a página com o token
    Então o formulário configurado é exibido com as perguntas na ordem persistida

  @paridade
  Cenário: Token expirado ou inválido é recusado
    Dado um token expirado, já usado ou inexistente
    Quando o cliente tenta abrir a página
    Então o acesso é recusado com a mensagem equivalente à do legado

  @paridade
  Cenário: Submissão válida persiste e confirma
    Dado um formulário aberto por token válido
    Quando o cliente envia respostas válidas
    Então a avaliação passa a "submitted" com "submitted_at" registrado
    E a confirmação é exibida

  @idempotencia @critico
  Cenário: Segunda submissão concorrente retorna confirmação idempotente
    Dado uma avaliação já "submitted"
    Quando uma segunda submissão chega com o mesmo token
    Então nenhum registro duplicado é criado
    E a resposta é a mesma confirmação de sucesso, sem erro exposto ao cliente

  @paridade
  Cenário: Sinalização por conteúdo negativo
    Quando o cliente envia nota baixa ou texto com palavra negativa configurada no tenant
    Então a avaliação é marcada com "has_negative" verdadeiro

  @paridade
  Cenário: Fluxo espontâneo controlado por flag do tenant
    Dado um tenant com o fluxo espontâneo desabilitado
    Quando uma submissão espontânea (sem token) é tentada
    Então a API recusa
