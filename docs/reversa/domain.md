# Domínio — A&S Feedback Hub

## Glossário

| Termo | Significado | Confiança |
|---|---|---|
| Ciclo | Janela temporal em que requests de feedback são gerados e respondidos. | 🟢 CONFIRMADO |
| Request | Solicitação de avaliação entre um avaliador (`giver`) e uma pessoa avaliada (`receiver`) dentro de um ciclo. | 🟢 CONFIRMADO |
| Feedback livre | Mensagem não estruturada enviada entre pessoas, podendo ser anônima e sensível. | 🟢 CONFIRMADO |
| Avaliação de cliente | Avaliação pública vinculada a um profissional por token e formulário configurável. | 🟢 CONFIRMADO |
| Papel ativo | Contexto de navegação selecionado quando um perfil possui mais de uma capacidade. | 🟢 CONFIRMADO |
| Período avaliado | Intervalo efetivo usado para decidir se um ciclo/feedback pode ser respondido, com possibilidade de extensão manual. | 🟢 CONFIRMADO |

## Regras de negócio

- 🟢 **CONFIRMADO:** somente usuários ativos participam da geração de requests.
- 🟢 **CONFIRMADO:** a abertura de um ciclo cria requests a partir das permissões ativas.
- 🟢 **CONFIRMADO:** requests cancelados e abdicados não entram no denominador de progresso; requests enviados representam conclusão.
- 🟢 **CONFIRMADO:** requests pendentes ou em rascunho podem ficar visualmente expirados após o prazo e a tolerância configurada.
- 🟢 **CONFIRMADO:** o envio de um feedback exige respostas válidas conforme o formulário e registra `submitted_at`.
- 🟢 **CONFIRMADO:** uma avaliação pública só pode ser enviada quando o token está pendente e dentro da validade.
- 🟢 **CONFIRMADO:** feedbacks de cliente podem ser sinalizados por nota baixa ou palavras negativas.
- 🟡 **INFERIDO:** regras de visibilidade de dados são reforçadas por RLS do Supabase, além das proteções de rota e flags de UI.
- 🔴 **LACUNA:** não há evidência suficiente no frontend para determinar a política final de retenção, anonimização ou exportação de dados sensíveis.

## Decisões e sinais do histórico

- 🟢 **CONFIRMADO:** `fix: carencia de 3 dias antes de fechar ciclo` indica uma tolerância operacional antes do encerramento automático.
- 🟢 **CONFIRMADO:** commits sobre período avaliado e extensões manuais indicam que a janela de resposta pode divergir das datas básicas do ciclo.
- 🟢 **CONFIRMADO:** commits sobre envio em background e `waitUntil` mostram que notificações devem continuar sem bloquear a operação principal, com compatibilidade específica para Deno Deploy.
- 🟢 **CONFIRMADO:** o relatório PDF e o envio por email são capacidades explícitas do produto, com tratamento de falha separado da montagem do relatório.

## Lacunas de domínio

- 🔴 **LACUNA:** estados e transições de solicitações de entrada de membros e mensagens de contato usam vocabulários próprios e não foram consolidados como máquinas centrais.
- 🔴 **LACUNA:** contratos das Edge Functions e regras de autorização no backend precisam ser confirmados diretamente nas funções/migrations.

## Validação humana — 2026-08-25

- 🟢 Usuários removidos devem permanecer como `profiles.status = 'deleted'`; o histórico deve ser preservado e o acesso Auth revogado.
- 🟡 Relatórios de clientes devem filtrar server-side pelo solicitante; o prazo de retenção, anonimização e exclusão ainda não foi definido.
- 🟡 `feedback_contacts` segue `novo → em_andamento → resolvido`; `team_requests` tem aprovação/rejeição, mas sua máquina completa permanece pendente.
