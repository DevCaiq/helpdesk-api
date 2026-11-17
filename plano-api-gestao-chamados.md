# API REST de Gestão de Chamados (Help Desk) — Plano Completo do Projeto

> **Atualização em 2026-11-16:** este é o plano original. Em caso de divergência,
> prevalecem [as decisões confirmadas](docs/decisoes-iniciais.md) e o
> [desenho técnico aprovado](docs/desenho-tecnico.md). O andamento da primeira
> etapa está no [plano da fundação](docs/superpowers/plans/2026-11-16-fundacao.md).

> Projeto de portfólio back-end • Python + Django REST Framework • 100% baseado em ferramentas e serviços gratuitos

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Stack tecnológica (gratuita)](#2-stack-tecnológica-gratuita)
3. [Arquitetura](#3-arquitetura)
4. [Modelagem de dados](#4-modelagem-de-dados)
5. [Regras de negócio](#5-regras-de-negócio)
6. [Endpoints da API](#6-endpoints-da-api)
7. [Plano de execução por fases](#7-plano-de-execução-por-fases)
8. [Estratégia de testes](#8-estratégia-de-testes)
9. [CI/CD com GitHub Actions](#9-cicd-com-github-actions)
10. [Docker e infraestrutura](#10-docker-e-infraestrutura)
11. [Segurança](#11-segurança)
12. [Deploy gratuito](#12-deploy-gratuito)
13. [Documentação e portfólio](#13-documentação-e-portfólio)
14. [Definition of Done (ponto final)](#14-definition-of-done-ponto-final)
15. [Cronograma](#15-cronograma)
16. [Riscos e evoluções futuras](#16-riscos-e-evoluções-futuras)

---

## 1. Visão geral

### 1.1 Problema
Equipes de suporte precisam registrar, priorizar, atribuir e acompanhar chamados, garantindo que os prazos de atendimento (SLA) sejam cumpridos e que problemas complexos sejam escalados do Nível 1 (N1) para o Nível 2 (N2), com rastreabilidade completa.

### 1.2 Objetivo
Construir uma **API REST** que cubra o ciclo de vida completo de um chamado, com:

- Autenticação **JWT** e três perfis: **Solicitante**, **Analista** e **Gestor**
- **SLA** com prazos por prioridade, pausa e indicadores de risco
- **Escalonamento N1 → N2** (manual e automático)
- **Histórico de status** imutável e **logs de auditoria**
- **Testes automatizados**, documentação **Swagger/OpenAPI** e **Docker**

### 1.3 Escopo

| Dentro do escopo | Fora do escopo (nesta versão) |
|---|---|
| API REST completa | Front-end / interface web |
| Autenticação e perfis | Chat em tempo real |
| SLA, prioridades e escalonamento | App mobile |
| Histórico e auditoria | Horário comercial/feriados no SLA (evolução) |
| Testes, Swagger, Docker, CI | Integração com WhatsApp (evolução) |
| Deploy gratuito com dados de demonstração | Multi-tenant (evolução) |

### 1.4 Perfis de usuário

| Perfil | Descrição |
|---|---|
| **Solicitante** | Abre chamados, acompanha e comenta nos seus, reabre dentro do prazo |
| **Analista (N1/N2)** | Atende a fila do seu nível, comenta (inclusive notas internas), muda status, escala |
| **Gestor** | Visão total, reatribui, gerencia categorias e políticas de SLA, vê métricas e auditoria |

---

## 2. Stack tecnológica (gratuita)

### 2.1 Núcleo

| Camada | Tecnologia | Por quê | Custo |
|---|---|---|---|
| Linguagem | **Python 3.12** | Sua base de experiência | Grátis |
| Framework | **Django 5.x** | ORM, admin, migrations, segurança | Grátis |
| API | **Django REST Framework** | Serializers, viewsets, permissões | Grátis |
| Autenticação | **djangorestframework-simplejwt** | JWT com refresh e blacklist | Grátis |
| Documentação | **drf-spectacular** | OpenAPI 3 + Swagger UI + ReDoc | Grátis |
| Filtros | **django-filter** | Filtros declarativos nas listagens | Grátis |
| Configuração | **django-environ** | Variáveis de ambiente | Grátis |
| CORS | **django-cors-headers** | Controle de origens | Grátis |
| Banco de dados | **PostgreSQL 16** | Robusto, JSON, índices avançados | Grátis |
| Servidor WSGI | **Gunicorn** + **WhiteNoise** (estáticos) | Produção simples | Grátis |

### 2.2 Qualidade e testes

| Ferramenta | Uso |
|---|---|
| **pytest** + **pytest-django** | Executor de testes |
| **factory_boy** + **Faker** | Dados de teste |
| **freezegun** (ou `time-machine`) | Congelar o tempo (essencial para SLA) |
| **pytest-cov** | Cobertura |
| **ruff** | Lint + formatação (substitui flake8, isort e black) |
| **mypy** + **django-stubs** (opcional) | Tipagem estática |
| **pre-commit** | Hooks antes do commit |
| **bandit** / **pip-audit** | Análise de segurança e dependências |

### 2.3 Tarefas assíncronas e agendamento

Duas opções, ambas gratuitas. **Recomendação: Opção A** para começar.

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A) Management command + agendador** | Comando `manage.py verificar_sla` executado a cada 5 min (cron local no Docker, ou GitHub Actions agendado chamando um endpoint protegido) | Simples, sem infraestrutura extra | Menos "enterprise" |
| **B) Celery + Redis** | Worker + Beat + Redis (Docker local; Upstash Redis free no deploy) | Padrão de mercado, ótimo para o portfólio | Mais peças para manter |

> Dica: implemente a lógica de SLA como **serviço puro** (função em `services.py`). Assim ela pode ser chamada tanto por um comando quanto por uma task Celery, e você migra de A para B sem reescrever nada.

### 2.4 Infra, DevOps e ferramentas de apoio

| Finalidade | Ferramenta | Observação |
|---|---|---|
| Versionamento | **Git** + **GitHub** | Repositório público |
| CI/CD | **GitHub Actions** | Gratuito em repositórios públicos |
| Containers | **Docker** + **Docker Compose** | Docker Engine é gratuito; Docker Desktop é gratuito para uso pessoal e pequenas empresas |
| Editor | **VS Code** (ou PyCharm Community) | Gratuito |
| Gerenciador de pacotes | **uv** (ou Poetry / pip-tools) | `uv` é rápido e simples |
| Cliente de API | **Bruno**, **Insomnia** ou **Postman** (plano free) | Bruno é open source e guarda coleções em arquivos |
| Cliente de banco | **DBeaver Community** ou **pgAdmin** | Gratuitos |
| Diagramas | **Mermaid** (no próprio Markdown), **dbdiagram.io**, **draw.io** | Gratuitos |
| E-mail em dev | **Mailpit** (container) | Captura e-mails localmente |
| E-mail em produção | **Brevo** ou **Resend** (planos gratuitos) | Confira os limites atuais |
| Cobertura | **Codecov** (grátis para repositórios públicos) ou relatório no próprio CI | Badge no README |
| Monitoramento de erros | **Sentry** (plano free) | Opcional |
| Hospedagem da API | **Render** (web service gratuito) | Entra em repouso após inatividade |
| Banco em produção | **Neon** ou **Supabase** (Postgres gratuito) | Verifique limites e expiração do plano |
| Redis em produção (se usar Celery) | **Upstash** (plano free) | Opcional |

> **Atenção:** planos gratuitos mudam com frequência (limites, expiração, hibernação). Antes de escolher o provedor de deploy, confira os termos atuais na página oficial de cada serviço. A arquitetura com Docker deixa o projeto portátil entre eles.

---

## 3. Arquitetura

### 3.1 Princípios
- **Camada de serviços:** regras de negócio ficam em `services.py`, nunca em views ou serializers.
- **Selectors:** consultas complexas e de visibilidade ficam em `selectors.py`.
- **Views finas:** só validam entrada, chamam serviços e serializam a saída.
- **Imutabilidade:** histórico e auditoria só permitem inserção.
- **Transações:** toda operação que altera mais de uma tabela roda em `transaction.atomic()`.
- **Configuração por ambiente:** nada de segredo no código.

### 3.2 Diagrama de componentes

```mermaid
flowchart LR
    C[Cliente / Swagger / Bruno] -->|HTTPS + JWT| API[Django + DRF]
    API --> SVC[Services / Regras de negócio]
    SVC --> DB[(PostgreSQL)]
    SVC --> AUD[Auditoria / Histórico]
    JOB[Job de SLA<br/>command ou Celery] --> SVC
    SVC -->|e-mail| MAIL[SMTP / Mailpit / Brevo]
```

### 3.3 Estrutura de pastas

```
helpdesk-api/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── prod.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/            # paginação, exceções, permissões base, utilitários
│   ├── usuarios/        # custom user, auth, perfis
│   ├── chamados/        # models, serializers, views, services, selectors, filters
│   ├── sla/             # políticas, cálculo, job de verificação
│   ├── auditoria/       # logs de auditoria
│   └── metricas/        # endpoints de indicadores
├── tests/
│   ├── factories.py
│   ├── unit/
│   ├── api/
│   └── e2e/
├── docs/
│   ├── escopo.md
│   ├── adr/
│   ├── er.md
│   ├── estados.md
│   └── openapi.yaml
├── docker/
│   └── entrypoint.sh
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── .pre-commit-config.yaml
├── Makefile
└── README.md
```

---

## 4. Modelagem de dados

### 4.1 Diagrama ER

```mermaid
erDiagram
    USUARIO ||--o{ CHAMADO : "solicita"
    USUARIO ||--o{ CHAMADO : "atende"
    CATEGORIA ||--o{ CHAMADO : "classifica"
    POLITICA_SLA ||--o{ CHAMADO : "rege"
    CHAMADO ||--o{ COMENTARIO : "tem"
    CHAMADO ||--o{ HISTORICO_STATUS : "registra"
    CHAMADO ||--o{ PAUSA_SLA : "possui"
    USUARIO ||--o{ LOG_AUDITORIA : "gera"

    USUARIO {
        int id PK
        string email UK
        string nome
        string perfil "SOLICITANTE|ANALISTA|GESTOR"
        string nivel "N1|N2 (analista)"
        bool ativo
    }
    CATEGORIA {
        int id PK
        string nome UK
        bool ativa
    }
    POLITICA_SLA {
        int id PK
        string prioridade UK
        int minutos_primeira_resposta
        int minutos_resolucao
    }
    CHAMADO {
        int id PK
        string titulo
        text descricao
        string status
        string prioridade
        string nivel_atual "N1|N2"
        int solicitante_id FK
        int responsavel_id FK
        int categoria_id FK
        datetime aberto_em
        datetime primeira_resposta_em
        datetime resolvido_em
        datetime fechado_em
        datetime prazo_primeira_resposta
        datetime prazo_resolucao
        string sla_status
    }
    COMENTARIO {
        int id PK
        int chamado_id FK
        int autor_id FK
        text texto
        bool interno
        datetime criado_em
    }
    HISTORICO_STATUS {
        int id PK
        int chamado_id FK
        string status_anterior
        string status_novo
        int autor_id FK
        text motivo
        datetime criado_em
    }
    PAUSA_SLA {
        int id PK
        int chamado_id FK
        datetime inicio
        datetime fim
    }
    LOG_AUDITORIA {
        int id PK
        int ator_id FK
        string acao
        string entidade
        string entidade_id
        json antes
        json depois
        string ip
        string user_agent
        datetime criado_em
    }
```

### 4.2 Máquina de estados do chamado

```mermaid
stateDiagram-v2
    [*] --> ABERTO
    ABERTO --> EM_ATENDIMENTO: assumir
    ABERTO --> CANCELADO: cancelar
    EM_ATENDIMENTO --> AGUARDANDO_SOLICITANTE: pedir informação
    AGUARDANDO_SOLICITANTE --> EM_ATENDIMENTO: solicitante responde
    EM_ATENDIMENTO --> RESOLVIDO: resolver
    RESOLVIDO --> FECHADO: confirmação / prazo
    RESOLVIDO --> REABERTO: solicitante reabre
    REABERTO --> EM_ATENDIMENTO: assumir
    FECHADO --> [*]
    CANCELADO --> [*]
```

**Tabela de transições permitidas**

| De | Para | Quem pode |
|---|---|---|
| ABERTO | EM_ATENDIMENTO | Analista (do nível do chamado), Gestor |
| ABERTO | CANCELADO | Solicitante (dono), Gestor |
| EM_ATENDIMENTO | AGUARDANDO_SOLICITANTE | Analista responsável, Gestor |
| AGUARDANDO_SOLICITANTE | EM_ATENDIMENTO | Solicitante (ao comentar), Analista, Gestor |
| EM_ATENDIMENTO | RESOLVIDO | Analista responsável, Gestor |
| RESOLVIDO | FECHADO | Solicitante (confirma), Sistema (após X dias sem reabertura), Gestor |
| RESOLVIDO | REABERTO | Solicitante (dentro de N dias) |
| REABERTO | EM_ATENDIMENTO | Analista, Gestor |

### 4.3 Matriz de prioridade (impacto × urgência)

| Impacto \ Urgência | Alta | Média | Baixa |
|---|---|---|---|
| **Alto** | CRÍTICA | ALTA | MÉDIA |
| **Médio** | ALTA | MÉDIA | BAIXA |
| **Baixo** | MÉDIA | BAIXA | BAIXA |

### 4.4 Política de SLA (valores iniciais, editáveis pelo Gestor)

| Prioridade | 1ª resposta | Resolução |
|---|---|---|
| CRÍTICA | 15 min | 4 h |
| ALTA | 1 h | 8 h |
| MÉDIA | 4 h | 24 h |
| BAIXA | 8 h | 72 h |

---

## 5. Regras de negócio

### 5.1 Abertura de chamado
1. Solicitante informa título, descrição, categoria, impacto e urgência.
2. O sistema calcula a **prioridade** pela matriz.
3. O sistema vincula a **política de SLA** e calcula `prazo_primeira_resposta` e `prazo_resolucao`.
4. O chamado nasce `ABERTO`, nível `N1`, sem responsável.
5. São gravados o histórico inicial e o log de auditoria.

### 5.2 SLA
- O relógio começa na **abertura**.
- **Pausa** em `AGUARDANDO_SOLICITANTE` (cria um registro em `PAUSA_SLA`). Ao retomar, fecha a pausa e **empurra os prazos** pelo tempo pausado.
- `primeira_resposta_em` é preenchido no primeiro comentário **público** de um analista ou na ação "assumir" (defina e documente qual).
- **Indicador `sla_status`:**
  - `NO_PRAZO`: consumido < 80%
  - `EM_RISCO`: consumido ≥ 80% e < 100%
  - `VENCIDO`: prazo ultrapassado sem resolução
  - `CUMPRIDO` / `VIOLADO`: estado final, calculado no `RESOLVIDO`
- Primeira versão: SLA em **tempo corrido (24x7)**. Horário comercial é evolução.

### 5.3 Escalonamento N1 → N2
- **Manual:** analista N1 chama `escalar`, com **justificativa obrigatória**. O chamado vai para `nivel_atual = N2`, fica sem responsável e volta à fila do N2.
- **Automático** (job periódico), quando:
  - o chamado é `CRÍTICA` e não foi assumido em X minutos; ou
  - o `sla_status` vira `EM_RISCO` no N1.
- A escalada automática é **idempotente**: um chamado só escala uma vez por motivo.
- Toda escalada gera histórico, auditoria e (opcional) notificação.

### 5.4 Visibilidade
- **Solicitante:** apenas chamados em que é o solicitante; **não** vê comentários internos.
- **Analista:** fila do seu nível + chamados atribuídos a ele.
- **Gestor:** todos.

### 5.5 Histórico e auditoria
- **Histórico de status:** toda mudança de status, imutável, com autor e motivo.
- **Auditoria:** login (sucesso/falha), criação/edição de entidades, mudança de perfil, reatribuição, escalada, alteração de SLA e prioridade. Guarda ator, ação, entidade, valores antes/depois, IP e user agent. **Nunca** grava senhas ou tokens.

### 5.6 Matriz de permissões (resumo)

| Ação | Solicitante | Analista | Gestor |
|---|:-:|:-:|:-:|
| Abrir chamado | ✅ | ✅ | ✅ |
| Ver chamados | só os seus | fila do nível | todos |
| Comentar público | ✅ (nos seus) | ✅ | ✅ |
| Comentar interno | ❌ | ✅ | ✅ |
| Assumir | ❌ | ✅ | ✅ |
| Mudar status | só cancelar/reabrir | ✅ | ✅ |
| Escalar | ❌ | ✅ | ✅ |
| Reatribuir | ❌ | ❌ | ✅ |
| Gerenciar categorias/SLA | ❌ | ❌ | ✅ |
| Ver métricas | ❌ | ❌ | ✅ |
| Ver auditoria | ❌ | ❌ | ✅ |
| Criar analista/gestor | ❌ | ❌ | ✅ |

---

## 6. Endpoints da API

Base: `/api/v1/`

### 6.1 Autenticação e usuários

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| POST | `/auth/login/` | Obtém access + refresh | Público |
| POST | `/auth/refresh/` | Renova access (com rotação) | Público |
| POST | `/auth/logout/` | Invalida refresh (blacklist) | Autenticado |
| POST | `/usuarios/` | Auto-cadastro de solicitante | Público |
| POST | `/usuarios/staff/` | Cria analista/gestor | Gestor |
| GET | `/usuarios/me/` | Dados do usuário logado | Autenticado |
| GET | `/usuarios/` | Lista usuários | Gestor |

### 6.2 Chamados

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| POST | `/chamados/` | Abre chamado | Autenticado |
| GET | `/chamados/` | Lista (filtros, busca, ordenação, paginação) | Conforme visibilidade |
| GET | `/chamados/{id}/` | Detalhe | Conforme visibilidade |
| PATCH | `/chamados/{id}/` | Edita título/descrição/categoria (regras por perfil) | Dono/Analista/Gestor |
| POST | `/chamados/{id}/assumir/` | Analista assume | Analista, Gestor |
| POST | `/chamados/{id}/transicionar/` | Muda status (`status` + `motivo`) | Conforme tabela |
| POST | `/chamados/{id}/escalar/` | Escala N1 → N2 (`justificativa`) | Analista, Gestor |
| POST | `/chamados/{id}/reatribuir/` | Troca responsável | Gestor |
| POST | `/chamados/{id}/reabrir/` | Reabre chamado resolvido | Solicitante, Gestor |
| GET | `/chamados/{id}/historico/` | Histórico de status | Conforme visibilidade |
| GET/POST | `/chamados/{id}/comentarios/` | Lista/cria comentários | Conforme visibilidade |

**Filtros da listagem:** `status`, `prioridade`, `categoria`, `responsavel`, `solicitante`, `nivel_atual`, `sla_status`, `aberto_em_de`, `aberto_em_ate`, `search` (título/descrição), `ordering`.

### 6.3 Administração e gestão

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| CRUD | `/categorias/` | Categorias | Leitura: autenticado • Escrita: Gestor |
| GET/PUT | `/sla/politicas/` | Políticas de SLA | Gestor |
| GET | `/metricas/sla/` | Indicadores de SLA | Gestor |
| GET | `/metricas/volume/` | Volume por status/categoria/nível | Gestor |
| GET | `/auditoria/` | Logs de auditoria (filtros) | Gestor |
| GET | `/health/` | Liveness | Público |
| GET | `/ready/` | Readiness (testa banco) | Público |

### 6.4 Padrão de erro

```json
{
  "error": {
    "code": "transicao_invalida",
    "message": "Não é possível mover de RESOLVIDO para EM_ATENDIMENTO.",
    "details": {"status_atual": "RESOLVIDO", "status_solicitado": "EM_ATENDIMENTO"}
  }
}
```

| HTTP | Uso |
|---|---|
| 400 | Dados inválidos |
| 401 | Não autenticado / token inválido |
| 403 | Sem permissão para a ação |
| 404 | Não encontrado (ou fora da visibilidade) |
| 409 | Conflito de estado (transição inválida) |
| 429 | Limite de requisições |

---

## 7. Plano de execução por fases

> Cada fase tem **tarefas**, **entregáveis** e um **critério de pronto**. Só avance quando o critério for atendido. **Escreva os testes junto com cada fase.**

### Fase 0 — Preparação e escopo (1–2 dias)

**Tarefas**
- [ ] Criar repositório no GitHub (público) com README inicial e licença MIT
- [ ] Escrever `docs/escopo.md` (problema, perfis, dentro/fora do escopo)
- [ ] Escrever ADRs curtos: DRF, JWT, PostgreSQL, camada de serviços, estratégia de job de SLA
- [ ] Definir convenção de commits (Conventional Commits) e branches (`main` + `feature/*`)
- [ ] Instalar: Python 3.12, Git, Docker, VS Code, uv

**Entregáveis:** repositório criado, `escopo.md`, `docs/adr/`.
**Pronto quando:** o escopo está escrito e as decisões técnicas principais estão registradas.

### Fase 1 — Modelagem e regras (2–3 dias)

**Tarefas**
- [ ] Finalizar ER, máquina de estados, matriz de prioridade e de permissões (use as da seção 4 e 5)
- [ ] Decidir e documentar: o que conta como "primeira resposta", prazo para reabrir, prazo de fechamento automático
- [ ] Definir catálogo de **eventos de auditoria**
- [ ] Definir os códigos de erro do padrão de resposta

**Entregáveis:** `docs/er.md`, `docs/estados.md`, `docs/regras.md`.
**Pronto quando:** não há ambiguidade nas regras de SLA, escalonamento e permissões.

### Fase 2 — Estrutura do projeto e ambiente (1–2 dias)

**Tarefas**
- [ ] Criar projeto Django com a estrutura da seção 3.3
- [ ] Configurar `settings` por ambiente + `django-environ` + `.env.example`
- [ ] Configurar `ruff`, `pre-commit` e `pytest` (com `pytest-django`)
- [ ] Criar `Dockerfile` e `docker-compose.yml` (api + db + mailpit)
- [ ] Criar `Makefile` com atalhos (`make up`, `make test`, `make lint`, `make migrate`)
- [ ] Implementar `/health/` e `/ready/`
- [ ] Criar o workflow inicial do GitHub Actions (lint + testes)

**Pronto quando:** `docker compose up` sobe a API e o banco, `/health/` retorna 200 e o CI roda verde.

### Fase 3 — Autenticação e usuários (2–3 dias)

**Tarefas**
- [ ] Custom User (`AbstractUser`, login por e-mail) **antes da primeira migration**
- [ ] Campos `perfil` e `nivel`, com validação (nível só para analista)
- [ ] Configurar `simplejwt`: access 15 min, refresh 7 dias, rotação + blacklist
- [ ] Endpoints de login, refresh, logout, cadastro, `me`, criação de staff
- [ ] Permissões reutilizáveis: `IsSolicitante`, `IsAnalista`, `IsGestor`, `IsOwnerOrStaff`
- [ ] Throttling de login e validadores de senha
- [ ] Auditar login (sucesso e falha)
- [ ] Testes: fluxo de auth completo + 403/401 por perfil

**Pronto quando:** os 3 perfis autenticam, renovam e invalidam token, e acessos indevidos retornam 401/403 (com testes).

### Fase 4 — Categorias e núcleo de chamados (4–5 dias)

**Tarefas**
- [ ] CRUD de categorias (escrita só Gestor)
- [ ] Models `Chamado` e `Comentario` + migrations + índices (`status`, `prioridade`, `responsavel`, `solicitante`, `prazo_resolucao`)
- [ ] `selectors.py` com visibilidade por perfil
- [ ] `services.py`: `abrir_chamado`, `assumir_chamado`, `transicionar_chamado`, `reatribuir_chamado`, `reabrir_chamado`, `comentar`
- [ ] Máquina de estados como estrutura de dados (dicionário de transições + perfis permitidos)
- [ ] Endpoints da seção 6.2 com filtros, busca, ordenação e paginação
- [ ] Comentários internos ocultos ao solicitante
- [ ] Handler global de exceções com o padrão de erro
- [ ] Testes: ciclo de vida completo, transições válidas e inválidas, visibilidade

**Pronto quando:** o ciclo abrir → assumir → comentar → resolver → fechar → reabrir funciona via API, e transições inválidas retornam 409 com mensagem clara.

### Fase 5 — Histórico e auditoria (2–3 dias)

**Tarefas**
- [ ] Model `HistoricoStatus` (somente inserção; bloquear `update`/`delete` no model e no admin)
- [ ] Registro automático no serviço de transição
- [ ] Model `LogAuditoria` + serviço `registrar_auditoria()` com ator, IP e user agent (middleware para capturar a requisição)
- [ ] Máscara de dados sensíveis
- [ ] Endpoints `/chamados/{id}/historico/` e `/auditoria/` (filtros por ator, ação, entidade, período)
- [ ] Testes: cada ação auditada gera registro; registros não podem ser alterados

**Pronto quando:** toda ação do catálogo gera registro correto e nenhum registro é editável via API.

### Fase 6 — SLA, prioridade e escalonamento (3–4 dias)

**Tarefas**
- [ ] Models `PoliticaSLA` e `PausaSLA` + seed com os valores padrão
- [ ] Serviço `calcular_prioridade(impacto, urgencia)`
- [ ] Serviço `aplicar_sla(chamado)`: define prazos na abertura e recalcula na troca de prioridade
- [ ] Pausa e retomada automáticas conforme o status
- [ ] Cálculo de `sla_status` e `percentual_consumido`
- [ ] Serviço `escalar_chamado(chamado, motivo, ator)` (manual) e `escalar_automaticamente()`
- [ ] Management command `verificar_sla` (idempotente), pronto para ser chamado por agendador ou Celery
- [ ] Endpoints de métricas: `/metricas/sla/` e `/metricas/volume/`
- [ ] Testes com **freezegun**: prazos, pausa, EM_RISCO, VENCIDO, escalada única, métricas

**Pronto quando:** os testes comprovam cálculo correto de prazos, pausa/retomada, mudança de `sla_status` nos instantes certos e escalada automática idempotente.

### Fase 7 — Notificações (opcional, 1–2 dias)

**Tarefas**
- [ ] Eventos: chamado aberto, atribuído, status alterado, escalado, SLA em risco
- [ ] E-mail via SMTP (Mailpit em dev; Brevo/Resend em produção)
- [ ] Envio assíncrono (Celery) **ou** via `transaction.on_commit` com tratamento de falha
- [ ] Teste: falha de envio não derruba a requisição

**Pronto quando:** os eventos disparam e-mails e uma falha de envio é apenas registrada em log.

### Fase 8 — Consolidação de testes (3–4 dias)

**Tarefas**
- [ ] Revisar a **pirâmide de testes** (unitários > API > e2e)
- [ ] Testes parametrizados da **matriz de permissões** (perfil × endpoint)
- [ ] Testes de regressão para bugs encontrados
- [ ] Medir cobertura e preencher lacunas
- [ ] Rodar `bandit` e `pip-audit` no CI

**Metas:** cobertura **≥ 85% global** e **≥ 95%** em SLA, estados e permissões.
**Pronto quando:** a suíte é determinística, passa no CI e atinge as metas.

### Fase 9 — Documentação OpenAPI/Swagger (1–2 dias)

**Tarefas**
- [ ] Configurar `drf-spectacular`: `/api/schema/`, `/api/docs/` (Swagger), `/api/redoc/`
- [ ] Anotar com `@extend_schema`: descrições, exemplos, códigos de erro, parâmetros de filtro, tags
- [ ] Configurar o esquema de segurança JWT (botão "Authorize")
- [ ] Validar o schema no CI: `python manage.py spectacular --validate --fail-on-warn`
- [ ] Exportar `docs/openapi.yaml` e criar coleção Bruno/Postman

**Pronto quando:** é possível autenticar e executar o fluxo completo só pelo Swagger, e o schema valida sem warnings.

### Fase 10 — Docker, performance e produção (2–3 dias)

**Tarefas**
- [ ] `Dockerfile` multi-stage, imagem slim, usuário não root, `gunicorn`
- [ ] `docker-compose.yml` (dev) e `docker-compose.prod.yml`, com healthchecks
- [ ] `entrypoint.sh`: aguarda o banco, roda migrations e `collectstatic`
- [ ] Revisar queries: `select_related`/`prefetch_related`, índices; checar N+1
- [ ] Comando `seed_demo`: usuários dos 3 perfis, categorias, políticas e chamados de exemplo
- [ ] Logs estruturados em JSON; opcionalmente Sentry
- [ ] `python manage.py check --deploy` sem alertas críticos

**Pronto quando:** em máquina limpa, `git clone` + `cp .env.example .env` + `docker compose up` entrega a API com dados demo em menos de 10 minutos.

### Fase 11 — Deploy, README e publicação (1–2 dias)

**Tarefas**
- [ ] Criar banco gratuito (Neon/Supabase) e web service (Render) — confira os planos atuais
- [ ] Configurar variáveis de ambiente e rodar `seed_demo` em produção
- [ ] Agendar a verificação de SLA (GitHub Actions `schedule` chamando um endpoint protegido por token, ou Celery se optou pela Opção B)
- [ ] README profissional (seção 13), badges, `CHANGELOG.md`, tag `v1.0.0`
- [ ] GIF/vídeo curto mostrando o fluxo no Swagger

**Pronto quando:** um recrutador entende o projeto em 2 minutos e consegue testá-lo no ar sem instalar nada.

---

## 8. Estratégia de testes

### 8.1 Pirâmide

| Nível | O que testa | Exemplos |
|---|---|---|
| **Unitário** | Funções puras e serviços | matriz de prioridade, cálculo de prazo, máquina de estados |
| **API / integração** | Endpoints com banco real | auth, permissões, filtros, visibilidade, erros |
| **E2E (fluxo)** | Cenários completos | abrir → escalar → resolver → fechar com SLA |

### 8.2 Boas práticas
- Use `freezegun` para **todo** teste que envolva tempo.
- Use `factory_boy` (nada de fixtures JSON gigantes).
- Um teste, uma razão para falhar; nomes descritivos (`test_solicitante_nao_ve_chamado_de_outro_usuario`).
- Teste o **caminho triste** (403, 404, 409) tanto quanto o feliz.
- Parametrize a matriz de permissões (perfil × endpoint × resultado esperado).

### 8.3 Exemplo: máquina de estados (esqueleto)

```python
# apps/chamados/estados.py
from enum import StrEnum


class Status(StrEnum):
    ABERTO = "ABERTO"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    AGUARDANDO_SOLICITANTE = "AGUARDANDO_SOLICITANTE"
    RESOLVIDO = "RESOLVIDO"
    FECHADO = "FECHADO"
    REABERTO = "REABERTO"
    CANCELADO = "CANCELADO"


# (origem, destino) -> perfis autorizados
TRANSICOES = {
    (Status.ABERTO, Status.EM_ATENDIMENTO): {"ANALISTA", "GESTOR"},
    (Status.ABERTO, Status.CANCELADO): {"SOLICITANTE", "GESTOR"},
    (Status.EM_ATENDIMENTO, Status.AGUARDANDO_SOLICITANTE): {"ANALISTA", "GESTOR"},
    (Status.AGUARDANDO_SOLICITANTE, Status.EM_ATENDIMENTO): {"SOLICITANTE", "ANALISTA", "GESTOR"},
    (Status.EM_ATENDIMENTO, Status.RESOLVIDO): {"ANALISTA", "GESTOR"},
    (Status.RESOLVIDO, Status.FECHADO): {"SOLICITANTE", "GESTOR"},
    (Status.RESOLVIDO, Status.REABERTO): {"SOLICITANTE", "GESTOR"},
    (Status.REABERTO, Status.EM_ATENDIMENTO): {"ANALISTA", "GESTOR"},
}


def transicao_permitida(origem: Status, destino: Status, perfil: str) -> bool:
    return perfil in TRANSICOES.get((origem, destino), set())
```

---

## 9. CI/CD com GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: helpdesk
          POSTGRES_USER: helpdesk
          POSTGRES_PASSWORD: helpdesk
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U helpdesk"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      DJANGO_SETTINGS_MODULE: config.settings.test
      DATABASE_URL: postgres://helpdesk:helpdesk@localhost:5432/helpdesk
      SECRET_KEY: ci-only-secret
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements/dev.txt
      - run: ruff check . && ruff format --check .
      - run: bandit -q -r apps config
      - run: pytest --cov=apps --cov-report=term-missing --cov-fail-under=85
      - run: python manage.py spectacular --validate --fail-on-warn --file /dev/null

  docker:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t helpdesk-api:ci .
```

> Opcional: workflow agendado (`on: schedule: cron: "*/10 * * * *"`) que faz um `curl -X POST` com token no endpoint interno de verificação de SLA, caso você use a Opção A em produção. Lembre que agendamentos do GitHub Actions podem atrasar alguns minutos.

---

## 10. Docker e infraestrutura

### 10.1 Dockerfile (multi-stage)

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
COPY requirements/base.txt requirements/base.txt
RUN pip wheel --wheel-dir /wheels -r requirements/base.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -m app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY . .
USER app
ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

### 10.2 docker-compose (desenvolvimento)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: helpdesk
      POSTGRES_USER: helpdesk
      POSTGRES_PASSWORD: helpdesk
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U helpdesk"]
      interval: 5s
      retries: 10

  api:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    depends_on:
      db: {condition: service_healthy}

  mailpit:
    image: axllent/mailpit
    ports: ["8025:8025", "1025:1025"]

volumes:
  pgdata:
```

### 10.3 Variáveis de ambiente (`.env.example`)

```
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=troque-esta-chave
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://helpdesk:helpdesk@db:5432/helpdesk
CORS_ALLOWED_ORIGINS=http://localhost:3000
EMAIL_HOST=mailpit
EMAIL_PORT=1025
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=7
SLA_JOB_TOKEN=troque-este-token
```

---

## 11. Segurança

- [ ] `SECRET_KEY`, tokens e senhas **somente** em variáveis de ambiente
- [ ] `DEBUG=False`, `ALLOWED_HOSTS` e CORS restritos em produção
- [ ] Headers de segurança (`SECURE_*`, HSTS, cookies seguros) e HTTPS
- [ ] Throttling (login e endpoints de escrita)
- [ ] Senhas com validadores do Django (hash padrão PBKDF2/Argon2)
- [ ] JWT de curta duração + rotação + blacklist de refresh
- [ ] **IDOR:** consultas sempre filtradas por visibilidade (404 para recursos fora do escopo)
- [ ] Validação de entrada em todos os serializers; sem `fields = "__all__"`
- [ ] Sem dados sensíveis em logs e auditoria
- [ ] `pip-audit` e `bandit` no CI; Dependabot habilitado (gratuito)
- [ ] Endpoint de job de SLA protegido por token e fora do Swagger público
- [ ] Imagem Docker com usuário não root

---

## 12. Deploy gratuito

> Planos gratuitos mudam. **Confira limites, hibernação e prazos de expiração** de cada serviço na página oficial antes de decidir.

**Arquitetura sugerida**

| Peça | Opção gratuita |
|---|---|
| API (container) | Render (web service free) |
| PostgreSQL | Neon ou Supabase (free) |
| E-mail | Brevo ou Resend (free) |
| Agendamento do SLA | GitHub Actions (`schedule`) chamando endpoint protegido |
| Monitoramento | Sentry (free) + logs do provedor |
| Cobertura / badges | Codecov + shields.io |

**Passos**
1. Criar o banco gratuito e copiar a `DATABASE_URL`.
2. Criar o web service apontando para o repositório (build via Dockerfile).
3. Definir as variáveis de ambiente de produção.
4. Rodar migrations e `seed_demo` (via entrypoint ou shell do provedor).
5. Testar `/health/`, `/ready/` e o Swagger no ar.
6. Anotar no README que o primeiro acesso pode demorar (serviços gratuitos hibernam).

---

## 13. Documentação e portfólio

### 13.1 Estrutura do README
1. Título, badges (CI, cobertura, licença) e uma frase de impacto
2. **Problema** que o projeto resolve
3. **Demo no ar** (link do Swagger) + usuários de teste
4. **Funcionalidades** (lista curta)
5. **Arquitetura** (diagrama de componentes) e decisões técnicas (links para ADRs)
6. **Stack**
7. **Como rodar** (Docker em 3 comandos) e **como testar**
8. **Exemplo de fluxo** (curl ou GIF)
9. **Limitações conhecidas** e roadmap
10. Autor e contatos

### 13.2 Como apresentar na entrevista
- Conte a história: "Usei minha experiência em Service Desk N1/N2 para modelar regras reais de SLA e escalonamento."
- Destaque decisões: camada de serviços, máquina de estados explícita, SLA com pausa, auditoria imutável, testes com tempo congelado.
- Tenha respostas para: "por que JWT?", "como evitaria N+1?", "como escalaria isso?", "como garante a idempotência da escalada?".

---

## 14. Definition of Done (ponto final)

O projeto está **de fato pronto** quando **todos** os itens abaixo forem verdadeiros.

### Funcional
- [ ] Os 3 perfis autenticam com JWT (login, refresh, logout com blacklist)
- [ ] Ciclo completo do chamado funciona via API; transições inválidas retornam 409
- [ ] Visibilidade e permissões por perfil corretas em **todos** os endpoints
- [ ] Prioridade calculada pela matriz impacto × urgência
- [ ] SLA calcula prazos, pausa/retoma e sinaliza `EM_RISCO` e `VENCIDO`
- [ ] Escalonamento N1 → N2 funciona (manual com justificativa e automático idempotente)
- [ ] Histórico de status é imutável
- [ ] Auditoria cobre todas as ações do catálogo, sem dados sensíveis
- [ ] Endpoints de métricas funcionam para o Gestor
- [ ] Comentários internos nunca vazam para o solicitante

### Qualidade
- [ ] Testes passam no CI; cobertura **≥ 85%** global e **≥ 95%** em SLA, estados e permissões
- [ ] Testes de tempo usam `freezegun` e são determinísticos
- [ ] `ruff`, `bandit` e `pip-audit` sem pendências críticas
- [ ] Sem N+1 nas listagens principais; índices nas colunas filtradas
- [ ] Padrão de erro e paginação consistentes em toda a API

### Documentação
- [ ] Swagger/OpenAPI completo, validado no CI, com JWT funcionando no botão "Authorize"
- [ ] README completo, ER, diagrama de estados, ADRs e `openapi.yaml` publicados
- [ ] Coleção Bruno/Postman disponível

### Infraestrutura
- [ ] `docker compose up` funciona do zero com `seed_demo`
- [ ] `check --deploy` sem alertas críticos; imagem com usuário não root
- [ ] API publicada com link funcional; release `v1.0.0` com tag
- [ ] Verificação periódica de SLA em execução no ambiente publicado

### Critério final
> Alguém que nunca viu o projeto consegue, em **10 minutos**, acessar a API, autenticar como cada perfil, abrir um chamado, vê-lo escalar por SLA e consultar histórico e auditoria — tudo documentado e testado.

---

## 15. Cronograma

| Fase | Duração estimada |
|---|---|
| 0. Preparação e escopo | 1–2 dias |
| 1. Modelagem e regras | 2–3 dias |
| 2. Estrutura e ambiente | 1–2 dias |
| 3. Autenticação e usuários | 2–3 dias |
| 4. Núcleo de chamados | 4–5 dias |
| 5. Histórico e auditoria | 2–3 dias |
| 6. SLA e escalonamento | 3–4 dias |
| 7. Notificações (opcional) | 1–2 dias |
| 8. Consolidação de testes | 3–4 dias |
| 9. Swagger/OpenAPI | 1–2 dias |
| 10. Docker e produção | 2–3 dias |
| 11. Deploy e publicação | 1–2 dias |
| **Total** | **~4 a 6 semanas** (ritmo de projeto paralelo) |

**Marcos sugeridos**
- **M1 (fim da Fase 3):** autenticação funcionando
- **M2 (fim da Fase 4):** ciclo do chamado completo
- **M3 (fim da Fase 6):** SLA e escalonamento prontos — *coração do projeto*
- **M4 (fim da Fase 9):** API documentada e testada
- **M5 (fim da Fase 11):** `v1.0.0` publicada

---

## 16. Riscos e evoluções futuras

### Riscos

| Risco | Mitigação |
|---|---|
| Escopo crescer demais | Congelar o escopo da Fase 0; novidades vão para o roadmap |
| Regras de SLA ambíguas | Documentar na Fase 1 e cobrir com testes de tempo |
| Complexidade de Celery | Começar com management command; migrar depois se quiser |
| Limites do plano gratuito | Arquitetura em Docker, portável entre provedores |
| Perder motivação no meio | Entregar por marcos e publicar o progresso no GitHub |

### Evoluções (roadmap v2)
- SLA em **horário comercial** e calendário de feriados
- Anexos em chamados (storage gratuito, como Cloudflare R2 ou Supabase Storage — verificar planos)
- Notificações por WhatsApp/Telegram (bot)
- Base de conhecimento (artigos sugeridos ao abrir chamado)
- Pesquisa de satisfação (CSAT) ao fechar
- Webhooks para integrações
- Cache com Redis nas métricas
- Multi-tenant (reaproveita sua experiência com SaaS)
- Versão em **ASP.NET Web API** do mesmo domínio, para mostrar as duas stacks no portfólio

---

*Documento gerado como guia de execução. Ajuste prazos, escopo e ferramentas conforme seu ritmo e os planos gratuitos disponíveis no momento do deploy.*
