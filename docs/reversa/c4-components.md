# C4 Componentes

## Frontend SPA

```mermaid
C4Component
    Container_Boundary(spa, "Frontend SPA") {
        Component(routes, "App Router", "React Router", "Seleciona rotas públicas e protegidas")
        Component(auth, "AuthContext", "React Context + Supabase Auth", "Sessão, perfil e papel ativo")
        Component(layout, "AppLayout/Sidebar", "React", "Navegação por papel e flags")
        Component(pages, "Páginas de domínio", "React", "Feedback, ciclos, dashboards e relatórios")
        Component(shared, "Componentes compartilhados", "React/shadcn", "Modais, tabelas, banners e formulários")
        Component(lib, "Biblioteca de domínio", "TypeScript", "Datas, status, auditoria e geração de requests")
    }
    ContainerDb(db, "Supabase PostgreSQL", "Dados do produto")
    Container(functions, "Supabase Edge Functions", "Processamento server-side")
    Rel(routes, auth, "protege e contextualiza")
    Rel(routes, pages, "renderiza")
    Rel(auth, db, "carrega perfil")
    Rel(layout, auth, "lê papel e flags")
    Rel(pages, shared, "compõe")
    Rel(pages, lib, "usa regras")
    Rel(pages, db, "consulta/muta")
    Rel(pages, functions, "invoca")
```

## Relatórios

- `AdminRelatorios`: filtros, tabelas, agregações e CSV.
- `AdminRelatorioFeedback`: construção de dados, análise textual/IA e PDF.
- `ColaboradorRelatoriosClientes`: relatório filtrado de avaliações de clientes.

🟢 Componentes e responsabilidades são derivados dos arquivos analisados. O detalhamento interno das Edge Functions é 🔴 **LACUNA**.
