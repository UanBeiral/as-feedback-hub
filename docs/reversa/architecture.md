# Arquitetura — A&S Feedback Hub

## Visão

SPA React/Vite em TypeScript, com roteamento no cliente, autenticação e persistência no Supabase. A UI organiza fluxos por papel e domínio; queries React Query acessam diretamente tabelas e Edge Functions. O deploy é configurado para Vercel.

## C4 Contexto

```mermaid
C4Context
    Person(colaborador, "Colaborador", "Envia e recebe feedback e pode acessar relatórios por permissão")
    Person(gestor, "Gestor", "Acompanha equipe, pendências e ciclos")
    Person(coordenador, "Coordenador", "Supervisiona membros coordenados")
    Person(admin, "Admin/RH", "Administra usuários, ciclos, formulários e configurações")
    Person(cliente, "Cliente externo", "Responde avaliação pública por token")
    System(hub, "A&S Feedback Hub", "SPA de feedback e avaliações")
    System_Ext(supabase, "Supabase", "Auth, PostgreSQL, Storage e Edge Functions")
    System_Ext(vercel, "Vercel", "Hospedagem e deploy da SPA")
    System_Ext(google, "Google Calendar", "Agenda, quando configurada")
    Rel(colaborador, hub, "Usa", "HTTPS")
    Rel(gestor, hub, "Usa", "HTTPS")
    Rel(coordenador, hub, "Usa", "HTTPS")
    Rel(admin, hub, "Administra", "HTTPS")
    Rel(cliente, hub, "Responde avaliação", "HTTPS/token")
    Rel(hub, supabase, "Consulta e grava dados", "HTTPS/Supabase JS")
    Rel(hub, vercel, "É publicado por", "Deploy")
    Rel(hub, google, "Sincroniza agenda", "OAuth/API")
```

## Riscos e dívidas

- 🟡 A lógica de agregação e autorização está distribuída em páginas e componentes, aumentando o acoplamento ao schema Supabase.
- 🟡 Há rotas duplicadas para coordenador no `App.tsx`, sinal de manutenção incompleta.
- 🟡 Queries amplas no cliente exigem validação de RLS para garantir isolamento de dados.
- 🟡 Alguns componentes usam `any` e casts para tabelas que não aparecem integralmente nos tipos gerados.
- 🔴 Cobertura de integração com Edge Functions e políticas RLS não foi comprovada.
