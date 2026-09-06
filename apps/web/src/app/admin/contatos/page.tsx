"use client";

/**
 * Triagem do Fale Conosco.
 *
 * A máquina é `novo → em_andamento → resolvido`, e só ela: reabrir um chamado resolvido
 * não existia no legado, então não foi inventado. Quem precisar, abre outro — e a API
 * recusa a transição com 409, não a tela.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  BarraDeFiltros,
  Botao,
  BotaoDeExportar,
  Carregando,
  Cartao,
  ContadorDeResultados,
  EstadoVazio,
  FiltroSelecao,
  Selo,
} from "@/components/ui";
import { contemTexto, exportarCsv } from "@/lib/exportar";
import { ApiError, api } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import type { MensagemDeContato } from "@/lib/tipos";

/** O catálogo, igual ao do servidor. `type` deixou de ser texto livre. */
const ROTULO_DO_TIPO: Record<string, string> = {
  sugestao: "Sugestão",
  critica: "Crítica",
};

const TOM = {
  novo: "alerta",
  em_andamento: "destaque",
  resolvido: "sucesso",
} as const;

const ROTULO = {
  novo: "Novo",
  em_andamento: "Em andamento",
  resolvido: "Resolvido",
} as const;

/** As transições que a API aceita — a tela mostra só o que vai dar certo. */
const PROXIMOS: Record<string, { status: string; rotulo: string }[]> = {
  novo: [
    { status: "em_andamento", rotulo: "Assumir" },
    { status: "resolvido", rotulo: "Resolver" },
  ],
  em_andamento: [{ status: "resolvido", rotulo: "Resolver" }],
  resolvido: [],
};

export default function AdminContatos() {
  const [mensagens, setMensagens] = useState<MensagemDeContato[] | null>(null);
  const [filtro, setFiltro] = useState<string>("");
  const [busca, setBusca] = useState("");
  const [tipo, setTipo] = useState("");
  const [aviso, setAviso] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async (status: string) => {
    setMensagens(
      await api<MensagemDeContato[]>("/contact-messages", {
        query: status ? { status } : undefined,
      }),
    );
  }, []);

  useEffect(() => {
    carregar(filtro).catch(() => setMensagens([]));
  }, [carregar, filtro]);

  async function mudar(mensagem: MensagemDeContato, status: string) {
    setAviso(null);
    try {
      await api(`/contact-messages/${mensagem.id}`, { method: "PATCH", body: { status } });
      await carregar(filtro);
    } catch (falha) {
      setAviso({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível atualizar.",
      });
    }
  }

  const visiveis = (mensagens ?? []).filter(
    (m) =>
      (!tipo || m.type === tipo) &&
      [m.contact_name, m.email, m.message, m.company].some((campo) => contemTexto(campo, busca)),
  );

  // O catálogo inteiro, e não só o que já apareceu na caixa: um filtro montado a partir
  // das linhas existentes some quando a caixa esvazia e volta quando alguém escreve — e
  // quem procura "Crítica" e não acha a opção conclui que o filtro não existe.
  const tiposPresentes = Object.keys(ROTULO_DO_TIPO);

  function exportar() {
    exportarCsv(
      "fale-conosco",
      ["Data", "Contato", "E-mail", "Telefone", "Empresa", "Tipo", "Status", "Mensagem"],
      visiveis.map((m) => [
        formatarDataHora(m.created_at),
        m.contact_name,
        m.email,
        m.phone ?? "",
        m.company ?? "",
        ROTULO_DO_TIPO[m.type] ?? m.type,
        ROTULO[m.status as keyof typeof ROTULO] ?? m.status,
        m.message,
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Fale conosco — triagem"
      descricao="Sugestões, problemas e dúvidas enviados pelo time."
      acao={
        <span className="flex gap-2">
          {[
            ["", "Todos"],
            ["novo", "Novos"],
            ["em_andamento", "Em andamento"],
            ["resolvido", "Resolvidos"],
          ].map(([valor, rotulo]) => (
            <button
              key={valor || "todos"}
              type="button"
              onClick={() => setFiltro(valor)}
              className={
                "rounded-md px-3 py-1.5 text-sm " +
                (filtro === valor
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-muted")
              }
            >
              {rotulo}
            </button>
          ))}
        </span>
      }
    >
      <div className="space-y-4">
        {aviso && <Aviso tom={aviso.tom}>{aviso.texto}</Aviso>}

        <Cartao>
          {mensagens === null ? (
            <Carregando />
          ) : mensagens.length === 0 ? (
            <EstadoVazio titulo="Nenhuma mensagem" />
          ) : (
            <>
            <BarraDeFiltros
              busca={busca}
              aoBuscar={setBusca}
              placeholder="Buscar por pessoa, e-mail ou texto…"
              acoes={
                <>
                  <ContadorDeResultados mostrando={visiveis.length} total={mensagens.length} />
                  <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                </>
              }
            >
              <FiltroSelecao
                rotuloDeTodos="Todos os tipos"
                valor={tipo}
                aoMudar={setTipo}
                opcoes={tiposPresentes.map((t) => ({ valor: t, rotulo: ROTULO_DO_TIPO[t] ?? t }))}
              />
            </BarraDeFiltros>

            {visiveis.length === 0 ? (
              <EstadoVazio titulo="Nenhuma mensagem com esses filtros" />
            ) : (
            <ul className="divide-y divide-border">
              {visiveis.map((mensagem) => (
                <li key={mensagem.id} className="py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-foreground">
                        {mensagem.contact_name}
                        <Selo tom={TOM[mensagem.status as keyof typeof TOM] ?? "neutro"}>
                          {ROTULO[mensagem.status as keyof typeof ROTULO] ?? mensagem.status}
                        </Selo>
                        <span className="text-xs font-normal text-muted-foreground">
                          {ROTULO_DO_TIPO[mensagem.type] ?? mensagem.type}
                        </span>
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
                        {mensagem.message}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {mensagem.email}
                        {mensagem.phone ? ` · ${mensagem.phone}` : ""} ·{" "}
                        {formatarDataHora(mensagem.created_at)}
                      </p>
                    </div>

                    <span className="flex shrink-0 gap-2">
                      {(PROXIMOS[mensagem.status] ?? []).map((acao) => (
                        <Botao
                          key={acao.status}
                          variante="secundario"
                          onClick={() => void mudar(mensagem, acao.status)}
                        >
                          {acao.rotulo}
                        </Botao>
                      ))}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
            )}
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
