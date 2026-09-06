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
  BarraDeFiltros,
  Botao,
  BotaoDeExportar,
  Campo,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
  Entrada,
  EstadoVazio,
  FiltroSelecao,
  Linha,
  Selecao,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { exportarCsv } from "@/lib/exportar";
import { useTabela } from "@/lib/tabela";
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
  const [verArquivados, setVerArquivados] = useState(false);
  const [formularios, setFormularios] = useState<Formulario[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [novo, setNovo] = useState({
    name: "",
    form_id: "",
    start_date: "",
    end_date: "",
    frequency: "",
  });
  // Quando há id, o mesmo formulário salva em vez de criar. Um formulário só porque os
  // campos são os mesmos, e dois divergiriam na primeira validação nova.
  const [editando, setEditando] = useState<string | null>(null);

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

  function limpar() {
    setNovo({ name: "", form_id: "", start_date: "", end_date: "", frequency: "" });
    setEditando(null);
  }

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api(editando ? `/cycles/${editando}` : "/cycles", {
        method: editando ? "PUT" : "POST",
        body: { ...novo, frequency: novo.frequency || null },
      });
      limpar();
      setMensagem({
        tom: "sucesso",
        texto: editando ? "Ciclo atualizado." : "Ciclo criado como rascunho.",
      });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível salvar o ciclo.",
      });
    }
  }

  function editar(ciclo: Ciclo) {
    setEditando(ciclo.id);
    setNovo({
      name: ciclo.name,
      form_id: ciclo.form_id,
      start_date: ciclo.start_date,
      end_date: ciclo.end_date,
      frequency: ciclo.frequency ?? "",
    });
    // O formulário está no topo: sem isso, clicar em "Editar" numa linha do fim da
    // tabela pareceria não ter feito nada.
    window.scrollTo({ top: 0, behavior: "smooth" });
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

  function nomeDoFormulario(formId: string): string {
    return formularios.find((f) => f.id === formId)?.name ?? "—";
  }

  const tabela = useTabela(ciclos ?? [], {
    busca: (c) => [c.name, nomeDoFormulario(c.form_id)],
    campos: {
      nome: (c) => c.name,
      frequencia: (c) => c.frequency,
      inicio: (c) => c.start_date,
      fim: (c) => c.end_date,
      formulario: (c) => nomeDoFormulario(c.form_id),
      status: (c) => ROTULO_DO_CICLO[c.status] ?? c.status,
    },
    // O mais recente primeiro: é o ciclo em curso que se procura ao abrir a tela.
    inicial: { campo: "inicio", direcao: "desc" },
  });
  const porStatus = tabela.filtro("status", (c, valor) => c.status === valor);
  const arquivados = (ciclos ?? []).filter((c) => c.status === "archived").length;
  const visiveis = tabela
    .visiveis([porStatus])
    .filter((c) => verArquivados || c.status !== "archived");

  function exportar() {
    exportarCsv(
      "ciclos",
      ["Nome", "Frequência", "Início", "Fim", "Formulário", "Status"],
      visiveis.map((c) => [
        c.name,
        c.frequency ?? "avulso",
        formatarData(c.start_date),
        formatarData(c.end_date),
        nomeDoFormulario(c.form_id),
        ROTULO_DO_CICLO[c.status] ?? c.status,
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Ciclos de feedback"
      descricao="Ciclos são períodos definidos para coleta de feedbacks. Cada ciclo tem uma data de início, fim e um formulário associado."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo={editando ? "Editar ciclo" : "Novo ciclo"}>
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
            <div className="flex items-end gap-2">
              <Botao tipo="submit">{editando ? "Salvar" : "Criar rascunho"}</Botao>
              {editando && (
                <Botao variante="fantasma" onClick={limpar}>
                  Cancelar
                </Botao>
              )}
            </div>
          </form>
        </Cartao>

        <Cartao titulo="Ciclos">
          {ciclos === null ? (
            <Carregando />
          ) : ciclos.length === 0 ? (
            <EstadoVazio titulo="Nenhum ciclo ainda" />
          ) : (
            <>
            <BarraDeFiltros
              busca={tabela.busca}
              aoBuscar={tabela.setBusca}
              placeholder="Buscar por nome do ciclo…"
              acoes={
                <>
                  <ContadorDeResultados mostrando={visiveis.length} total={ciclos.length} />
                  <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                </>
              }
            >
              <FiltroSelecao
                rotuloDeTodos="Todos os status"
                valor={porStatus.valor}
                aoMudar={porStatus.aoMudar}
                opcoes={Object.entries(ROTULO_DO_CICLO).map(([valor, rotulo]) => ({
                  valor,
                  rotulo,
                }))}
              />
              {/* O legado tem um botão "Arquivados (N)" que liga e desliga. Aqui é uma
                  caixa: o efeito é o mesmo e o estado fica visível sem contar itens. */}
              <label className="flex items-center gap-2 text-sm text-foreground">
                <input
                  type="checkbox"
                  checked={verArquivados}
                  onChange={(e) => setVerArquivados(e.target.checked)}
                />
                Ver arquivados ({arquivados})
              </label>
            </BarraDeFiltros>

            <Tabela
              ordenacao={tabela.ordenacao}
              vazio={visiveis.length === 0}
              vazioTexto="Nenhum ciclo com esses filtros."
              colunas={[
                { rotulo: "Nome", campo: "nome" },
                { rotulo: "Frequência", campo: "frequencia" },
                { rotulo: "Início", campo: "inicio" },
                { rotulo: "Fim", campo: "fim" },
                { rotulo: "Formulário", campo: "formulario" },
                { rotulo: "Status", campo: "status" },
                "Ações",
              ]}
            >
              {visiveis.map((ciclo) => (
                <Linha key={ciclo.id}>
                  <Celula className="font-medium">{ciclo.name}</Celula>
                  <Celula>{ciclo.frequency ?? "avulso"}</Celula>
                  <Celula>{formatarData(ciclo.start_date)}</Celula>
                  <Celula>
                    {formatarData(ciclo.end_date)}
                    {ciclo.evaluated_end && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        estendido até {formatarData(ciclo.evaluated_end)}
                      </span>
                    )}
                  </Celula>
                  {/* Sem esta coluna não dá para saber que perguntas o ciclo vai fazer —
                      e dois ciclos com o mesmo nome e formulários diferentes ficam
                      indistinguíveis na lista. */}
                  <Celula className="text-muted-foreground">
                    {nomeDoFormulario(ciclo.form_id)}
                  </Celula>
                  <Celula>
                    <Selo tom={TOM_DO_CICLO[ciclo.status as keyof typeof TOM_DO_CICLO]}>
                      {ROTULO_DO_CICLO[ciclo.status] ?? ciclo.status}
                    </Selo>
                  </Celula>
                  <Celula>
                    <span className="flex flex-wrap gap-2">
                      {/* Só rascunho: depois de aberto há requests apontando para o
                          formulário e prazos que as pessoas já viram. Corrigir ciclo em
                          curso é "estender", que é outra coisa. */}
                      {ciclo.status === "draft" && (
                        <Botao variante="fantasma" onClick={() => editar(ciclo)}>
                          Editar
                        </Botao>
                      )}
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
            </>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
