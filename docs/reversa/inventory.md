# Inventário do projeto — aesfeedbackinterno

## Resumo executivo

- Produto principal: aplicação web de feedback/avaliações internas com perfis por papel (colaborador, gestor, coordenador, admin).
- Stack principal: React + Vite + TypeScript + Supabase + React Router + Tailwind CSS + TanStack Query.
- Arquitetura observada: SPA com rotas protegidas por papel, UI em componentes reutilizáveis, dados em Supabase e regras de acesso por permissões.
- Padrão de organização: pastas por área funcional e por tipo de tela, com roteamento centralizado em `src/App.tsx`.

## Estrutura principal

- `src/App.tsx` — roteamento central e rotas protegidas por perfil.
- `src/pages/` — telas de negócio por área: `admin`, `gestor`, `coordenador`, `colaborador`, e páginas globais.
- `src/components/` — blocos reutilizáveis da interface e modais.
- `src/contexts/` — providers de autenticação e tema.
- `src/hooks/` — hooks customizados.
- `src/lib/` — utilitários de datas, feedback, auditoria e suporte ao domínio.
- `src/integrations/supabase/` — cliente Supabase e tipagens.
- `supabase/` — configurações, migrations e funções do backend.
- `public/` — assets públicos e script de notificações.

## Linguagens e tecnologia

### Linguagens detectadas

- TypeScript: predominante (`.ts`, `.tsx`)
- JavaScript: suporte residual e configuração do ambiente
- CSS: estilização e temas (`.css`)
- SQL: migrations e funções do banco (`supabase/migrations`, `supabase/functions`)
- Markdown: documentação e contexto do projeto
- JSON/TOML: configuração e metadados

### Frameworks e bibliotecas principais

- React 18
- Vite 5
- React Router DOM 6
- Supabase JS 2.x
- TanStack Query 5.x
- Tailwind CSS 3.x
- shadcn/ui via Radix + componentes customizados
- Vitest + Testing Library para testes
- Recharts, html2canvas, jspdf e xlsx para relatórios e exportação

## Ponto de entrada e configuração

- Entrada da app: `src/main.tsx` e `src/App.tsx`
- Configuração principal: `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`
- Testes: `vitest.config.ts`
- CI/CD/infra: `vercel.json`, `supabase/config.toml`
- Banco e funções: `supabase/migrations/`, `supabase/functions/`

## Módulos funcionais observados

- `admin` — gestão de usuários, ciclos, permissões, relatórios, agenda, configurações
- `gestor` — visão de equipe e pendências de gestor
- `coordenador` — acompanhamento de equipe e relatórios
- `colaborador` — feedback, histórico, relatórios e minhas anotações
- `public` — avaliação pública do cliente
- `feedback` — fluxo de ciclo de avaliação e formulários
- `notifications` — alertas e notificações
- `company-settings` — configurações globais e permissões

## Cobertura de testes

- Estrutura de testes presente em `src/test/` e configuração Vitest.
- Há arquivos de teste e suíte em andamento, embora o foco principal do projeto seja a aplicação e a lógica de feedback integrada ao Supabase.

## Integrations externas

- Supabase (Auth, DB, Edge Functions, storage)
- Vercel para deploy
- Possível uso de canais de notificação e integrações por função serverless do Supabase

## Banco de dados

- Presente.
- Evidências: `supabase/migrations/`, `supabase/functions/`, `supabase/config.toml`, uso massivo de `supabase.from(...)` no frontend.
