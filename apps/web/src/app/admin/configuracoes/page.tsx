"use client";

/**
 * Configurações do escritório (BR-MIGRAR-027).
 *
 * O salvamento manda de volta o `updated_at` que a tela leu. Se outra pessoa tiver
 * salvado a mesma chave nesse meio-tempo, o servidor recusa com 409 em vez de
 * sobrescrever — e a tela avisa para recarregar. No legado o último a clicar vencia, e
 * ninguém ficava sabendo que a mudança do colega tinha sumido.
 *
 * As chaves aparecem **agrupadas por assunto**, como no legado. Uma lista corrida de
 * onze cartões iguais obriga a ler todos os rótulos para achar o que se procura, e a
 * relação entre "palavras negativas" e "nota máxima negativa" — que só fazem sentido
 * juntas — some.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import { Aviso, Botao, Campo, Carregando, Cartao, Entrada, Selecao } from "@/components/ui";
import { ApiError, apiVoid, api, apiUpload } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { Configuracao } from "@/lib/tipos";

const ROTULOS: Record<string, string> = {
  // "Razão Social" é o rótulo interno do legado: no cabeçalho aparece o nome fantasia,
  // aqui se edita o que sai em documento.
  company_name: "Razão Social",
  logo_url: "Logo do escritório",
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

/** O ⓘ do legado: o que a chave faz, para quem não a configurou. */
const AJUDA: Record<string, string> = {
  company_name: "Sai nos e-mails e no cabeçalho do sistema.",
  logo_url: "PNG ou SVG, até 2 MB. Aparece no cabeçalho.",
  client_feedback_motivations: "Quais motivos o cliente pode escolher na primeira etapa.",
  whatsapp_message_template: "Texto sugerido ao enviar o link da avaliação.",
  calendar_keywords: "Termos que identificam compromissos de cliente na agenda.",
  gestor_can_access_reports: "Sem isto, gestor só vê relatório se tiver a capacidade no perfil.",
  gestor_can_access_agenda: "Libera a agenda para quem tem equipe.",
  colaborador_can_generate_own_report: "Deixa cada pessoa exportar o próprio resultado.",
  client_eval_spontaneous_enabled: "Permite avaliação sem convite, pelo link público.",
  client_eval_negative_keywords: "Uma delas no texto marca a avaliação para atenção.",
  client_eval_negative_rating_max: "Nota igual ou menor marca a avaliação para atenção.",
};

/** Os grupos do legado. A ordem dentro de cada um é a que a tela mostra. */
const GRUPOS: { titulo: string; icone: string; chaves: string[] }[] = [
  { titulo: "Identidade", icone: "🏢", chaves: ["company_name", "logo_url"] },
  {
    titulo: "Avaliação de clientes",
    icone: "⭐",
    chaves: [
      "client_eval_spontaneous_enabled",
      "client_feedback_motivations",
      "whatsapp_message_template",
      "client_eval_negative_keywords",
      "client_eval_negative_rating_max",
    ],
  },
  {
    titulo: "Acessos por papel",
    icone: "🔑",
    chaves: [
      "gestor_can_access_reports",
      "gestor_can_access_agenda",
      "colaborador_can_generate_own_report",
    ],
  },
  { titulo: "Agenda", icone: "📅", chaves: ["calendar_keywords"] },
];

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

const TOGGLES = new Set([
  "gestor_can_access_reports",
  "gestor_can_access_agenda",
  "colaborador_can_generate_own_report",
  "client_eval_spontaneous_enabled",
]);

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

  async function enviarLogo(arquivo: File) {
    setMensagem(null);
    try {
      const dados = new FormData();
      dados.append("arquivo", arquivo);
      await apiUpload("/settings/logo", dados);
      setMensagem({ tom: "sucesso", texto: "Logo atualizado." });
      await carregar();
    } catch (falha) {
      // O servidor recusa tipo e tamanho — repetir a mensagem dele evita inventar um
      // limite diferente do que ele aplica.
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível enviar o logo.",
      });
    }
  }

  const porChave = new Map((itens ?? []).map((item) => [item.key, item]));
  // Chave que o servidor devolva e que nenhum grupo conheça continua aparecendo: o
  // catálogo cresce no servidor, e sumir da tela é pior do que aparecer sem grupo.
  const agrupadas = new Set(GRUPOS.flatMap((grupo) => grupo.chaves));
  const grupos = [
    ...GRUPOS,
    {
      titulo: "Outras",
      icone: "⚙️",
      chaves: (itens ?? []).map((i) => i.key).filter((chave) => !agrupadas.has(chave)),
    },
  ].filter((grupo) => grupo.chaves.some((chave) => porChave.has(chave)));

  return (
    <PaginaAutenticada
      titulo="Configurações"
      descricao="Gerencie as configurações visuais e informações da empresa exibidas em todo o sistema."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        {itens === null ? (
          <Carregando />
        ) : (
          grupos.map((grupo) => (
            <Cartao
              key={grupo.titulo}
              titulo={`${grupo.icone}  ${grupo.titulo}`}
            >
              <div className="divide-y divide-border">
                {grupo.chaves
                  .map((chave) => porChave.get(chave))
                  .filter((item): item is Configuracao => item !== undefined)
                  .map((item) => (
                    <div key={item.key} className="flex flex-wrap items-end gap-4 py-4 first:pt-0">
                      <div className="min-w-64 flex-1">
                        <Campo
                          rotulo={ROTULOS[item.key] ?? item.key}
                          ajuda={AJUDA[item.key]}
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
                              onChange={(e) =>
                                setRascunho({ ...rascunho, [item.key]: e.target.value })
                              }
                            >
                              <option value="false">Desligado</option>
                              <option value="true">Ligado</option>
                            </Selecao>
                          ) : item.key === "logo_url" ? (
                            <Logo
                              url={rascunho[item.key] ?? ""}
                              aoEscolher={(arquivo) => void enviarLogo(arquivo)}
                              aoDigitar={(valor) =>
                                setRascunho({ ...rascunho, [item.key]: valor })
                              }
                            />
                          ) : item.key === "client_feedback_motivations" ? (
                            <span className="flex flex-wrap gap-4 pt-1">
                              {MOTIVACOES.map((motivacao) => {
                                const atual = motivacoesDe(rascunho[item.key]);
                                // Chave ausente vale ligada: é o default do catálogo, e
                                // uma config incompleta não pode esconder etapa do
                                // cliente.
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
                                              MOTIVACOES.map((m) => [
                                                m.chave,
                                                atual[m.chave] !== false,
                                              ]),
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
                              onChange={(e) =>
                                setRascunho({ ...rascunho, [item.key]: e.target.value })
                              }
                            />
                          )}
                        </Campo>
                      </div>
                      <Botao variante="secundario" onClick={() => void salvar(item)}>
                        Salvar
                      </Botao>
                    </div>
                  ))}
              </div>
            </Cartao>
          ))
        )}
      </div>
    </PaginaAutenticada>
  );
}

/**
 * O logo: sobe arquivo **ou** aponta uma URL.
 *
 * As duas formas porque o campo é uma URL no banco de qualquer jeito — quem já hospeda a
 * marca em algum lugar cola o endereço, e quem só tem o arquivo no computador manda o
 * arquivo. Pedir só a URL, como estava, era não ter o recurso para o segundo caso.
 *
 * O upload salva sozinho: ele grava o arquivo e a chave na mesma chamada, e um botão
 * "Salvar" depois disso sugeriria que dá para desistir do que já foi para o disco.
 */
function Logo({
  url,
  aoEscolher,
  aoDigitar,
}: {
  url: string;
  aoEscolher: (arquivo: File) => void;
  aoDigitar: (valor: string) => void;
}) {
  return (
    <div className="space-y-2">
      {url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt="Logo do escritório"
          className="h-12 w-auto rounded border border-border bg-card p-1"
        />
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Entrada
          value={url}
          placeholder="https://… ou envie um arquivo"
          onChange={(e) => aoDigitar(e.target.value)}
        />
        <label
          className={
            "inline-flex h-9 shrink-0 cursor-pointer items-center rounded-md border " +
            "border-input bg-card px-3 text-sm text-foreground hover:bg-muted"
          }
        >
          Enviar arquivo
          <input
            type="file"
            accept="image/png,image/svg+xml"
            className="hidden"
            onChange={(e) => {
              const arquivo = e.target.files?.[0];
              if (arquivo) aoEscolher(arquivo);
              // Zera para que escolher o mesmo arquivo de novo dispare o evento — sem
              // isto, reenviar depois de um erro não faz nada.
              e.target.value = "";
            }}
          />
        </label>
      </div>
    </div>
  );
}
