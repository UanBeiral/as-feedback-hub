"use client";

/**
 * Ciclos — criar, abrir, fechar, publicar, arquivar.
 *
 * Abrir é **um clique que dispara um comando** (`POST /cycles/{id}/open`), e o servidor
 * faz tudo numa transação: valida a concorrência por frequência, gera os requests dos
 * pares elegíveis e enfileira a notificação. No legado essa orquestração morava na
 * tela: o componente lia permissões, montava pares e inseria um a um — e uma falha no
 * meio deixava o ciclo aberto e vazio.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  Celula,
  Entrada,
  EstadoVazio,
  Linha,
  Selecao,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatarData, ROTULO_DO_CICLO } from "@/lib/formato";
import type { Ciclo, Formulario } from "@/lib/tipos";

const TOM_DO_CICLO = {
  draft: "neutro",
  open: "sucesso",
  closed: "alerta",
  published: "destaque",
  archived: "neutro",
} as const;

/** Transições que a máquina permite (BR-MIGRAR-004) — a mesma tabela do service. */
const ACOES: Record<string, { rota: string; rotulo: string }[]> = {
  draft: [
    { rota: "open", rotulo: "Abrir ciclo" },
    { rota: "archive", rotulo: "Arquivar" },
  ],
  open: [{ rota: "close", rotulo: "Fechar" }],
  closed: [{ rota: "publish", rotulo: "Publicar resultados" }],
  published: [{ rota: "archive", rotulo: "Arquivar" }],
  archived: [],
};

export default function AdminCiclos() {
  const [ciclos, setCiclos] = useState<Ciclo[] | null>(null);
  const [formularios, setFormularios] = useState<Formulario[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [novo, setNovo] = useState({
    name: "",
    form_id: "",
    start_date: "",
    end_date: "",
    frequency: "",
  });

  const carregar = useCallback(async () => {
    const [lista, forms] = await Promise.all([
      api<Ciclo[]>("/cycles"),
      api<Formulario[]>("/forms"),
    ]);
    setCiclos(lista);
    setFormularios(forms);
  }, []);

  useEffect(() => {
    carregar().catch(() => setCiclos([]));
  }, [carregar]);

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/cycles", {
        method: "POST",
        body: { ...novo, frequency: novo.frequency || null },
      });
      setNovo({ name: "", form_id: "", start_date: "", end_date: "", frequency: "" });
      setMensagem({ tom: "sucesso", texto: "Ciclo criado como rascunho." });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível criar o ciclo.",
      });
    }
  }

  async function executar(ciclo: Ciclo, rota: string) {
    setMensagem(null);
    try {
      const resposta = await api<{ requests_criados?: number }>(`/cycles/${ciclo.id}/${rota}`, {
        method: "POST",
      });
      setMensagem({
        tom: "sucesso",
        texto:
          rota === "open"
            ? `Ciclo aberto. ${resposta.requests_criados ?? 0} pedidos de feedback gerados.`
            : "Pronto.",
      });
      await carregar();
    } catch (falha) {
      // O 409 de concorrência por frequência (BR-MIGRAR-011) chega com a mensagem do
      // servidor — repetir aqui evita inventar um texto diferente do que a regra diz.
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Operação recusada.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Ciclos de feedback"
      descricao="Abrir um ciclo gera os pedidos a partir das permissões ativas, em uma única operação."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Novo ciclo">
          <form onSubmit={criar} className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Nome" obrigatorio>
              <Entrada
                required
                value={novo.name}
                onChange={(e) => setNovo({ ...novo, name: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Formulário" obrigatorio>
              <Selecao
                required
                value={novo.form_id}
                onChange={(e) => setNovo({ ...novo, form_id: e.target.value })}
              >
                <option value="">Selecione</option>
                {formularios.map((formulario) => (
                  <option key={formulario.id} value={formulario.id}>
                    {formulario.name}
                  </option>
                ))}
              </Selecao>
            </Campo>
            <Campo rotulo="Início" obrigatorio>
              <Entrada
                type="date"
                required
                value={novo.start_date}
                onChange={(e) => setNovo({ ...novo, start_date: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Fim" obrigatorio>
              <Entrada
                type="date"
                required
                value={novo.end_date}
                onChange={(e) => setNovo({ ...novo, end_date: e.target.value })}
              />
            </Campo>
            <Campo
              rotulo="Frequência"
              dica="Só um ciclo aberto por frequência ao mesmo tempo. Em branco = avulso."
            >
              <Selecao
                value={novo.frequency}
                onChange={(e) => setNovo({ ...novo, frequency: e.target.value })}
              >
                <option value="">Avulso</option>
                <option value="mensal">Mensal</option>
                <option value="trimestral">Trimestral</option>
                <option value="semestral">Semestral</option>
                <option value="anual">Anual</option>
              </Selecao>
            </Campo>
            <div className="flex items-end">
              <Botao tipo="submit">Criar rascunho</Botao>
            </div>
          </form>
        </Cartao>

        <Cartao titulo="Ciclos">
          {ciclos === null ? (
            <Carregando />
          ) : ciclos.length === 0 ? (
            <EstadoVazio titulo="Nenhum ciclo ainda" />
          ) : (
            <Tabela colunas={["Ciclo", "Período", "Frequência", "Status", "Ações"]}>
              {ciclos.map((ciclo) => (
                <Linha key={ciclo.id}>
                  <Celula className="font-medium">{ciclo.name}</Celula>
                  <Celula>
                    {formatarData(ciclo.start_date)} – {formatarData(ciclo.end_date)}
                    {ciclo.evaluated_end && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        estendido até {formatarData(ciclo.evaluated_end)}
                      </span>
                    )}
                  </Celula>
                  <Celula>{ciclo.frequency ?? "avulso"}</Celula>
                  <Celula>
                    <Selo tom={TOM_DO_CICLO[ciclo.status as keyof typeof TOM_DO_CICLO]}>
                      {ROTULO_DO_CICLO[ciclo.status] ?? ciclo.status}
                    </Selo>
                  </Celula>
                  <Celula>
                    <span className="flex flex-wrap gap-2">
                      {(ACOES[ciclo.status] ?? []).map((acao) => (
                        <Botao
                          key={acao.rota}
                          variante="secundario"
                          onClick={() => void executar(ciclo, acao.rota)}
                        >
                          {acao.rotulo}
                        </Botao>
                      ))}
                      {ciclo.status === "open" && (
                        <Botao
                          variante="fantasma"
                          onClick={() => void executar(ciclo, "regenerate-requests")}
                        >
                          Regerar pedidos
                        </Botao>
                      )}
                    </span>
                  </Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
