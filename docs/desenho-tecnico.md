# Desenho técnico — Help Desk API

Data: 2026-11-16. Requisitos consolidados em `decisoes-iniciais.md`.

## Objetivo e limites

API de portfólio funcional para equipe, com três perfis, atendimento N1/N2, SLA auditável e implantação local reproduzível. Não incluir frontend, anexos, multi-tenant, horário comercial ou Celery nesta versão. GitHub após conclusão local; hospedagem é decisão posterior.

## Abordagem escolhida

O responsável aceitou Django 5.2 LTS + DRF, uv, Docker, PostgreSQL em produção e management command. Celery acrescentaria infraestrutura sem necessidade nesta fase; aplicação com serviços separados permite adotá-lo futuramente. SQLite será o banco de desenvolvimento e testes locais por solicitação explícita; CI com PostgreSQL verificará compatibilidade com produção, sem exigir banco PostgreSQL local. O ambiente virtual `.venv` contém as dependências isoladas.

## Estrutura

- `config/settings/{base,dev,test,prod}.py`: configuração por ambiente.
- `apps/usuarios`: AbstractUser customizado, e-mail único para login, perfil e nível.
- `apps/chamados`: categoria, chamado, comentários, triagem, eventos e transições.
- `apps/sla`: políticas, ciclos, pausas, indicadores e job periódico.
- `apps/auditoria`: eventos imutáveis pela aplicação, sem segredos.
- `apps/metricas`: consultas de gestão; `apps/core`: erros, paginação e utilitários.
- `services.py` autoriza e altera estado em transações; `selectors.py` restringe consultas por visibilidade. Serializers validam formato e campos permitidos.

## Persistência

Usuário possui perfil SOLICITANTE/ANALISTA/GESTOR; nível N1/N2 obrigatório apenas para Analista. Campos Django de autenticação são preservados. Perfil não concede acesso ao admin automaticamente.

Chamado guarda título, descrição, categoria protegida contra exclusão se utilizada, impacto, urgência, prioridade, status, solicitante, responsável, nível atual, abertura, primeira resposta e triagem N1. Registrar ator/data/justificativa da triagem. Solicitante, nível e responsável não são campos livres no cadastro.

Política possui prioridade e duração de resolução; primeira resposta inicial uniforme de 120 minutos. Cada chamado preserva a duração de primeira resposta aplicada e um snapshot completo das durações das quatro prioridades na abertura. Reaberturas e mudanças de prioridade usam esse snapshot, sem adotar políticas posteriormente editadas. Cada ciclo de resolução preserva início, prazo, duração aplicada, prioridade, resolução, resultado e violações já registradas. Primeiro ciclo começa na abertura; reabertura cria outro. Só existe um ciclo não resolvido por chamado.

Pausas pertencem ao ciclo; no máximo uma pausa aberta. Datas devem ser coerentes. Constraints portáveis são acompanhadas de validação transacional; locks de linha são verificados em PostgreSQL.

Histórico de status registra todas as transições. Eventos separados registram triagem, escalada, prioridade, atribuição e alertas, inclusive sem mudança de status. Autor do sistema é nulo com origem explícita. Exclusões em cascata não podem destruir trilha de atendimento; desativar usuários/categorias usados.

## Estado e autorização

ABERTO → EM_ATENDIMENTO ao assumir; ABERTO → CANCELADO pelo solicitante ou Gestor. EM_ATENDIMENTO → AGUARDANDO_SOLICITANTE exige comentário público do responsável/Gestor. Resposta pública do solicitante retoma EM_ATENDIMENTO. Responsável/Gestor também pode retomar explicitamente, encerrando a pausa.

EM_ATENDIMENTO → RESOLVIDO pelo responsável/Gestor exige descrição de solução. RESOLVIDO → REABERTO pelo solicitante ou Gestor dentro de 48h desde a resolução, com motivo. REABERTO → EM_ATENDIMENTO ao assumir. RESOLVIDO → FECHADO por confirmação do solicitante, Gestor ou job elegível. FECHADO e CANCELADO são terminais.

Decisão técnica proposta: ao reabrir, remover responsável e preservar nível; nova assunção é obrigatória. Um chamado escalado pode permanecer EM_ATENDIMENTO sem responsável; somente nova assunção no nível correto habilita condução. Gestor conduz chamados sem assumir; assunção pessoal é reservada a Analistas para manter compatibilidade de nível.

Visibilidade: solicitante vê os próprios; Analista vê os próprios, fila do nível e atribuídos; Gestor vê todos. Ser solicitante tem precedência para ocultar comentários internos inclusive para equipe/Gestor. Respostas públicas dadas pelo próprio solicitante não contam como primeira resposta de atendimento.

Somente dono edita conteúdo enquanto ABERTO; responsável/Gestor pode corrigir conteúdo de chamados ativos com auditoria. Prioridade pode ser alterada pelo responsável Analista ou Gestor, em chamados ativos; impacto/urgência originais permanecem registrados e a sobreposição exige motivo.

## SLA e fechamento

Armazenar datas em UTC; API usa ISO 8601 com fuso. Tempo corrido. Resolução inicial: crítica 4h, alta 8h, média 24h, baixa 72h. Primeira resposta em até 2h para todas. Ambos os indicadores têm NO_PRAZO, EM_RISCO (>=80%), VENCIDO e resultado final CUMPRIDO/VIOLADO; cancelamento interrompe obrigações pendentes com resultado NAO_APLICAVEL.

Cumprimento no instante exato do prazo é permitido; ultrapassar o prazo caracteriza violação. Leitura calcula o indicador com horário atual, sem depender do job. Durante pausa, descontar a pausa aberta do consumo; no encerramento, deslocar o prazo e preservar pausas fechadas. Primeira resposta nunca pausa.

Reclassificação recalcula duração de resolução a partir do início do ciclo mais pausas; resultado de primeira resposta não reinicia, e violações já registradas não são apagadas. Alterar política não afeta ciclos existentes.

Confirmado em 2026-11-16: janela de reabertura fixa de 48h desde resolução. Comentário público do solicitante enquanto RESOLVIDO adia fechamento até 48h desde essa interação, mas não amplia janela de reabertura. Fechar exige RESOLVIDO e tanto janela de reabertura expirada quanto inatividade de 48h. Após FECHADO, nenhuma edição, novo comentário ou reabertura é permitida, inclusive pelo Gestor. O serviço impõe os prazos mesmo se o job de fechamento ainda não tiver executado.

## Triagem, alertas e job

Ação explícita de triagem é exclusiva de Analista N1, com justificativa, em ABERTO, REABERTO ou EM_ATENDIMENTO no nível N1. Pode ocorrer antes de assumir, sem atribuir responsável; se já atribuído, somente responsável N1 pode triar. O solicitante não pode triar seu próprio chamado, mesmo sendo N1. Antes da triagem, nunca transferir N2. Escalada manual exige triagem e motivo; automática exige triagem e gatilho de risco ou criticidade sem responsável após 10min da abertura. N2 não escala novamente. Solicitações repetidas não duplicam evento.

Antes de triar, gatilhos geram alerta auditável para N1/Gestor; primeira versão expõe alertas na API para N1 no seu escopo e Gestor, sem e-mail obrigatório. A cada ciclo/motivo registrar um alerta, sem repetição no job. Chamados aguardando solicitante ou terminais não escalam.

`verificar_sla` processa alertas, escaladas elegíveis e fechamento por lotes. Cada operação relê o estado sob lock no PostgreSQL e confirma elegibilidade dentro da transação. API usa o mesmo serviço. Requisições concorrentes de assunção têm um vencedor e conflito 409 para o outro. Histórico e auditoria são gravados na mesma transação.

## Contratos de API

Base `/api/v1/`. JWT access 15min e refresh 7 dias com rotação e blacklist. Logout revoga refresh; access pode durar até expirar. Desativação deve impedir autenticação/reutilização de conta inativa. Cadastro público rejeita campos de privilégio; atualização de usuários é exclusiva do Gestor e auditada.

Manter endpoints originais, acrescentando POST `/chamados/{id}/triar/`, POST `/chamados/{id}/prioridade/`, GET `/alertas/` para Analista N1 no seu escopo e Gestor, e PATCH `/usuarios/{id}/` para gestão de nível, perfil e desativação. Políticas: GET coleção e GET/PATCH `/sla/politicas/{id}/`. Health e readiness em `/health/` e `/ready/` fora da base; readiness retorna 503 se banco indisponível sem detalhes sensíveis.

Decisões técnicas: paginação padrão 20, máximo 100; ordenação por abertura e ID para desempate; título até 200 caracteres, descrição/comentário até 10.000. IDs inteiros são suficientes com visibilidade aplicada antes da busca. Erros seguem envelope original e códigos 400/401/403/404/409/429. Swagger documenta campos de leitura/escrita, exemplos e conflitos.

Métricas por período de abertura para volume, e por data de conclusão da obrigação para SLA. Taxa de cumprimento considera apenas obrigações concluídas aplicáveis; retornos incluem numerador e denominador. Resoluções são medidas por ciclo, primeira resposta por chamado. Não contar cancelamentos como cumprimentos.

## Qualidade, segurança e operação

pytest com SQLite por padrão e relógio controlado; suíte PostgreSQL específica para locks, constraints e integração. Testar papéis × objeto × status, ausência de notas internas, limites temporais, reaberturas, job repetido e API concorrente. Metas originais: 85% global e 95% em SLA, estados e permissões.

CI: uv sync com lock, Ruff, testes, cobertura, Bandit, pip-audit, schema OpenAPI, migrations pendentes e build Docker. Nenhuma dependência instalada sem lockfile. Sem prometer garantia de banco com testes SQLite.

Segredos via ambiente; produção sem DEBUG, com HTTPS e configurações seguras. Não registrar senhas, tokens ou descrições completas em auditoria desnecessariamente; usar allowlist de campos. Eventos são imutáveis via serviços, API e admin; triggers/permissões adicionais do banco ficam fora da garantia inicial. Recuperação de senha e verificação de e-mail ficam explicitamente fora da v1, documentadas como limitação.

Docker Compose local opcional com API e SQLite em volume persistente; imagem sem root e sem serviço PostgreSQL local. Produção preparada para PostgreSQL externo. Migrações em etapa única antes de iniciar aplicação em produção. Seed demo idempotente e explícito, sem criar credenciais conhecidas automaticamente em produção. Demo temporal pré-preparada para mostrar SLA sem alterar políticas reais.

## Sequência de implementação

1. Ambiente, configurações, custom user antes das migrations, health/readiness e CI mínimo.
2. Autenticação, perfis e autorização de objetos.
3. Models completos mínimos, abertura, atendimento, histórico e auditoria atômicos.
4. SLA, ciclos, pausas, prioridade e reabertura.
5. Triagem, escalada, alertas e job idempotente.
6. Métricas, OpenAPI, testes PostgreSQL e consolidação de segurança.
7. Docker reproduzível, documentação, dados demo e preparação para GitHub.

Nenhuma publicação externa é executada nesta etapa. Desenho aprovado pelo responsável em 2026-11-16, com confirmação final do fechamento em 48h. Implementação iniciada pela fundação do ambiente.

## Andamento da implementação

Fundação e autenticação entregues. Núcleo de chamados entregue com categorias,
prioridade inicial, políticas em snapshot, ciclos, pausas, comentários, atribuição,
transições, reabertura e histórico. Atribuição inicial por Gestor inicia
EM_ATENDIMENTO sem registrar primeira resposta. Admin respeita visibilidade e
ocultação de notas internas do próprio solicitante, inclusive superusuário.

Comando `fechar_resolvidos` implementado e idempotente, incorporado ao job
`verificar_sla`, com execução única ou modo contínuo local. A API bloqueia mutações após elegibilidade para fechamento,
mas a mudança persistida para FECHADO e seu histórico ocorrem quando o comando roda.
Indicadores independentes de primeira resposta/resolução, mudanças de prioridade,
gestão de políticas, triagem, escalonamento e alertas estão implementados. Eventos
internos são consultados pela equipe via API, exceto pelo solicitante do chamado.
Métricas de volume/SLA e consulta de auditoria pela API estão implementadas. Detalhes e
evidências nos planos `docs/superpowers/plans/2026-11-16-chamados.md` e
`docs/superpowers/plans/2026-11-16-sla-escalonamento.md`.

Resultados de primeira resposta são finalizados e preservados entre reaberturas;
ausência de resposta ao concluir atendimento é VIOLADO. Violações de resolução
são constatadas no job, repriorização ou resolução e persistem mesmo após ampliar
o prazo. Indicadores calculam pausa aberta sem gravar dados durante a leitura;
filtro de SLA é aplicado no banco antes da paginação, sempre no escopo visível.
O job contínuo exige terminal aberto; nenhum processo foi iniciado nesta sessão.
Agendamento gerenciado de produção será configurado após escolha da hospedagem.

Métricas/auditoria exigem Gestor ativo. Relatórios usam `inicio`/`fim` opcionais,
ISO8601 com fuso, início inclusivo e fim exclusivo. Volume filtra abertura e agrupa
estado atual; SLA filtra conclusão da obrigação, com primeira resposta por chamado
e resolução por ciclo. Cumprimento é cumpridos/(cumpridos+violados)*100; pendentes
não entram e NAO_APLICAVEL é informado separadamente. Sem denominador, retornar null.
Auditoria possui coleção/detalhe somente leitura, filtros e paginação20/máximo100;
snapshots legados são restringidos à allowlist na saída, sem alterar o registro.
Plano e evidências: `docs/superpowers/plans/2026-11-16-metricas-auditoria.md`.

Demonstração local entregue: cinco contas sem privilégios administrativos, onze
cenários, manifesto sem segredos, reexecução idempotente e rotação explícita de
senhas. Credenciais aleatórias ficam em ambiente Postman privado ignorado pelo Git;
seed desabilitado em produção e não executa jobs sobre chamados alheios.
Coleção pública v2.1 validada por29requisições/35asserções no Newman, com banco e
servidor temporários. Guias em `docs/demo.md` e `docs/publicacao.md`; plano em
`docs/superpowers/plans/2026-11-16-demonstracao.md`. GitHub, hospedagem e validação
Docker/PostgreSQL permanecem pendentes.
