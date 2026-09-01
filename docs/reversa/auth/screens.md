# Telas — unit `auth`

> Gerado pelo Visor (Reversa) em 2026-08-28 a partir de screenshots do sistema em produção (`aesfeedbackinterno.vercel.app`).
> Escala de confiança: 🟢 CONFIRMADO (visível no screenshot) · 🟡 INFERIDO · 🔴 LACUNA

---

## Login

- **Rota:** `/login` · **Arquivo:** `src/pages/Login.tsx`
- **Screenshot:** `screenshots/login.png`
- **Estado capturado:** vazio (formulário sem preenchimento)
- **Contexto:** ponto de entrada do sistema; usuários não autenticados são redirecionados para cá 🟡

### Layout

Tela de tema escuro com fundo em gradiente roxo/vinho estrelado, distinta do restante do sistema (que usa tema claro). Card central translúcido (glassmorphism) contendo:

- Logotipo "A&S" em um badge arredondado azul-escuro 🟢
- Título "A&S Feedback Hub" + subtítulo "PLATAFORMA DE FEEDBACK INTERNO" 🟢

### Formulário

| Campo | Tipo | Placeholder | Obrigatório |
|---|---|---|---|
| E-mail | email | `seu@email.com` | 🟡 sim |
| Senha | password (com toggle 👁 de exibição) | `••••••••` | 🟡 sim |

- Botão primário **"Entrar"** em gradiente roxo/violeta, largura total 🟢
- Link **"Esqueci minha senha"** abaixo do botão 🟢 — leva ao fluxo de reset (`src/pages/ResetPassword.tsx`) 🟡

### Validações e feedback

- 🔴 LACUNA: mensagens de erro de credencial inválida não capturadas em screenshot.

---

## Meu Perfil

- **Rota:** `/perfil` · **Arquivo:** `src/pages/Perfil.tsx`
- **Screenshot:** `screenshots/meu-perfil.png`
- **Estado capturado:** preenchido (usuário admin logado)
- **Contexto:** acessível pelo item "Meu Perfil" no menu lateral de qualquer papel 🟢 (capturado no menu do admin)
- **Nota de mapeamento:** tela compartilhada entre todos os papéis; mapeada à unit `auth` por decisão do usuário (identidade da conta), 2026-08-28.

### Seção "Dados Pessoais"

| Campo | Tipo | Estado observado |
|---|---|---|
| Nome Completo | text | "Uanderson Cassiano Beiral" (editável) 🟢 |
| Cargo | text | vazio 🟢 |
| E-mail | text (somente leitura 🟡) | placeholder com o e-mail do usuário 🟢 |
| Papel | badge somente leitura | "Administrador" 🟢 |
| Departamento | text | placeholder "TI" 🟢 |

- 🔴 LACUNA: parte inferior da tela (possível troca de senha / botão salvar) não capturada.

### Observações transversais

- Cabeçalho global: busca (atalho ⌘K), alternador de tema claro/escuro (ícone lua), sino de notificações, nome + papel do usuário e avatar 🟢 — presente em todas as telas autenticadas.
- Menu lateral azul-escuro com logo da empresa e item "Sair" no rodapé 🟢.
