---
schemaVersion: 1
generatedAt: 2026-08-28T01:45:00Z
reversa:
  version: "1.2.60"
kind: screen_modernization_decision
producedBy: screen-translator
decidedBy: Uan
decidedAt: 2026-08-28T02:00:00Z
mode: hybrid
sourcePlatform: react-spa
targetPlatform: web-nextjs
hash: "sha256:483f948c36342bfc96650d7f93acd5b639386cc8c47e12ea00060b849cad66ce"
---

# Decisão de Modernização de Telas

> Decisão consciente sobre como traduzir as telas do sistema legado: paridade observável byte-a-byte, redesign idiomático para a plataforma alvo, ou combinação tela-a-tela.
> Este artefato é leitura obrigatória do próprio Screen Translator (para gerar `target_screens.md`), do Inspector (para construir parity tests adequados ao modo) e do agente de codificação.

## Contexto

- **Plataforma origem detectada**: `react-spa` (React 18 + Vite + Tailwind/shadcn) — 🟢 CONFIRMADO (`inventory.md`, `dependencies.md`)
- **Plataforma alvo**: `web-nextjs` (Next.js App Router, feature-sliced, tokens do design system — `target_architecture.md`)
- **Telas inventariadas**: 45 (`_reversa_sdd/screens/inventory.json`; divergência com `ui/inventory.md`: 0%)
- **Origem do inventário**: `_reversa_sdd/screens/inventory.json` + `_reversa_sdd/ui/inventory.md` (83 screenshots do Visor)
- **Adapter aplicado**: `web-spa → web-spa` (mesma família de plataforma; specs `component-tree`)
- **Fora do escopo do primeiro corte**: SCR-0040 (Callback Google OAuth) e SCR-0045 (Agenda conectada) — adiadas com a integração Google Calendar (AMB-007)

Particularidade favorável deste par: a origem já é uma UI web moderna (shadcn/Radix + Tailwind) com design system extraído (32 tokens semânticos). "Traduzir" aqui não é atravessar gerações de tecnologia — é recriar as mesmas telas no Next.js **usando os tokens e eliminando as 657 cores hardcoded** (BR-DESCARTAR-007). Há oráculo visual para 35 telas (screenshots); 8 telas do primeiro corte não têm captura.

## Modos avaliados

### Modo: literal
- **Definição**: paridade pixel-equivalente com o legado — mesmas telas, mesmos textos, mesma hierarquia, agora via tokens.
- **Trade-offs**:
  - Custo de implementação: médio
  - Fidelidade visual: alta
  - Viabilidade de parity tests construtivos: sim (35 telas com screenshot como golden)
  - Aceitação esperada do usuário final: alta (o cliente homologa o que já conhece — zero re-treinamento)
  - Débito técnico futuro: baixo (a dívida visual do legado não migra: tokens em vez de hex)
- **Recomendado**: não como modo único
- **Justificativa**: 8 telas do primeiro corte não têm screenshot; a regra RF-13 bloqueia literal em plataforma gráfica sem oráculo visual — exigiria capturas extras antes de começar.

### Modo: modernizado
- **Definição**: redesign idiomático Next.js preservando informação e fluxo, com os 4 estados (idle, loading, error, success) declarados por tela.
- **Trade-offs**:
  - Custo de implementação: médio-alto
  - Fidelidade visual: média (layout pode divergir do que o cliente conhece)
  - Viabilidade de parity tests construtivos: parcial (contrato semântico, sem comparação visual)
  - Aceitação esperada do usuário final: média (re-aprendizado justamente na homologação — atrito contra a métrica de sucesso do brief)
  - Débito técnico futuro: baixo
- **Recomendado**: não como modo único
- **Justificativa**: a UI legada já é moderna; redesenhar tudo joga fora o oráculo visual de 35 telas e adiciona risco à homologação sem ganho proporcional.

### Modo: híbrido
- **Definição**: literal para as telas com screenshot (oráculo visual disponível), modernizado para as telas sem captura (especificadas a partir das specs SDD + design system, com os 4 estados declarados).
- **Trade-offs**:
  - Custo de implementação: médio
  - Fidelidade visual mista: alta nas 35 telas que o cliente usa e conhece; idiomática nas 8 sem oráculo
  - Viabilidade de parity tests: visual/golden para o subset literal; contrato semântico para o subset modernizado (declarado por tela em `parity_specs.md`)
  - Custo de manutenção da separação: baixo (a fronteira é objetiva: existe screenshot ou não)
- **Recomendado**: **sim**
- **Justificativa**: maximiza fidelidade onde há oráculo e o cliente tem memória visual; destrava as telas sem captura sem bloquear o pipeline esperando novas capturas; fronteira objetiva e auditável.

## Decisão

- **Modo escolhido**: híbrido
- **Justificativa do humano**: recomendação do agente aceita (resposta "3"); fronteira objetiva por existência de screenshot.
- **Alternativas descartadas**: literal (bloqueado por 8 telas sem captura — RF-13); modernizado (descartaria o oráculo visual de 35 telas e criaria atrito na homologação).
- **Decidido em**: 2026-08-28T02:00:00Z
- **Decidido por**: Uan

### Em modo híbrido, listas explícitas (obrigatórias)

**Telas em modo literal** (35 — todas com screenshot do Visor):
- SCR-0001 Login, SCR-0002 Meu Perfil, SCR-0003 Painel Administrativo, SCR-0004 Anotações Realizadas, SCR-0005 Minha Equipe (Admin), SCR-0006 Histórico da Equipe (Admin), SCR-0007 Usuários, SCR-0008 Departamentos, SCR-0009 Ciclos de Feedback, SCR-0010 Permissões de Feedback, SCR-0011 Diagnóstico de Permissões, SCR-0012 Auditoria, SCR-0013 Fale Conosco, SCR-0014 Agenda (estado não conectado), SCR-0015 Central de Atualizações, SCR-0016 Relatórios — Dados e Filtros, SCR-0017 Emitir Relatório, SCR-0018 Formulários, SCR-0019 Minhas Anotações, SCR-0020 Meus Feedbacks, SCR-0021 Meu Histórico, SCR-0022 Caderno do Ciclo, SCR-0023 Modal Dar Feedback Livre, SCR-0024 Configurações, SCR-0025 Início (Coordenador), SCR-0026 Minha Equipe (Coordenador), SCR-0027 Feedbacks Pendentes (Coordenador), SCR-0028 Histórico da Equipe (Coordenador), SCR-0029 Início (Gestor), SCR-0030 Minha Equipe (Gestor), SCR-0031 Feedbacks Pendentes (Gestor), SCR-0032 Histórico da Equipe (Gestor), SCR-0033 Início (Colaborador), SCR-0034 Avaliações de Clientes, SCR-0035 Avaliação Pública (16 etapas)

**Telas em modo modernizado** (8 — sem captura; especificadas de specs + design system):
- SCR-0036 Formulário de Resposta 360°, SCR-0037 Histórico por Pessoa, SCR-0038 Reset de Senha, SCR-0039 Novidades, SCR-0041 Index/NotFound, SCR-0042 Colaborador (Dashboard Clientes / Histórico Equipe / Relatórios Clientes), SCR-0043 Editor de Perguntas do Formulário, SCR-0044 Fluxo Público — Pergunta 6

> SCR-0040 e SCR-0045 fora do primeiro corte (AMB-007).

## Implicações pendentes para a Fase 2

| Etapa | Implicação | Como honrar |
|---|---|---|
| Geração de `target_screens.md` | Specs `component-tree` para ambos os subsets | subset literal referencia screenshot como oráculo; subset modernizado declara os 4 estados por tela |
| Captura de golden files | Screenshots do Visor são o golden do subset literal | manifest aponta para `_reversa_sdd/<unit>/screenshots/`; sem captura automatizada em v1 |
| Tokens do design-system | 657 cores hardcoded não migram | todo valor visual passa por token; cores sem token viram `tokens-derived.md` + deviation |
| Conteúdo textual | Preservar literal salvo aprovação explícita de revisão linguística | diff de strings zero contra as capturas/código |

## Implicações para o Inspector

- **Estratégia de paridade**:
  - Subset literal → paridade visual validada contra os screenshots do Visor + contrato semântico.
  - Subset modernizado → contrato semântico (eventos, transições, conteúdo textual, estados), sem comparação visual.
  - Declaração por tela em `parity_specs.md`.
- **Deviations conhecidas a propagar**: ver `screen_deviation_log.md` (Fase 2).

## Notas

- A troca de mecanismo por baixo das telas (Supabase → API OpenAPI) não é deviation visual: o contrato de tela permanece o mesmo; onde a latência assíncrona mudar percepção (relatórios pesados → job com link), a divergência será registrada como deviation `tipo=plataforma`.
- Os 4 papéis compartilham o shell autenticado (sidebar + header) — especificado uma vez como layout, referenciado pelas telas.
