"use client";

/**
 * Configurações do escritório (BR-MIGRAR-027).
 *
 * O salvamento manda de volta o `updated_at` que a tela leu. Se outra pessoa tiver
 * salvado a mesma chave nesse meio-tempo, o servidor recusa com 409 em vez de
 * sobrescrever — e a tela avisa para recarregar. No legado o último a clicar vencia, e
 * ninguém ficava sabendo que a mudança do colega tinha sumido.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Entrada,
  Selecao,
} from "@/components/ui";
import { ApiError, apiVoid, api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { Configuracao } from "@/lib/tipos";

const ROTULOS: Record<string, string> = {
  company_name: "Nome do escritório",
  logo_url: "URL do logo",
  client_feedback_motivations: "Motivações da avaliação do cliente",
  whatsapp_message_template: "Template da mensagem de WhatsApp",
  calendar_keywords: "Palavras-chave de calendário",
  gestor_can_access_reports: "Gestor acessa relatórios",
  gestor_can_access_agenda: "Gestor acessa agenda",
  colaborador_can_generate_own_report: "Colaborador gera o próprio relatório",
  client_eval_spontaneous_enabled: "Avaliação espontânea de cliente",
  client_eval_negative_keywords: "Palavras que sinalizam avaliação negativa",
  client_eval_negative_rating_max: "Nota máxima considerada negativa",
};

/**
 * Chaves que guardam JSON e que **não** devem ser editadas como JSON.
 *
 * Pedir `{"praise":true,...}` a um administrador de escritório é convite a erro de
 * digitação que desliga um recurso em silêncio: uma vírgula a mais e a motivação some
 * do formulário público sem ninguém entender por quê. As duas formas abaixo montam o
 * JSON a partir de controles que não têm como sair errados.
 */
const MOTIVACOES: { chave: string; rotulo: string }[] = [
  { chave: "praise", rotulo: "Quero elogiar" },
  { chave: "evaluate", rotulo: "Quero avaliar o atendimento" },
  { chave: "problem", rotulo: "Tive um problema" },
  { chave: "other", rotulo: "Outro motivo" },
];

/** Guardam uma lista JSON de strings, editada aqui como texto separado por vírgula. */
const LISTAS = new Set(["calendar_keywords", "client_eval_negative_keywords"]);

/** Lê a lista com tolerância: config quebrada não pode travar a tela de config. */
function listaDe(valor: string | undefined): string[] {
  try {
    const lido: unknown = JSON.parse(valor || "[]");
    return Array.isArray(lido) ? lido.map(String) : [];
  } catch {
    return [];
  }
}

function motivacoesDe(valor: string | undefined): Record<string, boolean> {
  try {
    const lido: unknown = JSON.parse(valor || "{}");
    return typeof lido === "object" && lido !== null ? (lido as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

const TOGGLES = new Set([
  "gestor_can_access_reports",
  "gestor_can_access_agenda",
  "colaborador_can_generate_own_report",
  "client_eval_spontaneous_enabled",
]);

export default function AdminConfiguracoes() {
  const [itens, setItens] = useState<Configuracao[] | null>(null);
  const [rascunho, setRascunho] = useState<Record<string, string>>({});
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    const lista = await api<Configuracao[]>("/settings");
    setItens(lista);
    setRascunho(Object.fromEntries(lista.map((item) => [item.key, item.value ?? ""])));
  }, []);

  useEffect(() => {
    carregar().catch(() => setItens([]));
  }, [carregar]);

  async function salvar(item: Configuracao) {
    setMensagem(null);
    try {
      await apiVoid(`/settings/${item.key}`, {
        method: "PUT",
        body: {
          value: rascunho[item.key] === "" ? null : rascunho[item.key],
          // Carimbo lido antes de editar: é o que permite ao servidor detectar a
          // edição concorrente. Ausente significa "a chave não existia".
          expected_updated_at: item.persisted ? item.updated_at : null,
        },
      });
      setMensagem({ tom: "sucesso", texto: `"${ROTULOS[item.key] ?? item.key}" salvo.` });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError && falha.status === 409
            ? "Outra pessoa alterou esta configuração enquanto você editava. Recarregue e revise."
            : "Não foi possível salvar.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Configurações"
      descricao="Gerencie as configurações visuais e informações da empresa exibidas em todo o sistema."
    >
      <div className="space-y-4">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        {itens === null ? (
          <Carregando />
        ) : (
          itens.map((item) => (
            <Cartao key={item.key}>
              <div className="flex flex-wrap items-end gap-4">
                <div className="min-w-64 flex-1">
                  <Campo
                    rotulo={ROTULOS[item.key] ?? item.key}
                    dica={
                      LISTAS.has(item.key)
                        ? "Separe por vírgula."
                        : item.persisted
                          ? `Última atualização: ${formatarDataHora(item.updated_at)}`
                          : "Ainda no valor padrão"
                    }
                  >
                    {TOGGLES.has(item.key) ? (
                      <Selecao
                        value={rascunho[item.key] ?? "false"}
                        onChange={(e) => setRascunho({ ...rascunho, [item.key]: e.target.value })}
                      >
                        <option value="false">Desligado</option>
                        <option value="true">Ligado</option>
                      </Selecao>
                    ) : item.key === "client_feedback_motivations" ? (
                      <span className="flex flex-wrap gap-4 pt-1">
                        {MOTIVACOES.map((motivacao) => {
                          const atual = motivacoesDe(rascunho[item.key]);
                          // Chave ausente vale ligada: é o default do catálogo, e uma
                          // config incompleta não pode esconder etapa do cliente.
                          const ligada = atual[motivacao.chave] !== false;
                          return (
                            <label
                              key={motivacao.chave}
                              className="flex items-center gap-2 text-sm text-foreground"
                            >
                              <input
                                type="checkbox"
                                checked={ligada}
                                onChange={(e) =>
                                  setRascunho({
                                    ...rascunho,
                                    [item.key]: JSON.stringify({
                                      ...Object.fromEntries(
                                        MOTIVACOES.map((m) => [m.chave, atual[m.chave] !== false]),
                                      ),
                                      [motivacao.chave]: e.target.checked,
                                    }),
                                  })
                                }
                              />
                              {motivacao.rotulo}
                            </label>
                          );
                        })}
                      </span>
                    ) : LISTAS.has(item.key) ? (
                      <Entrada
                        value={listaDe(rascunho[item.key]).join(", ")}
                        placeholder="péssimo, demora, sem retorno"
                        onChange={(e) =>
                          setRascunho({
                            ...rascunho,
                            [item.key]: JSON.stringify(
                              e.target.value
                                .split(",")
                                .map((palavra) => palavra.trim())
                                .filter(Boolean),
                            ),
                          })
                        }
                      />
                    ) : (
                      <Entrada
                        value={rascunho[item.key] ?? ""}
                        onChange={(e) => setRascunho({ ...rascunho, [item.key]: e.target.value })}
                      />
                    )}
                  </Campo>
                </div>
                <Botao variante="secundario" onClick={() => void salvar(item)}>
                  Salvar
                </Botao>
              </div>
            </Cartao>
          ))
        )}
      </div>
    </PaginaAutenticada>
  );
}
