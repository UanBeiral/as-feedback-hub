# Unidade: Avaliação Pública de Cliente

## Visão Geral

Permite que um cliente responda a uma avaliação por meio de token, sem autenticação interna, usando formulário dinâmico e perguntas configuradas. 🟢

## Responsabilidades

- Validar token, status e expiração. 🟢
- Carregar formulário e perguntas. 🟢
- Coletar notas, textos e dados de contato. 🟢
- Detectar sinais negativos e persistir a submissão. 🟢

## Regras de Negócio

- Token só é aceito quando o registro está `pending` e não expirou. 🟢
- Perguntas são carregadas dinamicamente de `client_feedback_forms` e `client_feedback_form_questions`. 🟢
- Palavras negativas podem sinalizar a avaliação. 🟢
- A validação do fluxo com token é confirmada por guard atômico e `UNIQUE(token)`; o fluxo espontâneo sem token e suas policies permanecem 🔴.

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Validar token público. | Must | Token inválido, usado ou expirado não abre o formulário. |
| RF-02 | Renderizar formulário dinâmico. | Must | Perguntas configuradas aparecem na ordem persistida. |
| RF-03 | Validar e enviar respostas. | Must | Submissão válida cria feedback e altera seu status. |
| RF-04 | Detectar conteúdo negativo. | Should | Entrada com palavra configurada recebe sinalização. |
| RF-05 | Exibir confirmação e impedir reenvio. | Must | Após sucesso, o token não pode ser usado novamente; concorrência retorna confirmação idempotente. 🟢 |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Segurança | Token não deve expor avaliações de outros registros. | `ClientFeedbackPage.tsx` | 🟡 |
| Privacidade | Formulário público deve limitar dados ao feedback alvo. | `ClientFeedbackPage.tsx` | 🟡 |
| Disponibilidade | Erro de submissão deve preservar entradas até nova tentativa. | `ClientFeedbackPage.tsx` | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um token pending e não expirado
Quando o cliente abrir a página
Então o formulário correspondente será exibido

Dado um token expirado ou inválido
Quando o cliente tentar abrir a página
Então o sistema recusará o acesso

Dado respostas válidas
Quando o cliente enviar o formulário
Então a avaliação será persistida e uma confirmação será exibida
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Validação de token e envio | Must | Fluxo central público. |
| Formulário dinâmico | Must | Configuração varia por formulário. |
| Detecção negativa | Should | Complementa triagem. |
| Prevenção server-side de replay | Must | Confirmada para convites com token; espontâneo sem token permanece pendente. 🟡 |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/public/ClientFeedbackPage.tsx` | página, token, formulário, submissão | 🟢 |
| `client_feedbacks` | token, status, expiração e alvo | 🟢 |
| `client_feedback_forms` | formulário público | 🟢 |
| `client_feedback_form_questions` | perguntas dinâmicas | 🟢 |

## Validação humana — 2026-08-25

- 🟢 O fluxo com token usa atualização atômica condicionada a `status = 'pending'`, validade e token presente.
- 🟢 A segunda submissão deve produzir confirmação idempotente, sem duplicidade.
- 🔴 O fluxo espontâneo usa anon key para inserir/atualizar feedback e notificações; as policies de produção precisam ser auditadas e versionadas.
