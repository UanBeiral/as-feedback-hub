# language: pt
# spec-id: PAR-05
# rastreabilidade: permissions.md (matriz RBAC + validação humana); target_business_rules.md BR-MIGRAR-013..017; AD-02/AD-10; R-04/R-09
# paradigma alvo: guards explícitos na API substituem RLS (BR-DESCARTAR-001); dimensão nova: isolamento multi-tenant

@paridade @critico
Funcionalidade: Autorização, escopo de equipe e isolamento de tenant

  @paridade @critico
  Cenário: Negar por padrão
    Dado um perfil com flag de capacidade ausente ou nula
    Quando o recurso controlado pela flag é requisitado diretamente na API
    Então o acesso é negado

  @paridade
  Cenário: Parâmetros de URL não ampliam escopo
    Dado um gestor autenticado com equipe própria
    Quando ele consulta o histórico passando o identificador de um membro de outra equipe
    Então a API nega ou retorna vazio, sem expor dados fora do escopo

  @paridade
  Cenário: Matriz RBAC por papel
    Dado a matriz papel × capacidade de permissions.md
    Quando cada papel chama cada endpoint administrativo, de gestão e de relatório
    Então apenas as combinações permitidas na matriz respondem com sucesso

  @paridade
  Cenário: Escopo do coordenador é a união deduplicada
    Dado um coordenador com subordinados diretos e membros associados, com sobreposição
    Quando a equipe coordenada é consultada
    Então cada perfil aparece uma única vez e nenhum perfil fora das duas fontes aparece

  @paridade
  Cenário: Flags de capacidade controlam acesso do colaborador
    Dado um colaborador com "can_generate_reports" falso
    Quando ele chama o endpoint de relatório de clientes
    Então a API nega e nenhum arquivo é gerado

  @isolamento @critico
  Cenário: Isolamento entre tenants
    Dado dois tenants com dados próprios
    Quando uma sessão do tenant A consulta qualquer recurso com identificadores do tenant B
    Então nenhum dado do tenant B é retornado, em nenhum endpoint

  @paridade
  Cenário: Papel ativo muda contexto sem ampliar autorização
    Dado um admin com papel ativo "gestor"
    Quando ele acessa recursos de gestor
    Então o escopo aplicado é o do contexto ativo e a autorização final é sempre revalidada no servidor
