# Máquinas de Estado

## Ciclo de feedback

```mermaid
stateDiagram-v2
    [*] --> draft: criar ciclo
    draft --> open: abrir ciclo
    open --> closed: fechar ciclo / tolerância
    closed --> published: publicar resultados
    published --> archived: arquivar
    draft --> archived: arquivar sem abrir
```

🟢 **CONFIRMADO:** os estados aparecem nas operações de `AdminCiclos.tsx`. Os gatilhos acima são os nomes observados nas ações de interface; a aplicação de transições adicionais no banco é 🔴 **LACUNA**.

## Request de feedback interno

```mermaid
stateDiagram-v2
    [*] --> pending: gerar request
    pending --> draft: iniciar preenchimento
    draft --> submitted: enviar respostas
    pending --> waived: abdicar
    draft --> waived: abdicar
    waived --> pending: retomar
    pending --> cancelled: cancelar com justificativa
    draft --> cancelled: cancelar com justificativa
    pending --> expired: prazo + carência
    draft --> expired: prazo + carência
    submitted --> reviewed: revisar, quando aplicável
```

- 🟢 `pending`, `draft` e `submitted` são usados diretamente no formulário e dashboards.
- 🟢 `waived`, `cancelled` e `expired` aparecem nas visões de histórico, pendências e relatórios.
- 🟡 `reviewed` aparece no mapa de status de relatórios, mas seu gatilho não foi localizado.
- 🟢 Requests em `cancelled` ou `waived` são excluídos de várias métricas de progresso.

## Avaliação pública de cliente

```mermaid
stateDiagram-v2
    [*] --> pending: criar token
    pending --> submitted: cliente envia avaliação
    pending --> expired: token ou prazo expira
```

🟢 **CONFIRMADO:** a página pública valida `status = pending` e expiração antes de atualizar para `submitted`.

## Validação humana — 2026-08-25

- 🟢 `feedback_contacts`: `novo → em_andamento → resolvido`.
- 🟡 `team_requests`: aprovação/rejeição pelo gestor da própria equipe foram confirmadas; cancelamento, expiração e demais transições permanecem sem contrato formal.
