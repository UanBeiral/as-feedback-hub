# Dependências e versões — aesfeedbackinterno

## Gerenciador de pacotes

- npm

## Dependências principais

- React: `18.3.1`
- React DOM: `18.3.1`
- React Router DOM: `6.30.1`
- @supabase/supabase-js: `2.101.1`
- @tanstack/react-query: `5.83.0`
- tailwindcss: `3.4.17`
- zod: `3.25.76`
- recharts: `2.15.4`
- lucide-react: `0.462.0`
- date-fns: `3.6.0`
- xlsx: `0.18.5`
- jspdf: `4.2.1`
- html2canvas: `1.4.1`
- react-hook-form: `7.61.1`
- @hookform/resolvers: `3.10.0`

## Dependências de desenvolvimento

- vite: `5.4.19`
- @vitejs/plugin-react-swc: `3.11.0`
- typescript: `5.8.3`
- vitest: `3.2.4`
- @testing-library/react: `16.0.0`
- @testing-library/jest-dom: `6.6.0`
- eslint: `9.32.0`
- tailwindcss: `3.4.17`
- postcss: `8.5.6`
- autoprefixer: `10.4.21`
- @playwright/test: `1.57.0`

## Observações

- A aplicação usa estrutura de UI moderna com Radix + shadcn, mas as dependências de UI são consumidas via componentes customizados e wrappers do design system.
- A integração com banco e autenticação ocorre via Supabase em um cliente frontend gerado em `src/integrations/supabase/client.ts`.
