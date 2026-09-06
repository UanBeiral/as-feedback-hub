"use client";

/**
 * Login — a porta do app interno.
 *
 * O nome do escritório não aparece aqui, e é de propósito: quem ainda não entrou não tem
 * sessão, e o `company_name` vive atrás de autenticação. Estampar a marca exigiria abrir
 * um endpoint público só para dizer de quem é a instalação — informação que o legado
 * dava porque tinha um tenant só.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Aviso, Botao, Campo, Cartao, Entrada } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useSessao } from "@/lib/sessao";

export default function PaginaDeLogin() {
  const { entrar, usuario, carregando } = useSessao();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [verSenha, setVerSenha] = useState(false);
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
          <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">
            Plataforma de feedback interno
          </p>
        </div>

        <Cartao>
          <form onSubmit={enviar} className="space-y-4">
            <Campo rotulo="E-mail" obrigatorio>
              <Entrada
                type="email"
                value={email}
                placeholder="seu@email.com"
                autoComplete="username"
                required
                onChange={(evento) => setEmail(evento.target.value)}
              />
            </Campo>

            <Campo rotulo="Senha" obrigatorio>
              {/* O olho de revelar existia no legado e resolve um problema real: senha
                  digitada errada em teclado de celular é a primeira causa de "não
                  consigo entrar". O botão fica fora do fluxo de tabulação porque quem
                  navega por teclado está lendo o que digita de outro jeito. */}
              <span className="relative block">
                <Entrada
                  type={verSenha ? "text" : "password"}
                  value={senha}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  className="pr-11"
                  onChange={(evento) => setSenha(evento.target.value)}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setVerSenha((atual) => !atual)}
                  aria-label={verSenha ? "Ocultar senha" : "Mostrar senha"}
                  className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    className="h-4 w-4"
                    aria-hidden="true"
                  >
                    <path
                      d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"
                      strokeLinejoin="round"
                    />
                    <circle cx="12" cy="12" r="3" />
                    {!verSenha && <path d="m4 20 16-16" strokeLinecap="round" />}
                  </svg>
                </button>
              </span>
            </Campo>

            {erro && <Aviso tom="erro">{erro}</Aviso>}

            <Botao tipo="submit" desabilitado={enviando} className="w-full">
              {enviando ? "Entrando…" : "Entrar"}
            </Botao>
          </form>
        </Cartao>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          <Link
            href="/esqueci-senha"
            className="text-primary underline-offset-4 hover:underline"
          >
            Esqueci minha senha
          </Link>
        </p>
      </div>
    </main>
  );
}
