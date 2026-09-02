"use client";

/**
 * Diagnóstico de permissões.
 *
 * Responde uma pergunta só, e é a mais cara de responder tarde: **o próximo ciclo vai
 * sair certo?** Sem esta tela, o administrador descobre que dezenas de pessoas ficaram
 * sem pedido depois de abrir o ciclo — e aí a correção já custa reabrir a conversa com
 * o time inteiro.
 *
 * Cada categoria vem com o que fazer a respeito, e duas trazem a ação embutida. É o que
 * diferencia diagnóstico de relatório: relatório informa, diagnóstico conserta.
 */

import { useCallback, useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Carregando,
  Cartao,
  Celula,
  EstadoVazio,
  Estatistica,
  Linha,
  Selo,
  Tabela,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Ciclo, Diagnostico, ParDePermissao, PessoaComCarga } from "@/lib/tipos";

export default function AdminDiagnostico() {
  const [diagnostico, setDiagnostico] = useState<Diagnostico | null>(null);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    const [dados, abertos] = await Promise.all([
      api<Diagnostico>("/permissions/diagnostics"),
      api<Ciclo[]>("/cycles", { query: { status: "open" } }),
    ]);
    setDiagnostico(dados);
    setCiclos(abertos);
  }, []);

  useEffect(() => {
    carregar().catch(() => setMensagem({ tom: "erro", texto: "Não foi possível diagnosticar." }));
  }, [carregar]);

  async function criarRequestsFaltantes() {
    const ciclo = ciclos[0];
    if (!ciclo) return;
    setMensagem(null);
    try {
      const resposta = await api<{ requests_criados: number }>(
        `/cycles/${ciclo.id}/regenerate-requests`,
        { method: "POST" },
      );
      setMensagem({
        tom: "sucesso",
        texto: `${resposta.requests_criados} pedido(s) criado(s) no ciclo aberto.`,
      });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível criar os pedidos.",
      });
    }
  }

  async function desativarComInativos() {
    setMensagem(null);
    try {
      const resposta = await api<{ desativadas: number }>("/permissions/deactivate-inactive", {
        method: "POST",
      });
      setMensagem({
        tom: "sucesso",
        texto: `${resposta.desativadas} permissão(ões) desativada(s). O histórico foi preservado.`,
      });
      await carregar();
    } catch {
      setMensagem({ tom: "erro", texto: "Não foi possível desativar." });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Diagnóstico de permissões"
      descricao="Identifica inconsistências e antecipa problemas no próximo ciclo."
      acao={
        diagnostico && (
          <Selo tom={diagnostico.pontos_de_atencao > 0 ? "perigo" : "sucesso"}>
            {diagnostico.pontos_de_atencao} ponto(s) de atenção
          </Selo>
        )
      }
    >
      {diagnostico === null ? (
        <Carregando />
      ) : (
        <div className="space-y-6">
          {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Estatistica
              rotulo="Ciclo ativo"
              valor={diagnostico.ciclo_ativo ?? "nenhum"}
              detalhe={
                diagnostico.dias_para_fechar !== null
                  ? `fecha em ${diagnostico.dias_para_fechar} dia(s)`
                  : undefined
              }
            />
            <Estatistica rotulo="Permissões ativas" valor={diagnostico.permissoes_ativas} />
            <Estatistica rotulo="Usuários ativos" valor={diagnostico.usuarios_ativos} />
            <Estatistica
              rotulo="Pedidos no próximo ciclo"
              valor={diagnostico.requests_a_criar}
              detalhe="se nada mudar"
            />
          </div>

          <CategoriaDePares
            titulo="Permissões sem pedido no ciclo ativo"
            tom="perigo"
            explicacao="Essas pessoas não veem o feedback em Meus Feedbacks e não recebem lembrete."
            acao={
              ciclos.length > 0 ? (
                <Botao onClick={() => void criarRequestsFaltantes()}>
                  Criar pedidos faltantes
                </Botao>
              ) : undefined
            }
            itens={diagnostico.sem_request}
          />

          <CategoriaDePares
            titulo="Par recíproco faltando"
            tom="alerta"
            explicacao="Permissões recíprocas em que só uma direção existe — alguém avalia sem ser avaliado."
            itens={diagnostico.par_reverso_faltando}
          />

          <CategoriaDePares
            titulo="Permissões com usuário inativo"
            tom="neutro"
            explicacao="Não causam erro, mas geram pedidos desnecessários e poluem os relatórios."
            acao={
              diagnostico.com_usuario_inativo.length > 0 ? (
                <Botao variante="secundario" onClick={() => void desativarComInativos()}>
                  Desativar {diagnostico.com_usuario_inativo.length} permissão(ões)
                </Botao>
              ) : undefined
            }
            itens={diagnostico.com_usuario_inativo}
          />

          <Cartao
            titulo={`Usuários sem cobertura (${diagnostico.sem_cobertura.length})`}
            descricao="Estão fora do processo: não avaliam e não são avaliados."
          >
            {diagnostico.sem_cobertura.length === 0 ? (
              <EstadoVazio titulo="Todo mundo está coberto" />
            ) : (
              <ul className="flex flex-wrap gap-2">
                {diagnostico.sem_cobertura.map((pessoa) => (
                  <li key={pessoa.profile_id}>
                    <Selo tom="alerta">{pessoa.nome}</Selo>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>

          <Cartao
            titulo="Equilíbrio de carga"
            descricao={`Média de ${diagnostico.media_por_avaliador} avaliação(ões) por avaliador e ${diagnostico.media_por_avaliado} por avaliado.`}
          >
            <div className="grid gap-6 sm:grid-cols-2">
              <Carga
                titulo="Avaliadores com poucas"
                pessoas={diagnostico.poucos_avaliadores}
              />
              <Carga titulo="Avaliados com poucas recebidas" pessoas={diagnostico.poucos_avaliados} />
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Desequilíbrio não entra na contagem de pontos de atenção: é informação para
              calibrar a matriz, não defeito a corrigir.
            </p>
          </Cartao>
        </div>
      )}
    </PaginaAutenticada>
  );
}

function CategoriaDePares({
  titulo,
  tom,
  explicacao,
  itens,
  acao,
}: {
  titulo: string;
  tom: "perigo" | "alerta" | "neutro";
  explicacao: string;
  itens: ParDePermissao[];
  acao?: React.ReactNode;
}) {
  return (
    <Cartao
      titulo={`${titulo} (${itens.length})`}
      descricao={explicacao}
      acao={itens.length > 0 ? acao : undefined}
    >
      {itens.length === 0 ? (
        <EstadoVazio titulo="Nada a corrigir aqui" />
      ) : (
        <Tabela colunas={["Avaliador", "Avaliado", "Tipo"]}>
          {itens.slice(0, 100).map((par) => (
            <Linha key={par.permission_id}>
              <Celula className="font-medium">{par.reviewer_nome}</Celula>
              <Celula>{par.reviewee_nome}</Celula>
              <Celula>
                <Selo tom={tom}>{par.permission_type}</Selo>
              </Celula>
            </Linha>
          ))}
        </Tabela>
      )}
      {itens.length > 100 && (
        <p className="mt-3 text-xs text-muted-foreground">
          Mostrando 100 de {itens.length}.
        </p>
      )}
    </Cartao>
  );
}

function Carga({ titulo, pessoas }: { titulo: string; pessoas: PessoaComCarga[] }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-foreground">
        {titulo} ({pessoas.length})
      </h3>
      {pessoas.length === 0 ? (
        <p className="text-sm text-muted-foreground">Ninguém abaixo do limite.</p>
      ) : (
        <ul className="space-y-1">
          {pessoas.map((pessoa) => (
            <li
              key={pessoa.profile_id}
              className="flex justify-between text-sm text-foreground"
            >
              <span>{pessoa.nome}</span>
              <span className="text-muted-foreground">{pessoa.quantidade}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
