# language: pt
# spec-id: PAR-SCR-02
# rastreabilidade: target_screens.md § Subset MODERNIZADO; screen_modernization_decision.md (híbrido, DEV-004 aprovada)
# nota: contrato semântico de tela — sem comparação visual byte-a-byte

@paridade-visual
Funcionalidade: Contrato de tela do subset modernizado (8 telas)

  Esquema do Cenário: Tela modernizada honra o contrato declarado
    Dado a tela "<tela>" implementada conforme sua seção em target_screens.md
    Quando a tela é exercitada em cada um dos estados declarados (idle, loading, error, success)
    Então a hierarquia de componentes e os eventos declarados estão presentes
    E o conteúdo textual existente no código legado aparece sem alteração
    E cada estado tem representação visual própria com tokens do design system

    Exemplos:
      | tela                                                  |
      | Formulário de Resposta 360° (SCR-0036)                |
      | Histórico por Pessoa (SCR-0037)                       |
      | Reset de Senha (SCR-0038)                             |
      | Novidades (SCR-0039)                                  |
      | Index / NotFound (SCR-0041)                           |
      | Colaborador — Dashboard/Histórico/Relatórios (SCR-0042) |
      | Editor de Perguntas do Formulário (SCR-0043)          |
      | Fluxo Público — Pergunta 6 (SCR-0044)                 |

  @critico
  Cenário: Formulário 360° preserva a validação de submissão
    Dado o Formulário de Resposta 360° com perguntas obrigatórias não respondidas
    Quando o envio é tentado
    Então o estado "error" é exibido e nada é persistido
