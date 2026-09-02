"use client";

/**
 * `AuthenticatedShell` — sidebar navy, header com sino e chip de usuário.
 *
 * O menu é montado a partir das claims que a API devolve em `/auth/me` e dos toggles de
 * `/settings`: papel, capacidades individuais e configuração global do escritório. É a
 * regra de PAR-05 vista do lado do front — a navegação **reflete** a autorização, não a
 * decide. Esconder um item aqui não protege nada; o servidor recusa de qualquer forma.
 *
 * O legado tinha rotas duplicadas por papel (`/gestor/inicio`, `/coordenador/inicio`,
 * `/admin/inicio`) com o mesmo conteúdo. Aqui a rota é uma só e o conteúdo se adapta
 * (DEV-005 / topology_decision: papel é autorização, nunca pasta).
 */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { temCapacidade, temPapel, toggleLigado, useSessao } from "@/lib/sessao";
import type { FeedNotificacoes } from "@/lib/tipos";

import { SeloDePapel } from "./ui";

type ItemDeMenu = {
  href: string;
  rotulo: string;
  visivel: boolean;
};

export function Shell({ children }: { children: React.ReactNode }) {
  const { usuario, configuracoes, sair, trocarContexto } = useSessao();
  const caminho = usePathname();
  const router = useRouter();
  const [naoLidas, setNaoLidas] = useState(0);

  useEffect(() => {
    if (!usuario) return;
    // O sino consulta a contagem uma vez por navegação — o legado fazia polling de
    // 30 segundos em todas as abas, o que era a maior fonte de requisições do sistema.
    api<FeedNotificacoes>("/notifications", { query: { unread: true } })
      .then((feed) => setNaoLidas(feed.unread_count))
      .catch(() => setNaoLidas(0));
  }, [usuario, caminho]);

  if (!usuario) return null;

  const podeRelatorios =
    temPapel(usuario, "admin", "rh") ||
    (temPapel(usuario, "gestor") && toggleLigado(configuracoes, "gestor_can_access_reports")) ||
    temCapacidade(usuario, "can_generate_reports");

  const itens: ItemDeMenu[] = [
    { href: "/", rotulo: "Início", visivel: true },
    { href: "/meus-feedbacks", rotulo: "Meus feedbacks", visivel: true },
    { href: "/minha-equipe", rotulo: "Minha equipe", visivel: temPapel(usuario, "admin", "rh", "gestor") || usuario.is_coordinator },
    { href: "/avaliacoes-clientes", rotulo: "Avaliações de clientes", visivel: true },
    { href: "/relatorios", rotulo: "Relatórios", visivel: podeRelatorios },
    { href: "/notificacoes", rotulo: "Notificações", visivel: true },
    { href: "/admin/usuarios", rotulo: "Usuários", visivel: temPapel(usuario, "admin", "rh") },
    { href: "/admin/ciclos", rotulo: "Ciclos", visivel: temPapel(usuario, "admin", "rh") },
    { href: "/admin/configuracoes", rotulo: "Configurações", visivel: temPapel(usuario, "admin", "rh") },
    { href: "/fale-conosco", rotulo: "Fale conosco", visivel: true },
  ];

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
        <div className="border-b border-sidebar-border px-5 py-5">
          <p className="text-sm font-semibold">
            {configuracoes.company_name ?? "A&S Feedback Hub"}
          </p>
          <p className="mt-0.5 text-xs text-sidebar-muted">Feedback 360 e clientes</p>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {itens
            .filter((item) => item.visivel)
            .map((item) => {
              const ativo = caminho === item.href || caminho.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={
                    "block rounded-md px-3 py-2 text-sm transition " +
                    (ativo
                      ? "bg-sidebar-primary font-medium text-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent")
                  }
                >
                  {item.rotulo}
                </Link>
              );
            })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <button
            type="button"
            onClick={async () => {
              await sair();
              router.push("/login");
            }}
            className="w-full rounded-md px-3 py-2 text-left text-sm hover:bg-sidebar-accent"
          >
            Sair
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-card px-6 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-card-foreground">
              {usuario.full_name}
            </p>
            {usuario.job_title && (
              <p className="truncate text-xs text-muted-foreground">{usuario.job_title}</p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/notificacoes"
              className="relative rounded-md px-3 py-1.5 text-sm text-foreground hover:bg-muted"
            >
              Notificações
              {naoLidas > 0 && (
                <span className="ml-2 inline-flex min-w-5 justify-center rounded-full bg-destructive px-1.5 text-xs font-semibold text-destructive-foreground">
                  {naoLidas}
                </span>
              )}
            </Link>

            {/* Troca de contexto: só desce na hierarquia, e o servidor confere de novo. */}
            {temPapel(usuario, "admin", "rh", "gestor") && (
              <select
                aria-label="Ver o sistema como"
                value={usuario.role}
                onChange={(evento) => void trocarContexto(evento.target.value)}
                className="rounded-md border border-input bg-card px-2 py-1.5 text-xs text-foreground"
              >
                {["admin", "rh", "gestor", "colaborador"].map((papel) => (
                  <option key={papel} value={papel}>
                    Ver como {papel}
                  </option>
                ))}
              </select>
            )}

            <SeloDePapel papel={usuario.role} coordenador={usuario.is_coordinator} />
          </div>
        </header>

        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
