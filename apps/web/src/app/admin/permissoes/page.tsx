"use client";

/**
 * Permissões — a matriz de quem avalia quem.
 *
 * É a tela que alimenta a geração de pedidos: abrir um ciclo lê daqui. Sem ela, o
 * sistema tinha um buraco embaraçoso — dava para abrir o ciclo pela interface, mas
 * não para configurar o que ele geraria.
 *
 * `peer_to_peer` cria a recíproca sozinho, no servidor, dentro da mesma transação
 * (BR-MIGRAR-002). A tela não simula isso: ela salva e recarrega, e a recíproca
 * aparece. Foi por duplicar essa lógica no front que o legado ficava com meia relação
 * quando alguém salvava por outro caminho.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  AreaDeTexto,
  Aviso,
  BarraDeFiltros,
  Botao,
  BotaoDeExportar,
  Campo,
  Carregando,
  Cartao,
  Celula,
  ContadorDeResultados,
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
import type { Ciclo, Perfil, PermissaoDeFeedback } from "@/lib/tipos";

const TIPOS: { valor: string; rotulo: string; explicacao: string }[] = [
  {
    valor: "peer_to_peer",
    rotulo: "Par (recíproco)",
    explicacao: "Cria também a permissão inversa automaticamente.",
  },
  { valor: "peer", rotulo: "Par (só esta direção)", explicacao: "Sem recíproca." },
  { valor: "manager", rotulo: "Gestor avalia liderado", explicacao: "" },
  { valor: "manager_to_report", rotulo: "Gestor → liderado", explicacao: "" },
  { valor: "upward", rotulo: "Liderado avalia gestor", explicacao: "" },
  { valor: "subordinate", rotulo: "Subordinado", explicacao: "" },
  { valor: "self", rotulo: "Autoavaliação", explicacao: "Único tipo com avaliador = avaliado." },
  { valor: "custom", rotulo: "Personalizada", explicacao: "" },
];

export default function AdminPermissoes() {
  const [permissoes, setPermissoes] = useState<PermissaoDeFeedback[] | null>(null);
  const [pessoas, setPessoas] = useState<Perfil[]>([]);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [abertos, setAbertos] = useState<string[]>([]);
  const [importacao, setImportacao] = useState("");
  const [nova, setNova] = useState({
    reviewer_id: "",
    reviewee_id: "",
    permission_type: "peer_to_peer",
    cycle_id: "",
  });

  const carregar = useCallback(async () => {
    const [regras, perfis, listaDeCiclos] = await Promise.all([
      api<PermissaoDeFeedback[]>("/permissions"),
      api<Perfil[]>("/profiles"),
      api<Ciclo[]>("/cycles"),
    ]);
    setPermissoes(regras);
    setPessoas(perfis);
    setCiclos(listaDeCiclos);
  }, []);

  useEffect(() => {
    carregar().catch(() => setPermissoes([]));
  }, [carregar]);

  const nomePor = useMemo(
    () => new Map(pessoas.map((pessoa) => [pessoa.id, pessoa.full_name])),
    [pessoas],
  );

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/permissions", {
        method: "POST",
        body: { ...nova, cycle_id: nova.cycle_id || null },
      });
      setMensagem({
        tom: "sucesso",
        texto:
          nova.permission_type === "peer_to_peer"
            ? "Permissão salva — a recíproca foi criada junto."
            : "Permissão salva.",
      });
      setNova({ ...nova, reviewer_id: "", reviewee_id: "" });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível salvar.",
      });
    }
  }

  async function alternar(regra: PermissaoDeFeedback) {
    setMensagem(null);
    try {
      await api("/permissions", {
        method: "POST",
        body: {
          reviewer_id: regra.reviewer_id,
          reviewee_id: regra.reviewee_id,
          permission_type: regra.permission_type,
          cycle_id: regra.cycle_id,
          active: !regra.active,
        },
      });
      await carregar();
    } catch {
      setMensagem({ tom: "erro", texto: "Não foi possível alterar." });
    }
  }

  function nomeDoCiclo(cycleId: string | null): string {
    if (!cycleId) return "permanente";
    return ciclos.find((c) => c.id === cycleId)?.name ?? "ciclo específico";
  }

  function rotuloDoTipo(tipo: string): string {
    return TIPOS.find((t) => t.valor === tipo)?.rotulo ?? tipo;
  }

  const tabela = useTabela(permissoes ?? [], {
    busca: (regra) => [nomePor.get(regra.reviewer_id), nomePor.get(regra.reviewee_id)],
    campos: {
      avaliador: (regra) => nomePor.get(regra.reviewer_id),
      avaliado: (regra) => nomePor.get(regra.reviewee_id),
      tipo: (regra) => rotuloDoTipo(regra.permission_type),
      alcance: (regra) => nomeDoCiclo(regra.cycle_id),
      situacao: (regra) => (regra.active ? "ativa" : "inativa"),
    },
    inicial: { campo: "avaliador" },
  });
  const porTipo = tabela.filtro("tipo", (regra, valor) => regra.permission_type === valor);
  const porSituacao = tabela.filtro("situacao", (regra, valor) =>
    valor === "ativa" ? regra.active : !regra.active,
  );
  const porCiclo = tabela.filtro("ciclo", (regra, valor) =>
    valor === "permanente" ? regra.cycle_id === null : regra.cycle_id === valor,
  );
  const visiveis = tabela.visiveis([porTipo, porSituacao, porCiclo]);

  const ativas = (permissoes ?? []).filter((regra) => regra.active).length;

  /**
   * A matriz agrupada por avaliador, como no oráculo.
   *
   * A tabela plana funciona com dezesseis regras e deixa de funcionar com trezentas: a
   * pergunta que se faz nesta tela é "quem a Bruna avalia", e numa lista de pares ela
   * exige varrer a coluna inteira. Agrupado, cada pessoa é uma linha que abre.
   */
  const porAvaliador = (() => {
    const grupos = new Map<string, typeof visiveis>();
    for (const regra of visiveis) {
      const atual = grupos.get(regra.reviewer_id) ?? [];
      atual.push(regra);
      grupos.set(regra.reviewer_id, atual);
    }
    return [...grupos.entries()]
      .map(([reviewerId, regras]) => ({
        reviewerId,
        nome: nomePor.get(reviewerId) ?? "(removido)",
        regras,
        ativas: regras.filter((r) => r.active).length,
      }))
      .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  })();

  function iniciais(nome: string): string {
    return nome
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((parte) => parte[0]?.toUpperCase() ?? "")
      .join("");
  }

  async function importar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);

    // Formato: uma linha por par, "avaliador;avaliado[;tipo]". Nomes, e não uuid: quem
    // monta a matriz monta numa planilha, e lá o que existe é o nome das pessoas.
    const porNome = new Map(
      pessoas.map((p) => [p.full_name.trim().toLowerCase(), p.id] as const),
    );
    const linhas = importacao
      .split("\n")
      .map((linha) => linha.trim())
      .filter(Boolean);

    const permissoes: unknown[] = [];
    const problemas: string[] = [];
    linhas.forEach((linha, indice) => {
      const [avaliador, avaliado, tipo] = linha.split(";").map((c) => c.trim());
      const reviewer = porNome.get((avaliador ?? "").toLowerCase());
      const reviewee = porNome.get((avaliado ?? "").toLowerCase());
      if (!reviewer || !reviewee) {
        problemas.push(
          `linha ${indice + 1}: não encontrei ${!reviewer ? avaliador : avaliado}`,
        );
        return;
      }
      permissoes.push({
        reviewer_id: reviewer,
        reviewee_id: reviewee,
        permission_type: tipo || "peer_to_peer",
        cycle_id: null,
        active: true,
      });
    });

    if (problemas.length > 0) {
      setMensagem({ tom: "erro", texto: problemas.slice(0, 5).join(" · ") });
      return;
    }
    if (permissoes.length === 0) {
      setMensagem({ tom: "erro", texto: "Nada para importar." });
      return;
    }

    try {
      const resultado = await api<{ criadas: number; ja_existiam: number }>(
        "/permissions/bulk",
        { method: "POST", body: { permissoes } },
      );
      setImportacao("");
      setMensagem({
        tom: "sucesso",
        texto:
          `${resultado.criadas} permissão(ões) criada(s)` +
          (resultado.ja_existiam > 0 ? `, ${resultado.ja_existiam} já existia(m).` : "."),
      });
      await carregar();
    } catch (falha) {
      // O servidor recusa o lote inteiro quando há linha ruim: meia matriz gravada é
      // pior que nenhuma, porque o ciclo abriria com metade das pessoas sem par.
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível importar.",
      });
    }
  }

  function exportar() {
    exportarCsv(
      "permissoes",
      ["Avaliador", "Avaliado", "Tipo", "Alcance", "Situação"],
      visiveis.map((regra) => [
        nomePor.get(regra.reviewer_id) ?? "",
        nomePor.get(regra.reviewee_id) ?? "",
        rotuloDoTipo(regra.permission_type),
        nomeDoCiclo(regra.cycle_id),
        regra.active ? "ativa" : "inativa",
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Permissões de feedback"
      descricao="Quem avalia quem. É esta matriz que a abertura de ciclo lê para gerar os pedidos."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Nova permissão">
          <form onSubmit={salvar} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Campo rotulo="Avaliador" obrigatorio>
              <Selecao
                required
                value={nova.reviewer_id}
                onChange={(e) => setNova({ ...nova, reviewer_id: e.target.value })}
              >
                <option value="">Selecione</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo rotulo="Avaliado" obrigatorio>
              <Selecao
                required
                value={nova.reviewee_id}
                onChange={(e) => setNova({ ...nova, reviewee_id: e.target.value })}
              >
                <option value="">Selecione</option>
                {pessoas.map((pessoa) => (
                  <option key={pessoa.id} value={pessoa.id}>
                    {pessoa.full_name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo
              rotulo="Tipo"
              dica={TIPOS.find((t) => t.valor === nova.permission_type)?.explicacao}
            >
              <Selecao
                value={nova.permission_type}
                onChange={(e) => setNova({ ...nova, permission_type: e.target.value })}
              >
                {TIPOS.map((tipo) => (
                  <option key={tipo.valor} value={tipo.valor}>
                    {tipo.rotulo}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <Campo rotulo="Ciclo" dica="Em branco vale para todos os ciclos.">
              <Selecao
                value={nova.cycle_id}
                onChange={(e) => setNova({ ...nova, cycle_id: e.target.value })}
              >
                <option value="">Permanente</option>
                {ciclos.map((ciclo) => (
                  <option key={ciclo.id} value={ciclo.id}>
                    {ciclo.name}
                  </option>
                ))}
              </Selecao>
            </Campo>

            <div className="flex items-end">
              <Botao tipo="submit">Salvar</Botao>
            </div>
          </form>
        </Cartao>

        <Cartao
          titulo="Importar em massa"
          descricao="Uma linha por par, no formato avaliador;avaliado — o tipo é opcional."
        >
          <form onSubmit={importar} className="space-y-3">
            {/* Nomes, e não uuid: quem monta a matriz monta numa planilha, e lá o que
                existe é o nome das pessoas. Nome que não bate para a importação inteira
                antes de gravar qualquer linha. */}
            <AreaDeTexto
              value={importacao}
              onChange={(e) => setImportacao(e.target.value)}
              placeholder={[
                "Bruna Camargo;Diego Ramos",
                "Diego Ramos;Bruna Camargo",
                "Marina Duarte;Bruna Camargo;manager_to_report",
              ].join("\n")}
              className="min-h-32 font-mono text-xs"
            />
            <span className="flex items-center gap-3">
              <Botao tipo="submit" desabilitado={!importacao.trim()}>
                Importar
              </Botao>
              <span className="text-xs text-muted-foreground">
                Um erro em qualquer linha cancela o lote inteiro — meia matriz é pior que
                nenhuma.
              </span>
            </span>
          </form>
        </Cartao>

        <Cartao titulo={`Matriz (${ativas} ativa${ativas === 1 ? "" : "s"})`}>
          {permissoes === null ? (
            <Carregando />
          ) : permissoes.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma permissão"
              descricao="Sem permissões ativas, abrir um ciclo não gera pedido nenhum."
            />
          ) : (
            <>
            <BarraDeFiltros
              busca={tabela.busca}
              aoBuscar={tabela.setBusca}
              placeholder="Buscar por nome…"
              acoes={
                <>
                  <ContadorDeResultados mostrando={visiveis.length} total={permissoes.length} />
                  <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                </>
              }
            >
              <FiltroSelecao
                rotuloDeTodos="Todos os tipos"
                valor={porTipo.valor}
                aoMudar={porTipo.aoMudar}
                opcoes={TIPOS.map((t) => ({ valor: t.valor, rotulo: t.rotulo }))}
              />
              <FiltroSelecao
                rotuloDeTodos="Todas as situações"
                valor={porSituacao.valor}
                aoMudar={porSituacao.aoMudar}
                opcoes={[
                  { valor: "ativa", rotulo: "Ativas" },
                  { valor: "inativa", rotulo: "Inativas" },
                ]}
              />
              <FiltroSelecao
                rotuloDeTodos="Todos os ciclos"
                valor={porCiclo.valor}
                aoMudar={porCiclo.aoMudar}
                opcoes={[
                  { valor: "permanente", rotulo: "Permanentes" },
                  ...ciclos.map((c) => ({ valor: c.id, rotulo: c.name })),
                ]}
              />
            </BarraDeFiltros>

            {visiveis.length === 0 ? (
              <EstadoVazio titulo="Nenhuma permissão com esses filtros" />
            ) : (
              <ul className="divide-y divide-border">
                {porAvaliador.map((grupo) => (
                  <li key={grupo.reviewerId} className="py-1">
                    <button
                      type="button"
                      onClick={() =>
                        setAbertos((atual) =>
                          atual.includes(grupo.reviewerId)
                            ? atual.filter((id) => id !== grupo.reviewerId)
                            : [...atual, grupo.reviewerId],
                        )
                      }
                      aria-expanded={abertos.includes(grupo.reviewerId)}
                      className="flex w-full items-center gap-3 rounded-md px-2 py-2.5 text-left hover:bg-muted"
                    >
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                        {iniciais(grupo.nome)}
                      </span>
                      <span className="flex-1 text-sm font-medium text-foreground">
                        {grupo.nome}
                      </span>
                      <Selo tom={grupo.ativas > 0 ? "sucesso" : "neutro"}>
                        {grupo.ativas} ativa{grupo.ativas === 1 ? "" : "s"}
                      </Selo>
                      <span className="text-xs text-muted-foreground" aria-hidden="true">
                        {abertos.includes(grupo.reviewerId) ? "▲" : "▼"}
                      </span>
                    </button>

                    {abertos.includes(grupo.reviewerId) && (
                      <div className="pb-2 pl-11">
            <Tabela
              ordenacao={tabela.ordenacao}
              colunas={[
                { rotulo: "Avaliado", campo: "avaliado" },
                { rotulo: "Tipo", campo: "tipo" },
                { rotulo: "Alcance", campo: "alcance" },
                { rotulo: "Situação", campo: "situacao" },
                "",
              ]}
            >
              {grupo.regras.map((regra) => (
                <Linha key={regra.id}>
                  <Celula>{nomePor.get(regra.reviewee_id) ?? "—"}</Celula>
                  <Celula>
                    {rotuloDoTipo(regra.permission_type)}
                  </Celula>
                  <Celula className="text-muted-foreground">{nomeDoCiclo(regra.cycle_id)}</Celula>
                  <Celula>
                    <Selo tom={regra.active ? "sucesso" : "neutro"}>
                      {regra.active ? "ativa" : "inativa"}
                    </Selo>
                  </Celula>
                  <Celula className="text-right">
                    <button
                      type="button"
                      onClick={() => void alternar(regra)}
                      className="text-sm text-primary underline-offset-4 hover:underline"
                    >
                      {regra.active ? "Desativar" : "Ativar"}
                    </button>
                  </Celula>
                </Linha>
              ))}
            </Tabela>
                      </div>
                    )}
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
