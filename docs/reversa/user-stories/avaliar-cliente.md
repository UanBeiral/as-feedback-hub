# User Stories — Avaliações de Cliente

## US-01 — Solicitar avaliação

Como colaborador, gestor ou coordenador autorizado, quero solicitar uma avaliação de cliente para um profissional ativo, para coletar percepção externa sobre o atendimento.

### Critérios de aceite

- Dado um profissional ativo, quando a solicitação for confirmada, então um fluxo de avaliação é criado. 🟢
- Dado um profissional inativo, quando ele for selecionado, então a solicitação não é permitida. 🟢
- Em caso de falha, a interface informa o erro e não sinaliza criação concluída. 🟡

## US-02 — Responder por link público

Como cliente, quero responder um formulário por link seguro, para avaliar o profissional sem criar uma conta interna.

### Critérios de aceite

- Token pendente e não expirado abre o formulário correto. 🟢
- Token inválido, expirado ou já usado não permite submissão. 🟢/🔴 validação server-side.
- Respostas válidas alteram o feedback para submetido e exibem confirmação. 🟢

## US-03 — Consultar avaliações

Como usuário autorizado, quero filtrar avaliações por pessoa, cliente, status e período, para acompanhar resultados e prioridades.

### Critérios de aceite

- Filtros alteram a lista e as métricas apresentadas. 🟢
- Telefones são mascarados na listagem. 🟢
- Respostas detalhadas aparecem somente quando a flag do perfil permite. 🟢

## US-04 — Gerar relatório de clientes

Como usuário com permissão de relatórios, quero exportar os resultados filtrados, para compartilhar ou analisar os dados fora da aplicação.

### Critérios de aceite

- O CSV contém somente registros filtrados e usa separador `;`. 🟢
- Usuário sem `can_generate_reports` é redirecionado e não exporta. 🟢

## Lacunas

- 🔴 Confirmar replay, RLS e contrato de persistência do token público.
