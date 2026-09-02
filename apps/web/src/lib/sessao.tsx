"use client";

/**
 * Contexto de sessão do front.
 *
 * A regra que este arquivo materializa é a de BR-MIGRAR-016 e PAR-05: **a navegação
 * reflete papel e capacidades, mas nunca decide autorização**. Esconder um item de menu
 * é conveniência visual; quem recusa é o servidor. No legado, a rota de relatórios
 * sumia do menu quando o toggle estava desligado — e continuava respondendo para quem
 * digitasse a URL.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, ApiError, sessao } from "./api";
import type { Configuracao, ParDeTokens, UsuarioAtual } from "./tipos";

type EstadoDaSessao = {
  usuario: UsuarioAtual | null;
  configuracoes: Record<string, string | null>;
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
  trocarContexto: (papel: string) => Promise<void>;
  recarregar: () => Promise<void>;
};

const Contexto = createContext<EstadoDaSessao | null>(null);

export function ProvedorDeSessao({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioAtual | null>(null);
  const [configuracoes, setConfiguracoes] = useState<Record<string, string | null>>({});
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    try {
      const [eu, settings] = await Promise.all([
        api<UsuarioAtual>("/auth/me"),
        api<Configuracao[]>("/settings"),
      ]);
      setUsuario(eu);
      setConfiguracoes(Object.fromEntries(settings.map((s) => [s.key, s.value])));
    } catch (erro) {
      // 401 aqui é o caso normal de quem ainda não entrou; qualquer outro erro também
      // resulta em "sem sessão", porque não há tela útil sem `/auth/me`.
      if (!(erro instanceof ApiError)) throw erro;
      setUsuario(null);
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    // Sem refresh guardado não há o que restaurar: evita um 401 garantido no boot.
    if (!sessao.refresh) {
      setCarregando(false);
      return;
    }
    void carregar();
  }, [carregar]);

  const entrar = useCallback(
    async (email: string, senha: string) => {
      const par = await api<ParDeTokens>("/auth/login", {
        method: "POST",
        body: { email, password: senha },
      });
      sessao.definir(par.access_token, par.refresh_token);
      await carregar();
    },
    [carregar],
  );

  const sair = useCallback(async () => {
    const refresh = sessao.refresh;
    try {
      if (refresh) {
        await api("/auth/logout", { method: "POST", body: { refresh_token: refresh } });
      }
    } finally {
      // Falha no logout não pode prender a pessoa dentro do app: o refresh some daqui
      // de qualquer jeito, e o token continua revogável pelo servidor depois.
      sessao.limpar();
      setUsuario(null);
    }
  }, []);

  const trocarContexto = useCallback(
    async (papel: string) => {
      const resposta = await api<{ access_token: string }>("/auth/active-role", {
        method: "POST",
        body: { active_role: papel },
      });
      sessao.definirAccess(resposta.access_token);
      await carregar();
    },
    [carregar],
  );

  const valor = useMemo(
    () => ({
      usuario,
      configuracoes,
      carregando,
      entrar,
      sair,
      trocarContexto,
      recarregar: carregar,
    }),
    [usuario, configuracoes, carregando, entrar, sair, trocarContexto, carregar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): EstadoDaSessao {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useSessao precisa estar dentro de ProvedorDeSessao");
  return contexto;
}

/** Atalho para quem só precisa do usuário e já sabe que a tela é autenticada. */
export function useUsuario(): UsuarioAtual {
  const { usuario } = useSessao();
  if (!usuario) throw new Error("tela autenticada renderizada sem usuário");
  return usuario;
}

export function temPapel(usuario: UsuarioAtual | null, ...papeis: string[]): boolean {
  return usuario !== null && papeis.includes(usuario.role);
}

export function temCapacidade(usuario: UsuarioAtual | null, flag: string): boolean {
  if (!usuario) return false;
  return Boolean((usuario.flags as unknown as Record<string, boolean>)[flag]);
}

/** Toggle global do escritório (BR-MIGRAR-027). Ausente vale `false`. */
export function toggleLigado(
  configuracoes: Record<string, string | null>,
  chave: string,
): boolean {
  return configuracoes[chave] === "true";
}
