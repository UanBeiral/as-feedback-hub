"use client";

/**
 * Avaliações de clientes — pedir link e acompanhar respostas.
 *
 * O WhatsApp aparece mascarado para quem não é admin/RH, e o mascaramento é do
 * servidor (BR-MIGRAR-022): a tela mostra o que recebeu, sem ter o número completo em
 * lugar nenhum. Não adianta abrir o DevTools.
 *
 * O token só existe na resposta da criação — é dele que sai o link para mandar ao
 * cliente. Nas listagens ele não vem, porque quem vê a lista não precisa poder
 * responder no lugar do cliente.
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
import { formatarDataHora } from "@/lib/formato";
import { temCapacidade, useSessao } from "@/lib/sessao";
import type { AvaliacaoDeCliente, Perfil } from "@/lib/tipos";

export default function AvaliacoesDeClientes() {
  const { usuario } = useSessao();
  const [avaliacoes, setAvaliacoes] = useState<AvaliacaoDeCliente[] | null>(null);
  const [equipe, setEquipe] = useState<Perfil[]>([]);
  const [link, setLink] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);
  const [pedido, setPedido] = useState({ target_user_id: "", client_name: "", client_whatsapp: "" });

  const podePedir = temCapacidade(usuario, "can_request_client_feedback");

  const carregar = useCallback(async () => {
    const [lista, membros] = await Promise.all([
      api<AvaliacaoDeCliente[]>("/client-eval/evaluations"),
      api<Perfil[]>("/auth/my-team"),
    ]);
    setAvaliacoes(lista);
    setEquipe(membros);
  }, []);

  useEffect(() => {
    carregar().catch(() => setAvaliacoes([]));
  }, [carregar]);

  async function pedir(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    setLink(null);
    try {
      const resposta = await api<{ public_path: string }>("/client-eval/requests", {
        method: "POST",
        body: {
          target_user_id: pedido.target_user_id,
          client_name: pedido.client_name || null,
          client_whatsapp: pedido.client_whatsapp || null,
        },
      });
      setLink(`${window.location.origin}${resposta.public_path}`);
      setMensagem({ tom: "sucesso", texto: "Link gerado. Copie e mande para o cliente." });
      await carregar();
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError && falha.status === 403
            ? "Você não tem a capacidade de pedir avaliação de cliente."
            : "Não foi possível gerar o link.",
      });
    }
  }

  return (
    <PaginaAutenticada
      titulo="Avaliações de clientes"
      descricao="Gere o link, mande ao cliente e acompanhe as respostas."
    >
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        {podePedir && (
          <Cartao titulo="Pedir avaliação">
            <form onSubmit={pedir} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Campo rotulo="Quem será avaliado" obrigatorio>
                <Selecao
                  required
                  value={pedido.target_user_id}
                  onChange={(e) => setPedido({ ...pedido, target_user_id: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {equipe.map((membro) => (
                    <option key={membro.id} value={membro.id}>
                      {membro.full_name}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              <Campo rotulo="Nome do cliente">
                <Entrada
                  value={pedido.client_name}
                  onChange={(e) => setPedido({ ...pedido, client_name: e.target.value })}
                />
              </Campo>
              <Campo rotulo="WhatsApp do cliente">
                <Entrada
                  value={pedido.client_whatsapp}
                  onChange={(e) => setPedido({ ...pedido, client_whatsapp: e.target.value })}
                />
              </Campo>
              <div className="flex items-end">
                <Botao tipo="submit">Gerar link</Botao>
              </div>
            </form>

            {link && (
              <div className="mt-4 rounded-md border border-border bg-muted px-3 py-2">
                <p className="text-xs text-muted-foreground">Link do cliente (válido por 30 dias)</p>
                <code className="mt-1 block break-all text-sm text-foreground">{link}</code>
              </div>
            )}
          </Cartao>
        )}

        <Cartao titulo="Avaliações">
          {avaliacoes === null ? (
            <Carregando />
          ) : avaliacoes.length === 0 ? (
            <EstadoVazio titulo="Nenhuma avaliação ainda" />
          ) : (
            <Tabela colunas={["Cliente", "WhatsApp", "Status", "Nota", "Enviada em"]}>
              {avaliacoes.map((avaliacao) => (
                <Linha key={avaliacao.id}>
                  <Celula className="font-medium">{avaliacao.client_name ?? "—"}</Celula>
                  <Celula className="font-mono text-xs">
                    {avaliacao.client_whatsapp ?? "—"}
                  </Celula>
                  <Celula>
                    <Selo
                      tom={
                        avaliacao.status === "submitted"
                          ? "sucesso"
                          : avaliacao.status === "expired"
                            ? "neutro"
                            : "alerta"
                      }
                    >
                      {avaliacao.status_exibicao}
                    </Selo>
                    {avaliacao.has_negative && (
                      <span className="ml-2">
                        <Selo tom="perigo">atenção</Selo>
                      </span>
                    )}
                  </Celula>
                  <Celula>{avaliacao.overall_rating ?? "—"}</Celula>
                  <Celula>{formatarDataHora(avaliacao.submitted_at)}</Celula>
                </Linha>
              ))}
            </Tabela>
          )}
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
