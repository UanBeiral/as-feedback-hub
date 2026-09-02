"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { Aviso, Botao, Campo, Cartao, Entrada } from "@/components/ui";

export default function PaginaDeLogin() {
  const { entrar, usuario, carregando } = useSessao();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!carregando && usuario) router.replace("/");
  }, [carregando, usuario, router]);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(email, senha);
      router.replace("/");
    } catch (falha) {
      // A API devolve a mesma mensagem para e-mail inexistente e senha errada, de
      // propósito. Repetir aqui o que ela disse mantém essa decisão de pé — inventar
      // "usuário não encontrado" no front desfaria a proteção do servidor.
      setErro(falha instanceof ApiError ? falha.message : "Não foi possível entrar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-foreground">A&amp;S Feedback Hub</h1>
          <p className="mt-1 text-sm text-muted-foreground">Entre para continuar</p>
        </div>

        <Cartao>
          <form onSubmit={enviar} className="space-y-4">
            <Campo rotulo="E-mail" obrigatorio>
              <Entrada
                type="email"
                value={email}
                autoComplete="username"
                required
                onChange={(evento) => setEmail(evento.target.value)}
              />
            </Campo>

            <Campo rotulo="Senha" obrigatorio>
              <Entrada
                type="password"
                value={senha}
                autoComplete="current-password"
                required
                onChange={(evento) => setSenha(evento.target.value)}
              />
            </Campo>

            {erro && <Aviso tom="erro">{erro}</Aviso>}

            <Botao tipo="submit" desabilitado={enviando} className="w-full">
              {enviando ? "Entrando…" : "Entrar"}
            </Botao>
          </form>
        </Cartao>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Esqueceu a senha? Fale com o administrador do escritório.
        </p>
      </div>
    </main>
  );
}
