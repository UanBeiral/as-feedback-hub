# Unidade: Avaliação Pública de Cliente — Design Técnico

## Interface

| Símbolo | Assinatura | Retorno | Observação |
|---------|-----------|---------|------------|
| `ClientFeedbackPage` | `()` | `JSX.Element` | Resolve token da URL, consulta feedback/formulário e controla envio. 🟢 |
| `findNegativeMatches` | `(entries)` | `NegativeMatch[]` | Procura palavras negativas nas respostas. 🟢 |

## Fluxo Principal

1. Ler token da rota pública. 🟢
2. Buscar `client_feedbacks` e validar `status`/`token_expires_at`. 🟢
3. Carregar formulário e perguntas relacionadas. 🟢
4. Validar entradas, calcular notas/sinais e inserir respostas. 🟢
5. Atualizar status e mostrar confirmação. 🟡

## Fluxos Alternativos

- Token inválido/expirado: estado de acesso recusado. 🟢
- Pergunta sem resposta: validação conforme tipo/configuração. 🟡
- Texto negativo: marcar `has_negative` ou sinalização equivalente. 🟢
- Falha de rede: manter formulário e informar erro. 🟡

## Dependências

Supabase, tabelas de feedback externo, formulário dinâmico e componentes de UI. 🟢

## Decisões de Design Identificadas

| Decisão | Evidência | Confiança |
|---------|-----------|-----------|
| Acesso público é baseado em token. | `ClientFeedbackPage.tsx` | 🟢 |
| Formulário é dirigido por dados. | queries de forms/questions | 🟢 |
| Análise negativa ocorre no cliente. | `findNegativeMatches` | 🟢 |

## Estado Interno

Token, feedback, perguntas, respostas, loading, erro e confirmação são estado local/remoto. 🟢

## Observabilidade

Não foram encontrados logs estruturados ou métricas da submissão. 🔴

## Riscos e Lacunas

- 🔴 Confirmar atomicidade, replay e autorização da mutação.
- 🟡 Confirmar dicionário de palavras negativas e idioma.
