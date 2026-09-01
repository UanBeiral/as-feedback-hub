# Fluxograma — Relatórios

```mermaid
flowchart TD
    A[Usuário abre relatório] --> B{Tipo de relatório}
    B -->|Operacional| C[Carregar perfis, ciclos e departamentos]
    C --> D{Aba}
    D -->|Clientes| E[Consultar client_feedbacks submetidos]
    D -->|Livres| F[Consultar free_feedbacks]
    D -->|360| G[Consultar feedback_requests com joins]
    D -->|Engajamento| H[Consultar requests por status]
    E --> I[Aplicar filtros, ordenação e colunas]
    F --> I
    G --> J[Calcular status visual, atraso e taxa]
    J --> I
    H --> K[Restringir a ciclos fechados e agregar por pessoa]
    K --> I
    I --> L[Preview limitado ou exportação CSV]
    B -->|Executivo| M[Validar escopo, pessoa e ciclo]
    M --> N[Carregar requests submitted e respostas]
    N --> O[Calcular notas, cobertura e ciclo anterior]
    O --> P{Escopo geral?}
    P -->|Não| Q[Recuperar ou gerar análise individual]
    P -->|Sim| R[Recuperar ou gerar análise da equipe]
    Q --> S[Renderizar HTML em páginas A4]
    R --> S
    S --> T[html2canvas + jsPDF]
    T --> U{Destino}
    U -->|Download| V[Baixar PDF]
    U -->|Email| W[Invocar send-report-email]
```

## Regras críticas

- A taxa 360° divide requests `submitted` pelo total filtrado.
- O engajamento percorre somente ciclos com status `closed`.
- A geração executiva ignora pessoas sem feedback submetido.
- Análises de IA podem ser lidas do cache antes de invocar as Edge Functions.