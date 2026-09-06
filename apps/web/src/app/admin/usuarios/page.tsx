"use client";

/**
 * Usuários — cadastro, papel, capacidades e remoção.
 *
 * As capacidades aparecem como switches individuais porque é isso que elas são
 * (BR-MIGRAR-015): atributos do perfil, não consequências do papel. Marcar alguém como
 * gestor não liga nenhuma flag, e é essa separação que o legado não tinha — lá,
 * "coordenador" virou papel e duplicou telas.
 *
 * Remover é soft-delete: o histórico fica, o acesso cai na hora (BR-MIGRAR-018).
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
  SeloDePapel,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { exportarCsv } from "@/lib/exportar";
import { ROTULO_DO_STATUS_DE_PESSOA } from "@/lib/formato";
import { useTabela } from "@/lib/tabela";
import type { Departamento, Perfil } from "@/lib/tipos";

const PAPEIS = ["colaborador", "gestor", "rh", "admin"];

const CAPACIDADES: { chave: string; rotulo: string }[] = [
  { chave: "can_request_client_feedback", rotulo: "Pedir avaliação de cliente" },
  { chave: "can_view_feedback_answers", rotulo: "Ver respostas de feedback" },
  { chave: "can_view_team_history", rotulo: "Ver histórico da equipe" },
  { chave: "can_generate_reports", rotulo: "Gerar relatórios" },
  { chave: "can_view_manager_dashboard", rotulo: "Ver painel de gestor" },
];

export default function AdminUsuarios() {
  const [perfis, setPerfis] = useState<Perfil[] | null>(null);
  const [departamentos, setDepartamentos] = useState<Departamento[]>([]);
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [novo, setNovo] = useState({
    email: "",
    senha: "",
    full_name: "",
    role: "colaborador",
    job_title: "",
  });

  const carregar = useCallback(async () => {
    const [lista, deptos] = await Promise.all([
      api<Perfil[]>("/profiles"),
      api<Departamento[]>("/departments"),
    ]);
    setPerfis(lista);
    setDepartamentos(deptos);
  }, []);

  useEffect(() => {
    carregar().catch(() => setPerfis([]));
  }, [carregar]);

  function relatar(falha: unknown, padrao: string) {
    setMensagem({
      tom: "erro",
      texto: falha instanceof ApiError ? falha.message : padrao,
    });
  }

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/profiles", {
        method: "POST",
        body: { ...novo, job_title: novo.job_title || null },
      });
      setNovo({ email: "", senha: "", full_name: "", role: "colaborador", job_title: "" });
      setMensagem({ tom: "sucesso", texto: "Usuário criado." });
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível criar o usuário.");
    }
  }

  async function mudarPapel(perfil: Perfil, role: string) {
    setMensagem(null);
    try {
      await api(`/profiles/${perfil.id}/role`, { method: "PUT", body: { role } });
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível mudar o papel.");
    }
  }

  async function alternarCapacidade(perfil: Perfil, chave: string, valor: boolean) {
    setMensagem(null);
    try {
      // PATCH manda só a chave que mudou: omitir as outras é o que evita desligar por
      // acidente uma capacidade que ninguém tocou.
      await api(`/profiles/${perfil.id}/flags`, {
        method: "PATCH",
        body: { flags: { [chave]: valor } },
      });
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível alterar a capacidade.");
    }
  }

  async function remover(perfil: Perfil) {
    setMensagem(null);
    try {
      await api(`/profiles/${perfil.id}`, { method: "DELETE" });
      setMensagem({
        tom: "sucesso",
        texto: "Usuário removido. O histórico foi preservado e as sessões dele caíram.",
      });
      await carregar();
    } catch (falha) {
      relatar(falha, "Não foi possível remover.");
    }
  }

  const perfil = perfis?.find((p) => p.id === selecionado) ?? null;

  function nomeDoDepartamento(id: string | null): string {
    return departamentos.find((d) => d.id === id)?.name ?? "—";
  }

  const tabela = useTabela(perfis ?? [], {
    busca: (p) => [p.full_name, p.email, p.job_title],
    campos: {
      nome: (p) => p.full_name,
      email: (p) => p.email,
      cargo: (p) => p.job_title,
      departamento: (p) => nomeDoDepartamento(p.department_id),
      papel: (p) => p.role,
      status: (p) => p.status,
    },
    inicial: { campo: "nome" },
  });
  const porDepartamento = tabela.filtro("departamento", (p, valor) => p.department_id === valor);
  const porPapel = tabela.filtro("papel", (p, valor) => p.role === valor);
  const porStatus = tabela.filtro("status", (p, valor) => p.status === valor);
  const visiveis = tabela.visiveis([porDepartamento, porPapel, porStatus]);

  function exportar() {
    // Exporta o que está na tela, com os filtros aplicados — é o que
    // `target_screens.md` pede em `reflects_filters`.
    exportarCsv(
      "usuarios",
      ["Nome", "E-mail", "Cargo", "Departamento", "Papel", "Status", "Coordena"],
      visiveis.map((p) => [
        p.full_name,
        p.email ?? "",
        p.job_title ?? "",
        nomeDoDepartamento(p.department_id),
        p.role,
        ROTULO_DO_STATUS_DE_PESSOA[p.status] ?? p.status,
        p.is_coordinator ? "sim" : "não",
      ]),
    );
  }

  return (
    <PaginaAutenticada
      titulo="Usuários"
      descricao="Cadastro, papéis e capacidades individuais do escritório."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Novo usuário" descricao="A credencial e o perfil são criados juntos.">
          <form onSubmit={criar} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Campo rotulo="Nome completo" obrigatorio>
              <Entrada
                required
                value={novo.full_name}
                onChange={(e) => setNovo({ ...novo, full_name: e.target.value })}
              />
            </Campo>
            <Campo rotulo="E-mail" obrigatorio>
              <Entrada
                type="email"
                required
                value={novo.email}
                onChange={(e) => setNovo({ ...novo, email: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Senha inicial" obrigatorio dica="Mínimo de 8 caracteres.">
              <Entrada
                type="password"
                required
                minLength={8}
                value={novo.senha}
                onChange={(e) => setNovo({ ...novo, senha: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Cargo">
              <Entrada
                value={novo.job_title}
                onChange={(e) => setNovo({ ...novo, job_title: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Papel" obrigatorio>
              <Selecao
                value={novo.role}
                onChange={(e) => setNovo({ ...novo, role: e.target.value })}
              >
                {PAPEIS.map((papel) => (
                  <option key={papel} value={papel}>
                    {papel}
                  </option>
                ))}
              </Selecao>
            </Campo>
            <div className="flex items-end">
              <Botao tipo="submit">Criar usuário</Botao>
            </div>
          </form>
        </Cartao>

        <Cartao
          titulo="Pessoas"
          descricao={
            perfis === null ? undefined : `${perfis.length} pessoa(s) ativa(s) no escritório.`
          }
        >
          {perfis === null ? (
            <Carregando />
          ) : perfis.length === 0 ? (
            <EstadoVazio titulo="Nenhum usuário ativo" />
          ) : (
            <>
              <BarraDeFiltros
                busca={tabela.busca}
                aoBuscar={tabela.setBusca}
                placeholder="Buscar por nome, e-mail ou cargo…"
                acoes={
                  <>
                    <ContadorDeResultados mostrando={visiveis.length} total={perfis.length} />
                    <BotaoDeExportar quantidade={visiveis.length} onClick={exportar} />
                  </>
                }
              >
                <FiltroSelecao
                  rotuloDeTodos="Todos os departamentos"
                  valor={porDepartamento.valor}
                  aoMudar={porDepartamento.aoMudar}
                  opcoes={departamentos.map((d) => ({ valor: d.id, rotulo: d.name }))}
                />
                <FiltroSelecao
                  rotuloDeTodos="Todos os papéis"
                  valor={porPapel.valor}
                  aoMudar={porPapel.aoMudar}
                  opcoes={PAPEIS.map((p) => ({ valor: p, rotulo: p }))}
                />
                <FiltroSelecao
                  rotuloDeTodos="Todos os status"
                  valor={porStatus.valor}
                  aoMudar={porStatus.aoMudar}
                  opcoes={Object.entries(ROTULO_DO_STATUS_DE_PESSOA).map(([valor, rotulo]) => ({
                    valor,
                    rotulo,
                  }))}
                />
              </BarraDeFiltros>

              <Tabela
                ordenacao={tabela.ordenacao}
                vazio={visiveis.length === 0}
                vazioTexto="Nenhuma pessoa com esses filtros."
                colunas={[
                  { rotulo: "Nome", campo: "nome" },
                  { rotulo: "E-mail", campo: "email" },
                  { rotulo: "Cargo", campo: "cargo" },
                  { rotulo: "Departamento", campo: "departamento" },
                  { rotulo: "Papel", campo: "papel" },
                  { rotulo: "Status", campo: "status" },
                  "Capacidades",
                  "Ações",
                ]}
              >
              {visiveis.map((pessoa) => (
                <Linha key={pessoa.id}>
                  <Celula className="font-medium">
                    <span className="flex items-center gap-2">
                      {pessoa.full_name}
                      {pessoa.is_coordinator && <SeloDePapel papel={pessoa.role} coordenador />}
                    </span>
                  </Celula>
                  <Celula className="text-muted-foreground">{pessoa.email ?? "—"}</Celula>
                  <Celula>{pessoa.job_title ?? "—"}</Celula>
                  <Celula>{nomeDoDepartamento(pessoa.department_id)}</Celula>
                  <Celula>
                    <Selecao
                      value={pessoa.role}
                      onChange={(e) => void mudarPapel(pessoa, e.target.value)}
                      // `min-w`, e não `w`: `CLASSE_ENTRADA` já traz `w-full`, e duas
                      // utilitárias de `width` disputam pela ordem no CSS gerado. Sem
                      // isto a coluna espreme o select até sobrar uma letra.
                      className="h-8 min-w-[7.5rem] py-0 text-xs"
                    >
                      {PAPEIS.map((papel) => (
                        <option key={papel} value={papel}>
                          {papel}
                        </option>
                      ))}
                    </Selecao>
                  </Celula>
                  <Celula>
                    <Selo tom={pessoa.status === "active" ? "sucesso" : "neutro"}>
                      {ROTULO_DO_STATUS_DE_PESSOA[pessoa.status] ?? pessoa.status}
                    </Selo>
                  </Celula>
                  <Celula>
                    <button
                      type="button"
                      onClick={() => setSelecionado(selecionado === pessoa.id ? null : pessoa.id)}
                      className="text-sm text-primary underline-offset-4 hover:underline"
                    >
                      {selecionado === pessoa.id ? "Fechar" : "Editar"}
                    </button>
                  </Celula>
                  <Celula>
                    <button
                      type="button"
                      onClick={() => void remover(pessoa)}
                      className="text-sm text-destructive underline-offset-4 hover:underline"
                    >
                      Remover
                    </button>
                  </Celula>
                </Linha>
              ))}
              </Tabela>
            </>
          )}
        </Cartao>

        {perfil && (
          <Cartao
            titulo={`Capacidades de ${perfil.full_name}`}
            descricao="Capacidade é atributo da pessoa, não consequência do papel."
          >
            <ul className="grid gap-3 sm:grid-cols-2">
              {CAPACIDADES.map((capacidade) => (
                <li key={capacidade.chave} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-foreground">{capacidade.rotulo}</span>
                  <span className="flex gap-2">
                    <Botao
                      variante="secundario"
                      onClick={() => void alternarCapacidade(perfil, capacidade.chave, true)}
                    >
                      Conceder
                    </Botao>
                    <Botao
                      variante="fantasma"
                      onClick={() => void alternarCapacidade(perfil, capacidade.chave, false)}
                    >
                      Revogar
                    </Botao>
                  </span>
                </li>
              ))}
            </ul>

            <div className="mt-5 border-t border-border pt-4">
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-foreground">Coordenação:</span>
                <Botao
                  variante="secundario"
                  onClick={async () => {
                    await api(`/profiles/${perfil.id}/coordinator`, {
                      method: "PUT",
                      body: { is_coordinator: !perfil.is_coordinator },
                    });
                    await carregar();
                  }}
                >
                  {perfil.is_coordinator ? "Remover coordenação" : "Tornar coordenador"}
                </Botao>
              </span>
            </div>
          </Cartao>
        )}
      </div>
    </PaginaAutenticada>
  );
}
