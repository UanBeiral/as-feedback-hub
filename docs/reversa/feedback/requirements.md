# Unidade: Feedback Interno

## Visão Geral

O núcleo de feedback interno administra ciclos, permissões entre avaliadores e avaliados, requests, formulários e respostas. 🟢 É o fluxo central que transforma um ciclo aberto em avaliações rastreáveis.

## Responsabilidades

- Criar e transicionar ciclos de feedback. 🟢
- Gerar requests conforme permissões ativas. 🟢
- Aplicar formulários e coletar respostas. 🟢
- Calcular progresso e estados do ciclo. 🟢

## Regras de Negócio

- Abrir ciclo gera requests para pares ativos em `feedback_permissions`. 🟢
- Permissão `peer_to_peer` deve criar relação reversa. 🟢
- Requests possuem estados `pending`, `draft`, `submitted`, `cancelled` e `waived`. 🟢
- Ciclos têm estados de criação, abertura, fechamento e arquivamento. 🟢
- Políticas RLS e efeitos de Edge Functions não foram confirmados. 🔴

## Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | Criar e editar ciclos com formulário e datas. | Must | Dado dados válidos, salvar cria ciclo consultável. |
| RF-02 | Abrir ciclo e gerar requests elegíveis. | Must | Ao abrir, cada par ativo permitido recebe request único. |
| RF-03 | Gerenciar permissões por par, tipo e ciclo. | Must | Permissões ativas controlam a geração de requests. |
| RF-04 | Preencher e enviar formulário de feedback. | Must | Envio persiste respostas e muda request para `submitted`. |
| RF-05 | Salvar rascunho e retomar avaliação. | Should | Rascunho pode ser retomado sem perder respostas existentes. |
| RF-06 | Fechar e arquivar ciclo. | Should | Transição válida atualiza o estado e métricas. |

## Requisitos Não Funcionais

| Tipo | Requisito inferido | Evidência | Confiança |
|------|--------------------|-----------|-----------|
| Segurança | Ciclos e respostas exigem rota protegida e permissões. | `ProtectedRoute`, páginas admin | 🟢 |
| Consistência | Requests devem ser únicos por par/ciclo/formulário. | `generateFeedbackRequests.ts` | 🟡 |
| Disponibilidade | Falha de notificação não deve desfazer geração principal. | hooks de notificação | 🟡 |

## Critérios de Aceitação

```gherkin
Dado um ciclo draft com permissões ativas
Quando o administrador o abrir
Então requests serão criados para os pares elegíveis

Dado um request pending
Quando o avaliador enviar respostas válidas
Então respostas serão persistidas e o request ficará submitted

Dado uma transição inválida
Quando ela for solicitada
Então o estado não mudará e a interface informará o erro
```

## Prioridade (MoSCoW)

| Requisito | MoSCoW | Justificativa |
|-----------|--------|---------------|
| Ciclos, permissões e requests | Must | Núcleo do produto. |
| Envio de respostas | Must | Resultado principal do ciclo. |
| Rascunhos e histórico | Should | Importante para continuidade. |
| Integrações não confirmadas | Won't | Exige validação adicional. |

## Rastreabilidade de Código

| Arquivo | Função / Classe | Cobertura |
|---------|-----------------|-----------|
| `src/pages/admin/AdminCiclos.tsx` | transições e geração de requests | 🟢 |
| `src/lib/generateFeedbackRequests.ts` | geração por membro/par | 🟢 |
| `src/pages/admin/AdminPermissoes.tsx` | permissões e reversão peer | 🟢 |
| `src/pages/Dashboard.tsx` | progresso do ciclo | 🟢 |
| `src/lib/createAuditLog.ts` | auditoria auxiliar | 🟢 |
