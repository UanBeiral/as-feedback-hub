# ADR 001 — SPA React com Supabase como backend

## Contexto

O sistema concentra a navegação em `src/App.tsx`, usa componentes React e React Query no frontend e acessa autenticação, banco, storage e Edge Functions pelo cliente Supabase.

## Decisão

Manter uma SPA React/Vite com roteamento protegido, consultas Supabase no cliente e lógica de apresentação/agregação próxima às páginas.

## Evidências

- 🟢 `src/main.tsx` e `src/App.tsx` são os entry points.
- 🟢 `supabase.from(...)` é usado nas páginas, hooks e componentes.
- 🟢 O histórico Git não mostra uma migração arquitetural para backend separado.

## Alternativas consideradas

- 🟡 Backend REST/BFF separado: não há evidência de sua adoção no repositório.
- 🟡 SSR: incompatível com o padrão atual de Vite SPA e rotas client-side.

## Consequências

- Consultas e agregações ficam simples de desenvolver, mas o frontend concentra lógica de domínio.
- Segurança depende fortemente de RLS e contratos server-side, além da UI.
- Mudanças em schema e Edge Functions impactam diretamente vários componentes.
