# Lacunas da Revisão — A&S Feedback Hub

> Gerado pelo Revisor em 2026-08-25. As lacunas abaixo permanecem após o processamento das respostas humanas.

## Resolvidas ou reduzidas

- Escopo geral de autorização: confirmado como server-side + RLS e negar por padrão.
- Replay do fluxo público com token: confirmado como atualização atômica com confirmação idempotente.
- Estrutura e constraints principais dos caches de IA: confirmadas em produção, mas ainda não versionadas.
- Catálogo atual de `company_settings`: confirmado como oito chaves globais por escritório.
- Escopo de histórico por papel: confirmado com `view_history_of`, equipes autorizadas e bloqueio por padrão.

## Críticas

- RLS e autorização efetiva por tabela/papel não foram consolidadas.
- A proteção server-side contra replay e concorrência da avaliação pública não foi confirmada.
- Os contratos e permissões das Edge Functions de IA, email e notificações não estão especificados.
- O schema dos caches de IA não foi confirmado.

## Moderadas

- Retenção, anonimização e exportação de dados sensíveis não foram definidas.
- O escopo de acesso ao histórico de outras pessoas não foi validado.
- Idempotência e constraints na geração concorrente de requests não foram confirmadas.
- Catálogo/defaults de configurações e notificações permanecem incompletos.
- Contrato da exportação XLSX e campos de auditoria/notificação do coordenador não foram confirmados.
- Estados de solicitações de membros e mensagens de contato não foram consolidados.

## Cosméticas / operacionais

- Requisitos de logs, métricas, traces e alertas não foram encontrados para vários módulos.
- Compatibilidade detalhada de PDF/email e comportamento de falhas depende de contratos externos.
