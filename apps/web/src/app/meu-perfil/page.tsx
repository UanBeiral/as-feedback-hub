"use client";

/**
 * Meu Perfil — o que a própria pessoa pode mudar.
 *
 * Dados de contato e senha, e nada além. Papel, capacidades e coordenação não estão
 * aqui de propósito: se alguém pudesse mudar o próprio papel, a autorização inteira
 * viraria decoração. Quem muda isso é admin/RH, em Usuários.
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PaginaAutenticada } from "@/components/pagina";
import {
  Aviso,
  Botao,
  Campo,
  Cartao,
  Entrada,
  SeloDePapel,
} from "@/components/ui";
import { ApiError, api, apiVoid } from "@/lib/api";
import { useSessao } from "@/lib/sessao";

const CAPACIDADES: Record<string, string> = {
  can_request_client_feedback: "Pedir avaliação de cliente",
  can_view_feedback_answers: "Ver respostas de feedback",
  can_view_team_history: "Ver histórico da equipe",
  can_generate_reports: "Gerar relatórios",
  can_view_manager_dashboard: "Ver painel de gestor",
};

export default function MeuPerfil() {
  const { usuario, recarregar, sair } = useSessao();
  const router = useRouter();
  const [dados, setDados] = useState({ full_name: "", job_title: "", whatsapp: "" });
  const [senhas, setSenhas] = useState({ senha_atual: "", nova_senha: "" });
  const [mensagem, setMensagem] = useState<{ tom: "erro" | "sucesso"; texto: string } | null>(null);

  useEffect(() => {
    if (usuario) {
      setDados({
        full_name: usuario.full_name,
        job_title: usuario.job_title ?? "",
        whatsapp: "",
      });
    }
  }, [usuario]);

  async function salvarDados(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await api("/auth/me", {
        method: "PATCH",
        body: {
          full_name: dados.full_name,
          job_title: dados.job_title || null,
          whatsapp: dados.whatsapp || null,
        },
      });
      await recarregar();
      setMensagem({ tom: "sucesso", texto: "Perfil atualizado." });
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto: falha instanceof ApiError ? falha.message : "Não foi possível salvar.",
      });
    }
  }

  async function trocarSenha(evento: React.FormEvent) {
    evento.preventDefault();
    setMensagem(null);
    try {
      await apiVoid("/auth/me/password", { method: "POST", body: senhas });
      // Trocar a senha derruba todas as sessões, inclusive esta — é o comportamento
      // certo, e a tela leva a pessoa de volta ao login em vez de deixá-la clicando
      // em botões que respondem 401.
      await sair();
      router.replace("/login");
    } catch (falha) {
      setMensagem({
        tom: "erro",
        texto:
          falha instanceof ApiError && falha.status === 422
            ? "Senha atual incorreta, ou a nova é curta demais (mínimo 8 caracteres)."
            : "Não foi possível trocar a senha.",
      });
    }
  }

  const flags = usuario
    ? Object.entries(usuario.flags as unknown as Record<string, boolean>).filter(([, v]) => v)
    : [];

  return (
    <PaginaAutenticada titulo="Meu perfil" descricao="Seus dados de contato e sua senha.">
      <div className="space-y-6">
        {mensagem && <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso>}

        <Cartao titulo="Dados">
          <form onSubmit={salvarDados} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo rotulo="Nome completo" obrigatorio>
                <Entrada
                  required
                  value={dados.full_name}
                  onChange={(e) => setDados({ ...dados, full_name: e.target.value })}
                />
              </Campo>
              <Campo rotulo="Cargo">
                <Entrada
                  value={dados.job_title}
                  onChange={(e) => setDados({ ...dados, job_title: e.target.value })}
                />
              </Campo>
              <Campo rotulo="WhatsApp">
                <Entrada
                  value={dados.whatsapp}
                  onChange={(e) => setDados({ ...dados, whatsapp: e.target.value })}
                  placeholder="(11) 98765-4321"
                />
              </Campo>
              <Campo rotulo="E-mail" dica="Alterado apenas pela administração.">
                <Entrada value={usuario?.email ?? ""} disabled />
              </Campo>
            </div>
            <Botao tipo="submit">Salvar</Botao>
          </form>
        </Cartao>

        <Cartao
          titulo="Acesso"
          descricao="Definido pela administração — mostrado aqui para você saber o que pode fazer."
        >
          <div className="flex flex-wrap items-center gap-3">
            {usuario && (
              <SeloDePapel papel={usuario.role} coordenador={usuario.is_coordinator} />
            )}
            {flags.length === 0 ? (
              <span className="text-sm text-muted-foreground">
                Nenhuma capacidade adicional concedida.
              </span>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {flags.map(([chave]) => (
                  <li
                    key={chave}
                    className="rounded-full border border-border px-2.5 py-0.5 text-xs text-foreground"
                  >
                    {CAPACIDADES[chave] ?? chave}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Cartao>

        <Cartao
          titulo="Trocar senha"
          descricao="Trocar a senha encerra todas as sessões, inclusive esta."
        >
          <form onSubmit={trocarSenha} className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Senha atual" obrigatorio>
              <Entrada
                type="password"
                required
                autoComplete="current-password"
                value={senhas.senha_atual}
                onChange={(e) => setSenhas({ ...senhas, senha_atual: e.target.value })}
              />
            </Campo>
            <Campo rotulo="Nova senha" obrigatorio dica="Mínimo de 8 caracteres.">
              <Entrada
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={senhas.nova_senha}
                onChange={(e) => setSenhas({ ...senhas, nova_senha: e.target.value })}
              />
            </Campo>
            <div className="sm:col-span-2">
              <Botao tipo="submit" variante="secundario">
                Trocar senha e sair
              </Botao>
            </div>
          </form>
        </Cartao>
      </div>
    </PaginaAutenticada>
  );
}
