# Métricas e consulta de auditoria — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans com testes antes do código e revisão independente final.

**Goal:** Entregar GET metricas/volume/, metricas/sla/ e auditoria/ com acesso exclusivo do Gestor, filtros validados e documentação.
**Architecture:** Selectors agregam dados no banco, sem carregar todos os chamados ou modificar estado; views autorizam e validam parâmetros. Auditoria é somente leitura com snapshots limitados à allowlist existente.
**Tech Stack:** Django/DRF instalados, SQLite no desenvolvimento/testes, PostgreSQL preparado para produção. Sem Docker, novas dependências ou publicação.
**Spec:** `docs/desenho-tecnico.md`, seção métricas/contratos. Execução autorizada da próxima etapa, diretamente no workspace sem Git.

## Global Constraints

- Apenas Gestor ativo consulta métricas/auditoria. Não autenticado401, outro perfil403; flags do admin não substituem perfil.
- `inicio` e `fim` opcionais em ISO8601 com fuso; intervalo inclui início e exclui fim. Limites independentes permitidos; fim deve ser posterior a início.
- Volume filtra abertura e agrupa status/categoria/nível/prioridade atuais. Status/prioridades/níveis conhecidos aparecem com zero quando ausentes; categorias incluem somente as com chamados no período.
- SLA filtra conclusão da obrigação: primeira_resposta_finalizada_em por chamado, encerrado_em por ciclo. Reabertura não duplica primeira resposta e cada ciclo encerrado conta separadamente.
- Taxa = cumpridos/(cumpridos+violados)*100, arredondada a2casas. Retornar numerador, denominador, cumpridos, violados, não aplicáveis e total concluído. Denominador zero retorna null, nunca100 por ausência de dados.
- Somente obrigações concluídas com resultado conhecido entram no relatório; cancelamento não é cumprimento. Sem período, consultar todo o histórico.
- Auditoria GET coleção e detalhe; filtros ator, sistema, ação, entidade, entidade_id, período; paginação20/máximo100 e ordem -criado_em,-id. Sistema=true significa ator nulo; não pode combinar com ator.
- Leituras não geram novos logs; nenhuma rota permite criar/editar/excluir auditoria.
- Serializar somente campos explícitos; snapshots usam allowlist por entidade e não expõem senhas/tokens/conteúdo de notas. Nenhum motivo interno de EventoChamado é incluído nesses relatórios.

## Review Focus

1. Chamado aberto antes do período e concluído dentro dele deve contar no SLA, mas não no volume desse período.
2. Reabertura e múltiplos ciclos, cancelamento e resultados ativos não podem inflar a taxa.
3. Intervalos invertidos, datas sem fuso e filtros inválidos devem retornar400 antes de consultar.
4. Gestor com perfil revogado ou usuário desativado não pode acessar relatórios; outros perfis/admin flags não concedem acesso.
5. Agregações e paginação não devem introduzir N+1, nem vazar conteúdo sensível da auditoria.

## Task 1 — Métricas

Files: `apps/metricas/{apps,selectors,serializers,views,urls}.py`, `apps/core/periodos.py`, settings/urls, testes `tests/test_metricas.py`.
Interfaces: `volume(*,inicio=None,fim=None) -> dict`; `sla(*,inicio=None,fim=None) -> dict`; `PeriodoSerializer` valida o intervalo compartilhado.

- [x] Escrever testes de permissão, volume vazio/agrupado, taxa sem denominador, reabertura/cancelamento, fronteiras com timezone e consultas constantes.
- [x] Observar falhas antes da implementação.
- [x] Implementar agregações SQL e contratos explícitos, sem cálculos que confundam data de abertura com conclusão.
- [x] Verificar resultados e regressões.

## Task 2 — Auditoria

Files: `apps/auditoria/{selectors,serializers,views,urls}.py`, testes `tests/test_api_auditoria.py`.
Interfaces: `consultar_logs(filtros) -> QuerySet[LogAuditoria]`; representação não modifica snapshots persistidos.

- [x] Testar acesso, filtros, datas, paginação, detalhe/inexistente, sistema, métodos405 e ausência de segredos.
- [x] Observar falha pelos endpoints ausentes.
- [x] Implementar listagem/detalhe e mascaramento por allowlist, mantendo histórico imutável.
- [x] Verificar ausência de novas gravações durante leitura e consultas constantes.

## Task 3 — Documentação e validação

- [x] Documentar fórmulas, limites e payloads em README/OpenAPI.
- [x] Rodar suíte completa com cobertura>=85%, Ruff, Bandit, Django check e migration drift.
- [x] Revisão independente; achados importantes com regressão RED→GREEN e suíte completa.

## Registro

- Sem mudança nas regras de atendimento/SLA desta etapa. Datas e taxas definidas conforme desenho aprovado.

## Resultado verificado

- 236 testes passaram em SQLite, 57 novos nesta etapa; cobertura global apps 98,32%.
- Modulo metricas, selectors e serializacao da auditoria com cobertura100%; validacao compartilhada de periodos coberta inclusive datas impossiveis.
- Ruff, formatacao, Bandit, checks Django, migration drift e OpenAPI passaram.
- Nenhuma migration nova necessaria; esta etapa apenas consulta dados existentes.
- Revisao independente sem achados importantes: 55 testes metricas/auditoria executados em SQLite em memoria, sem usar banco local. Dois casos adicionais cobrem calendario invalido.
- Relatorios comprovados com duas consultas cada, independentemente da quantidade de chamados; auditoria paginada com duas consultas, sem N+1 ou novas gravacoes.
- Decisoes tecnicas documentadas: intervalos [inicio,fim), taxa null sem denominador, volume por abertura/estado atual e SLA por conclusao de cada obrigacao. Resultado de resposta ja concluida e preservado mesmo se houver cancelamento posterior.
- Mixin de throttle por metodo movido para core e reutilizado, evitando dependencia de outras APIs no modulo de chamados.
- Sem novas dependencias, Docker, Git, publicacao ou processos persistentes. PostgreSQL e CI remoto ainda nao executados neste ambiente.
- Proxima etapa: dados demonstrativos, colecao de requisicoes e preparacao para publicacao no GitHub.
