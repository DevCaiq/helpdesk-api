# Gestão de Chamados — API REST

API de portfólio em Python 3.12, Django 5.2 LTS e Django REST Framework.

**Estado atual:** autenticação JWT, gestão de usuários, categorias, chamados,
atribuição, comentários públicos/internos, histórico e auditoria. Abertura já
calcula prioridade e prazos; ciclos de resolução e pausas preservam o SLA aplicado.
Inclui indicadores de SLA, triagem N1, escalonamento manual/automático, alertas,
job periódico local, Django Admin para consulta, Swagger e testes.
Métricas de gestão e consulta de auditoria pela API também estão disponíveis.
Demonstração idempotente, coleção Postman e preparação para GitHub também estão prontas.
Código disponível no [GitHub](https://github.com/DevCaiq/helpdesk-api).
Hospedagem e agendamento de produção ficam para depois.

## Decisões

- [Desenho técnico](docs/desenho-tecnico.md)
- [Regras consolidadas](docs/decisoes-iniciais.md)
- [Plano da fundação](docs/superpowers/plans/2026-11-16-fundacao.md)
- [Demonstração e coleção Postman](docs/demo.md)
- [Arquitetura e decisões](docs/arquitetura.md)
- [Preparação para GitHub](docs/publicacao.md)

Chamados passam por triagem N1 antes de N2. Primeira resposta em até 2h.
Reabertura em até 48h desde resolução; fechamento após 48h sem interação do
solicitante. Fechado é definitivo, sem edições ou reabertura.

## Instalação local (PowerShell)

Pré-requisitos: Python 3.12 e uv. Desenvolvimento e testes usam SQLite;
Docker é opcional. PostgreSQL é reservado à produção.

```powershell
git clone https://github.com/DevCaiq/helpdesk-api.git
cd helpdesk-api
Copy-Item .env.example .env
uv sync --frozen
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

O `uv sync` cria o ambiente virtual `.venv` e instala as dependências do lockfile.
O banco local é `db.sqlite3`, excluído do versionamento. Para sair do ambiente:

```powershell
deactivate
```

Neste workspace o uv foi instalado somente em `.tools`. Caso não tenha uv no
PATH, substitua `uv` por `.\.tools\Scripts\uv.exe` nos comandos locais.
O ambiente `.venv` e as pastas auxiliares não devem ser versionados.

Se o PowerShell bloquear a ativação, você pode usar o interpretador diretamente,
sem alterar a política de execução:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## API com SQLite via Docker (opcional)

```powershell
Copy-Item .env.example .env
docker compose build
docker compose run --rm api /app/.venv/bin/python manage.py migrate
docker compose run --rm api /app/.venv/bin/python manage.py createsuperuser
docker compose up -d api
```

O Compose não inicia PostgreSQL. O SQLite fica em `/data/db.sqlite3`, persistido
no volume `sqlite-data`. As migrations são explícitas, não executadas
simultaneamente por cada worker. Não há usuários/senhas demo criados automaticamente.

- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:8000/api/docs/
- OpenAPI: http://localhost:8000/api/schema/
- Liveness: http://localhost:8000/health/
- Readiness: http://localhost:8000/ready/

O Swagger permite testar autenticação, usuários, categorias e o ciclo de atendimento.

## Demonstração pronta

Com `.venv` ativo, depois de aplicar as migrations:

```powershell
python manage.py seed_demo
python manage.py runserver
```

São criadas cinco contas sem acesso ao Admin e onze chamados fictícios cobrindo
abertura, N1/N2, espera, resolução, reabertura, fechamento e automação.
Credenciais fortes são geradas em `.demo/local.postman_environment.json`, ignorado
pelo Git. O comando não imprime senhas e não modifica contas alheias ou dados já
existentes do demo. Produção mantém o seed desabilitado.

Importe [a coleção Postman](collections/postman/helpdesk.postman_collection.json)
e o ambiente privado gerado para executar o fluxo inteiro. A coleção pública usa
variáveis e não contém senhas. Detalhes de cenários, rotação explícita, nova base de
demonstração e validação HTTP isolada estão em [docs/demo.md](docs/demo.md).

## Autenticação e usuários

Base: `/api/v1/`.

| Método | Rota | Acesso |
|---|---|---|
| POST | `usuarios/` | Cadastro público de Solicitante |
| POST | `auth/login/` | E-mail e senha |
| POST | `auth/refresh/` | Refresh válido |
| POST | `auth/logout/` | Access Bearer e refresh do próprio usuário |
| GET | `usuarios/me/` | Autenticado |
| GET | `usuarios/` | Gestor |
| POST | `usuarios/staff/` | Gestor cria Analista/Gestor |
| PATCH | `usuarios/{id}/` | Gestor altera nome, perfil, nível ou is_active |

Cadastro público:

```json
{"email": "pessoa@example.com", "nome": "Pessoa", "password": "Use-uma-senha-forte!"}
```

Login recebe `email` e `password`, retornando `access` (15 minutos) e `refresh`
(7 dias). No Swagger, clique em **Authorize** e informe o access conforme o campo
indicar. Nas requisições, envie `Authorization: Bearer <access>`.
Renovação recebe `{"refresh": "..."}` e devolve um novo par; descarte o refresh
anterior. Logout recebe o refresh mais recente e revoga somente ele; access já
emitido permanece válido até expirar. Desativar conta impede uso de access e refresh.
Papéis são consultados no banco, portanto mudanças de perfil valem na próxima requisição.

Para criar o primeiro Gestor local, use `python manage.py createsuperuser`.
Gestores criados pela API não recebem acesso ao Admin Django. Criar Analista
exige `perfil=ANALISTA` e `nivel=N1` ou `N2`; Gestor não pode ter nível.
Ao mudar um Analista para Gestor/Solicitante, envie também `nivel: null`.
Gestor não pode desativar ou rebaixar a própria conta pela API.

Login limitado a 10 tentativas/minuto por IP; cadastro a 10/hora por IP.
Renovação permite 30/minuto; escrita de gestão/logout permite 60/minuto.
O cache padrão é local a cada processo: para limitação global em produção,
configurar cache compartilhado ou controle no proxy na etapa de implantação.

Auditoria registra criação/alteração de usuários, login bem-sucedido/falho e logout,
além das ações de categorias e chamados. Conteúdo de notas e descrições não é copiado
para os snapshots de auditoria.
Os registros podem ser consultados no Admin, sem edição/exclusão; usuários com
eventos associados devem ser desativados, não excluídos. SQL direto não é coberto
pela garantia de imutabilidade da aplicação. Não há recuperação de senha ou
verificação de e-mail nesta versão.

## Chamados e atendimento

Todas as rotas exigem autenticação e usam `/api/v1/` como base.

| Método | Rota | Comportamento |
|---|---|---|
| GET/POST | `categorias/` | Listagem autenticada; criação por Gestor |
| GET/PUT/PATCH/DELETE | `categorias/{id}/` | Escrita por Gestor; categoria utilizada só pode ser desativada |
| GET/POST | `chamados/` | Fila visível e abertura em N1 |
| GET/PATCH | `chamados/{id}/` | Detalhe e edição controlada |
| POST | `chamados/{id}/assumir/` | Analista do nível assume chamado sem responsável |
| POST | `chamados/{id}/reatribuir/` | Gestor atribui a Analista ativo do mesmo nível |
| POST | `chamados/{id}/transicionar/` | Transição autorizada com motivo |
| POST | `chamados/{id}/reabrir/` | Dono/Gestor reabre antes de completar 48h |
| GET/POST | `chamados/{id}/comentarios/` | Comentários com isolamento de notas internas |
| GET | `chamados/{id}/historico/` | Histórico imutável por ordem cronológica |
| POST | `chamados/{id}/prioridade/` | Responsável/Gestor altera prioridade com motivo |
| POST | `chamados/{id}/triar/` | Triagem explícita por N1, exceto solicitante do chamado |
| POST | `chamados/{id}/escalar/` | Escalada manual N1→N2 após triagem |
| GET | `chamados/{id}/eventos/` | Eventos internos: equipe visível, exceto dono |
| GET | `sla/politicas/` | Políticas de SLA, somente Gestor |
| GET/PATCH | `sla/politicas/{id}/` | Gestor consulta/atualiza prazo para novos chamados |
| GET | `alertas/` | Alertas históricos no escopo N1 ou visão global do Gestor |

Fluxo de demonstração pelo Swagger:

1. Como Gestor, criar categoria e um Analista N1.
2. Como Solicitante, abrir chamado com `titulo`, `descricao`, `categoria` (ID),
   `impacto` (`ALTO`, `MEDIO`, `BAIXO`) e `urgencia` (`ALTA`, `MEDIA`, `BAIXA`).
3. Como Analista N1, enviar `{}` para `assumir/`: muda para EM_ATENDIMENTO,
   mas ainda não conta como primeira resposta.
4. Comentar `{"texto": "Vou analisar", "interno": false}`. Primeiro comentário
   público de atendimento marca primeira resposta; notas internas não contam.
5. Enviar `{"status": "AGUARDANDO_SOLICITANTE", "motivo": "Informe o erro"}`
   a `transicionar/`: publica a pergunta e pausa a resolução.
6. Como Solicitante, comentar a resposta: retoma atendimento e o prazo de resolução.
7. Como responsável/Gestor, enviar `{"status": "RESOLVIDO", "motivo": "Solução aplicada"}`.
   A solução vira comentário público e encerra o ciclo.
8. Como Solicitante, confirmar com status FECHADO ou reabrir com `{"motivo": "Falha retornou"}`.

Solicitante edita conteúdo somente em ABERTO; equipe responsável/Gestor pode
corrigir chamados ativos. Campos calculados, nível, autor, responsável e prioridade
não são aceitos no cadastro ou PATCH comum. Atribuição por Gestor de um chamado
ABERTO/REABERTO inicia EM_ATENDIMENTO sem contar primeira resposta.
O Admin apresenta chamados, comentários e histórico apenas para consulta;
use a API para executar ações de negócio auditadas.

Filtros: `status`, `prioridade`, `categoria`, `responsavel`, `solicitante`,
`nivel_atual`, `sla_status`, `aberto_em_de`, `aberto_em_ate` (ISO 8601). Busca via `search`
em título/descrição e ordenação via `ordering` em `aberto_em`, `id`, `prioridade`,
`status`; padrão `-aberto_em,-id`. Paginação padrão 20, máximo 100.
Filtros nunca ampliam a visibilidade do perfil.

As políticas iniciais são criadas por migration; cada chamado guarda um snapshot
das quatro durações. Reabrir preserva primeira resposta e ciclos anteriores,
remove responsável e inicia novo ciclo no mesmo nível.

## Indicadores de SLA e prioridade

Cada chamado retorna `sla.primeira_resposta` e `sla.resolucao`, com `status`,
`percentual_consumido`, `prazo`, `violado` e `pausado`. Os valores refletem o
horário da consulta sem depender do job. `sla_status` resume o pior indicador:
VIOLADO, VENCIDO, EM_RISCO; depois estados finais ou NO_PRAZO.

- NO_PRAZO: consumo menor que 80%.
- EM_RISCO: consumo a partir de 80%, até o instante do prazo inclusive.
- VENCIDO: prazo ultrapassado ou violação anterior preservada no ciclo ativo.
- CUMPRIDO/VIOLADO: resultado final da obrigação; cancelamento interrompe
  obrigações pendentes como NAO_APLICAVEL, preservando respostas já concluídas.

Primeira resposta continua em 2h para todas as prioridades. Pausa aberta congela
apenas resolução e ajusta seu prazo efetivo. Concluir sem resposta pública de
atendimento registra primeira resposta como VIOLADO; reabrir não reinicia essa obrigação.

Para alterar prioridade, envie `{"prioridade":"ALTA","motivo":"Impacto revisado"}`
ao endpoint `prioridade/`. Apenas responsável do nível ou Gestor pode alterar
chamados ativos. O prazo é recalculado desde o início do ciclo usando o snapshot
original e descontando pausas. Violações não são apagadas mesmo se o prazo aumentar;
o percentual pode ficar abaixo de 100% com `violado=true` por uma violação anterior.

Gestor altera política com `{"minutos_resolucao":480}`. O valor deve estar entre
1 e 525600 minutos; prioridade não é editável nem a política pode ser excluída.
Alterações valem apenas para novas aberturas, não para reaberturas ou repriorizações
de chamados existentes. Ambas as alterações são auditadas.

## Triagem, escalonamento e alertas

Triagem recebe `{"motivo":"Classificação conferida"}` em `triar/` e deve ser feita
por Analista N1 que não seja solicitante. Pode ocorrer antes de assumir; se já
atribuído, apenas o responsável N1 pode triar. Gestor/N2 não substitui a triagem N1.

Após triar, N1 responsável (ou N1 da fila se ainda sem responsável) e Gestor podem
enviar `{"motivo":"Exige análise N2"}` a `escalar/`. O solicitante não escala o
próprio chamado, mesmo tendo outro perfil. A escalada mantém status e prazos,
remove responsável e transfere para N2. O N2 deve assumir antes de conduzir atendimento.

O job automático verifica:

- Resolução com pelo menos 80% consumidos em N1, incluindo vencidos.
- Chamado crítico sem responsável após 10min desde abertura.
- Risco/vencimento de primeira resposta, gerando somente alerta por esse motivo.

Sem triagem, os gatilhos geram apenas alertas. Com triagem, os dois primeiros
permitem escalada. AGUARDANDO_SOLICITANTE e estados terminais não escalam.
Há somente uma escalada por chamado e um alerta por ciclo/motivo. Alertas são
históricos: `triagem_pendente` registra a condição no momento da emissão, não o
estado atual. N1 consulta alertas de chamados atualmente em seu nível; Gestor vê
todos. N2 e Solicitante não acessam o endpoint de alertas.

Eventos de triagem, prioridade e escalada ficam separados do histórico de status,
pois podem ocorrer sem mudar estado. Motivos são internos e não são mostrados ao
solicitante (inclusive Gestor dono do chamado). O endpoint `eventos/` permite
consulta pela equipe visível; esses eventos não estão expostos no Admin.

## Métricas de gestão

Rotas exclusivas do Gestor:

- `GET /api/v1/metricas/volume/`: total de chamados e agrupamentos por status,
  categoria, nível e prioridade atuais, filtrados pela **data de abertura**.
- `GET /api/v1/metricas/sla/`: resultados de primeira resposta por chamado e
  resolução por ciclo, filtrados pela **data de conclusão de cada obrigação**.

Ambas aceitam `inicio` e `fim` opcionais em ISO8601 com fuso, por exemplo
`inicio=2026-11-01T00:00:00Z&fim=2026-12-01T00:00:00Z`.
O início é inclusivo e o fim exclusivo; fim deve ser posterior a início.
É possível informar apenas um limite. Sem limites, todo o histórico é considerado.
Datas sem horário/fuso, intervalos invertidos e parâmetros desconhecidos retornam400.

Volume não conta ciclos como novos chamados. Um chamado reaberto continua sendo
um único chamado; seus agrupamentos refletem o estado atual, não o estado na data
da abertura. Status, prioridades e níveis ausentes aparecem com zero; categorias
aparecem somente quando possuem chamados no período, mesmo se hoje inativas.

SLA considera apenas obrigações concluídas. Cada ciclo de resolução encerrado
entra uma vez; reabrir não duplica primeira resposta. Obrigações pendentes ou
ainda em risco/vencidas não entram nessa taxa; podem ser consultadas pelos
indicadores e filtros de chamados. Resultados NAO_APLICAVEL são informados
separadamente e não entram no denominador.
Uma primeira resposta já concluída antes de um cancelamento conserva seu resultado;
o cancelamento interrompe apenas obrigações que ainda estavam pendentes.

Cada obrigação retorna um resumo como:

```json
{
  "cumpridos": 3,
  "violados": 1,
  "nao_aplicaveis": 2,
  "total_concluidos": 6,
  "numerador": 3,
  "denominador": 4,
  "taxa_cumprimento_percentual": 75.0
}
```

A fórmula é `cumpridos / (cumpridos + violados) * 100`, com duas casas decimais.
Sem obrigações aplicáveis concluídas, a taxa é `null`, não100%.
As métricas não executam jobs nem alteram chamados ou auditoria.

## Consulta de auditoria pela API

- `GET /api/v1/auditoria/`: listagem exclusiva do Gestor, com paginação padrão20,
  limite100 e ordem `-criado_em,-id`.
- `GET /api/v1/auditoria/{id}/`: detalhe do evento, também exclusivo do Gestor.

Filtros da listagem: `ator` (ID positivo), `acao`, `entidade`, `entidade_id`,
`inicio`, `fim`, `sistema`, `page` e `page_size`. As datas seguem as mesmas regras
dos relatórios, aplicadas a `criado_em`. `sistema=true` filtra ator nulo;
`sistema=false` filtra atores identificados. Não combine `ator` com `sistema=true`.
Textos de ação/entidade são comparados exatamente; filtros válidos sem correspondência
retornam uma lista vazia. Exemplo: `?entidade=chamado&entidade_id=25`.

POST, PUT, PATCH e DELETE não são permitidos. Consultar não cria novos logs.
Snapshots `antes`/`depois` são limitados à allowlist por entidade, inclusive para
registros legados, sem copiar senhas, tokens ou conteúdo de notas internas para
as respostas. A filtragem de saída não modifica o registro original.
Flags do Admin não substituem o perfil Gestor; desativação/revogação de perfil
vale também para access tokens emitidos anteriormente.

## Executar a automação local

Com `.venv` ativo, execute uma rodada:

```powershell
python manage.py verificar_sla
```

Para repetir a cada cinco minutos, mantenha um segundo terminal aberto:

```powershell
python manage.py verificar_sla --continuo --intervalo 300
```

Encerre com Ctrl+C. O comando integra alertas, escalonamento e fechamento de
resolvidos e não precisa de Docker, Redis ou Celery. Nenhum processo permanente
é iniciado automaticamente. Em produção, o agendador deve executar a rodada
periódica; o intervalo mede a espera entre o fim de uma rodada e a próxima.

Para efetivar os fechamentos elegíveis no banco:

```powershell
python manage.py fechar_resolvidos
```

O comando específico de fechamento continua disponível e é idempotente;
`verificar_sla` já inclui a mesma operação.
Mesmo sem executá-lo, a API bloqueia mutações em chamados já elegíveis a fechamento.
O status persistido e seu histórico passam para FECHADO quando o comando roda.
Comentários públicos do solicitante reiniciam apenas a contagem de inatividade;
nunca ampliam a janela fixa de 48h para reabertura. FECHADO e CANCELADO não aceitam
edições nem comentários, mesmo pelo Gestor. Leituras permanecem disponíveis.

## Testes e qualidade

Os testes padrão usam SQLite em memória e não precisam de Docker ou `.env`.

```powershell
uv run pytest
uv run ruff check apps config tests scripts manage.py
uv run ruff format --check apps config tests scripts manage.py
uv run python manage.py check --settings=config.settings.test
```

O CI mantém uma verificação adicional de compatibilidade com PostgreSQL de produção,
sem exigir PostgreSQL local. Consulte as execuções no
[GitHub Actions](https://github.com/DevCaiq/helpdesk-api/actions).
SQLite não comprova comportamento de locks de produção.

## Produção

Use `DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY` forte,
`DATABASE_URL` PostgreSQL e `ALLOWED_HOSTS` explícito. HTTPS é obrigatório;
a configuração do proxy depende do provedor escolhido. O Compose incluído é
apenas para desenvolvimento local com SQLite. Produção exige banco PostgreSQL
externo e configuração própria de implantação.
Não utilizar `config.settings.test` fora da suíte de testes.

## Próximas entregas

1. Acompanhamento dos workflows no GitHub e revisão dos resultados.
2. Validação de PostgreSQL/Docker em ambiente disponível.
3. Escolha de hospedagem e agendamento de produção.
