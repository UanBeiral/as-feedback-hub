"use client";

/**
 * Casca de página autenticada.
 *
 * Concentra três coisas que toda tela repete e que ninguém deveria reescrever: esperar
 * a sessão carregar, mandar para o login quem não tem sessão, e desenhar o cabeçalho.
 *
 * O redirecionamento aqui é **navegação**, não proteção: quem chamar a API sem sessão
 * recebe 401 do servidor de qualquer jeito. É a diferença que o legado confundia, com
 * `ProtectedRoute` sendo a única barreira de várias telas.
 */

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSessao } from "@/lib/sessao";

import { Shell } from "./shell";
import { Carregando } from "./ui";

export function PaginaAutenticada({
  titulo,
  descricao,
  acao,
  children,
}: {
  titulo: string;
  descricao?: string;
  acao?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { usuario, carregando } = useSessao();
  const router = useRouter();

  useEffect(() => {
    if (!carregando && !usuario) router.replace("/login");
  }, [carregando, usuario, router]);

  if (carregando) return <Carregando />;
  if (!usuario) return null;

  return (
    <Shell>
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-foreground">{titulo}</h1>
            {descricao && <p className="mt-1 text-sm text-muted-foreground">{descricao}</p>}
          </div>
          {acao}
        </header>
        {children}
      </div>
    </Shell>
  );
}
