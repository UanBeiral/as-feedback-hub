import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { ProvedorDeSessao } from "@/lib/sessao";

import "./globals.css";

/**
 * Inter é a fonte do design system (`docs/reversa/design-system/typography.md`).
 *
 * Servida pelo `next/font` e não por `<link>` para o Google Fonts: a fonte é embutida
 * no build, o que tira uma requisição a terceiro do carregamento de toda página e
 * elimina o pulo de layout enquanto ela baixa. Também evita mandar o IP de quem usa o
 * sistema para fora, o que importa num produto que lida com feedback nominal.
 */
const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
  variable: "--fonte-inter",
});

export const metadata: Metadata = {
  title: "A&S Feedback Hub",
  description: "Feedback 360 e avaliação de clientes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body>
        <ProvedorDeSessao>{children}</ProvedorDeSessao>
      </body>
    </html>
  );
}
