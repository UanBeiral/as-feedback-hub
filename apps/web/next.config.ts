import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // A API é um serviço separado (AD-01). Em desenvolvimento o front fala com ela por
  // este proxy, o que evita CORS e faz o caminho ser o mesmo de produção, onde o Nginx
  // roteia /api para a API e o resto para o web (AD-06).
  //
  // Atenção: o `destination` é resolvido no `next build` e gravado no routes-manifest.
  // Mudar `API_ORIGIN` depois do build não tem efeito — por isso o Dockerfile o recebe
  // como build arg.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_ORIGIN ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default config;
