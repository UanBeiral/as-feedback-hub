# Unidade: Avaliação Pública de Cliente — Tarefas

## Pré-requisitos

- [ ] Migrations e RLS/Edge Function para tokens públicos.
- [ ] Formulários e perguntas dinâmicas disponíveis.

## Tarefas

- [ ] T-01, Implementar resolução e validação de token. Origem: `src/pages/public/ClientFeedbackPage.tsx`. Pronto quando inválido/expirado for recusado. Confiança: 🟢.
- [ ] T-02, Carregar formulário e renderizar perguntas. Origem: `ClientFeedbackPage.tsx`. Pronto quando ordem e tipos forem respeitados. Confiança: 🟢.
- [ ] T-03, Implementar validação, notas e textos. Origem: `ClientFeedbackPage.tsx`. Pronto quando entradas inválidas forem rejeitadas. Confiança: 🟢.
- [ ] T-04, Implementar detecção negativa. Origem: `findNegativeMatches`. Pronto quando sinalização coincidir com palavras configuradas. Confiança: 🟢.
- [ ] T-05, Persistir respostas atomicamente e impedir replay. Origem: `client_feedbacks` e migrations. Pronto quando token submetido não puder ser reutilizado. Confiança: 🔴.

## Tarefas de Teste

- [ ] TT-01, token válido, inválido e expirado.
- [ ] TT-02, perguntas obrigatórias e opcionais.
- [ ] TT-03, texto negativo e submissão repetida.
- [ ] TT-04, falha de rede e isolamento de dados. 🔴

## Ordem Sugerida

1. Token; 2. formulário; 3. validação/análise; 4. persistência atômica; 5. segurança.

## Lacunas Pendentes (🔴)

- Confirmar endpoint seguro, replay, RLS e dicionário negativo.
