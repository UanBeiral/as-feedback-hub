# ADR 002 — Ciclos com estados explícitos e tolerância de fechamento

## Contexto

O produto precisa abrir ciclos, permitir preenchimento, encerrar pendências e publicar resultados. O histórico recente registra correção para carência de três dias antes do fechamento.

## Decisão

Representar o ciclo com estados `draft`, `open`, `closed`, `published` e `archived`, mantendo requests pendentes/draft visíveis durante a janela de tolerância e tratando o prazo visualmente nos relatórios e dashboards.

## Evidências

- 🟢 Estados e mutações estão em `src/pages/admin/AdminCiclos.tsx`.
- 🟢 A função `getVisualStatus` diferencia prazo de estado persistido.
- 🟢 Commit `e9ffbe9` registra a carência de três dias.

## Alternativas consideradas

- 🟡 Encerrar imediatamente na data final: contradiz o hotfix observado.
- 🟡 Inferir expiração apenas no banco: não explica o status visual calculado no cliente.

## Consequências

- Usuários recebem tempo operacional adicional sem alterar necessariamente o status persistido.
- Métricas precisam distinguir status real e status visual.
- Alterações de prazo devem ser acompanhadas por testes de datas e timezone.
