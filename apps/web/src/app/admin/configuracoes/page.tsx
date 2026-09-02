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
  client_feedback_motivations: "Motivações do formulário público (JSON)",
  whatsapp_message_template: "Template da mensagem de WhatsApp",
  calendar_keywords: "Palavras-chave de calendário (JSON)",
  gestor_can_access_reports: "Gestor acessa relatórios",
  gestor_can_access_agenda: "Gestor acessa agenda",
  colaborador_can_generate_own_report: "Colaborador gera o próprio relatório",
  client_eval_spontaneous_enabled: "Avaliação espontânea de cliente",
  client_eval_negative_keywords: "Palavras que sinalizam avaliação negativa (JSON)",
  client_eval_negative_rating_max: "Nota máxima considerada negativa",
};

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
      descricao="Valem para o escritório inteiro. Toggles nascem desligados."
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
                      item.persisted
                        ? `Alterado em ${formatarDataHora(item.updated_at)}`
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
