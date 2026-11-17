# SLA, triagem e escalonamento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, com testes antes da implementação e revisão independente final.

**Goal:** Entregar indicadores independentes de SLA, políticas editáveis, prioridade auditada, triagem N1, escalada manual/automática e alertas idempotentes.
**Architecture:** Indicadores calculados em leitura com relógio explícito; violações preservadas antes de repriorizar. Serviços transacionais bloqueiam o chamado; eventos sem transição de status têm tabela append-only. Job chama os mesmos serviços e integra fechamento, com execução única ou contínua local.
**Tech Stack:** Django/DRF, SQLite local, pytest/freezegun. PostgreSQL preparado, sem Docker ou publicação.
**Spec:** `docs/desenho-tecnico.md` e decisões confirmadas. Autorização: seguir próxima etapa, implementação direta no workspace existente.

## Global Constraints

- Primeira resposta 120min independente da prioridade; assumir não conta.
- NO_PRAZO <80%, EM_RISCO >=80% até o prazo inclusive, VENCIDO somente após prazo. Resultados finais CUMPRIDO/VIOLADO/NAO_APLICAVEL.
- Resolução pausa em espera; indicadores descontam pausa ainda aberta. Primeira resposta não pausa.
- Reclassificação só em chamados ativos por responsável compatível/Gestor; motivo obrigatório; preservar snapshots, tempo e violações anteriores.
- Políticas editadas afetam apenas novos chamados; não permitir excluir as quatro prioridades.
- Triagem explícita por N1, nunca solicitante do chamado ou Gestor sem perfil N1; pode anteceder assunção; após atribuição, só responsável N1 tria.
- Escalada N1→N2 exige triagem; mantém status e prazos, remove responsável. Não escalar espera/terminais. Autor manual responsável N1 ou Gestor; sem responsável, N1 do nível pode escalar após triagem.
- Automação: resolução >=80% em N1 ou crítico sem responsável >=10min desde abertura. Sem triagem apenas alertas. Primeira resposta >=80% também gera alerta sem transferir por esse motivo.
- Alertas únicos por ciclo/motivo; escalada única por chamado. N1 vê alertas no seu escopo N1, Gestor todos; N2/Solicitante não acessam alertas.
- Motivos de triagem/escalada são internos; não expor ao solicitante via API/Admin. Eventos somente equipe visível e não dono.
- Sem instalar agendador global: comando `verificar_sla` executa uma vez por padrão, `--continuo --intervalo 300` permite uso local; não iniciar processo permanente nesta sessão.

## Review Focus

1. Repriorizar depois de vencer e pausar/reabrir não pode apagar violações nem usar políticas novas.
2. Pausa aberta não pode ser contada duas vezes na alteração de prioridade e retomada.
3. Dono/nível errado não tria/escala, nem obtém motivos internos pelo Admin/eventos.
4. Job repetido e interação manual não duplicam alertas/escaladas nem modificam status terminal.
5. Leituras refletem horário atual sem job; filtros respeitam visibilidade e listas não geram N+1.

## Task 1 — Indicadores e políticas

Files: `apps/sla/{indicadores,services,models,serializers,views,urls}.py`, migrations e testes `tests/test_sla.py`.
Interfaces: `indicadores(chamado, agora=None) -> dict` com primeira_resposta/resolucao/status; `alterar_politica(*, politica, minutos_resolucao, ator, request=None)`; `alterar_prioridade(*, chamado_id, ator, prioridade, motivo, request=None)`.

- [x] Testar fronteiras de tempo, pausas abertas, finalização/cancelamento, prazo independente da prioridade, políticas e repriorização com violação preservada.
- [x] Observar falhas antes de implementar.
- [x] Adicionar flags de finalização/violação com backfill para dados existentes; calcular indicadores e expor nas respostas sem N+1.
- [x] Implementar GET/PATCH políticas para Gestor e POST prioridade; auditar e proteger campos.

## Task 2 — Triagem e eventos

Files: `apps/chamados/{models,services_escalonamento,serializers,views,urls,admin}.py` e testes `tests/test_escalonamento.py`.
Interfaces: `triar_chamado`, `escalar_chamado`, `escalar_bloqueado`; evento imutável por chamado/tipo com ator/motivo/dados allowlist.

- [x] Testar triagem antes/depois de assumir, dono N1, Gestor e N2, estado proibido, idempotência e sigilo.
- [x] Implementar ações e histórico de eventos, sem alterar histórico de status quando estado não muda.
- [x] Garantir retorno de níveis/responsável corretos e limites de mutação existentes.

## Task 3 — Job e alertas

Files: `apps/sla/{automacao,models,views,serializers}.py`, command `verificar_sla` e testes de job.
Interfaces: `verificar_sla(agora=None) -> dict` com contadores; processamento transacional por chamado.

- [x] Testar risco sem triagem (somente alerta), com triagem (N2), crítico aos10min, espera/terminais, replay e rollback de auditoria.
- [x] Implementar alertas deduplicados, filtros de acesso e comando único/contínuo com intervalo válido.
- [x] Integrar fechamento existente sem recriar eventos ou prolongar janela de reabertura.

## Task 4 — Verificação e documentação

- [x] Rodar suíte inteira, cobertura>=85%, Ruff, Bandit, checks/migrations e OpenAPI sem warnings.
- [x] Aplicar migrations e atualizar README/desenho; documentar execução periódica local sem Docker.
- [x] Revisão independente; achados importantes com regressão RED→GREEN e suíte completa.

## Registro

- Plano consolidado a partir das regras aprovadas; sem nova discussão de escopo ou frontend.

## Resultado verificado

- 179 testes passaram com SQLite, 49 novos nesta etapa. Cobertura global de apps: 98,08%.
- Servico de escalonamento, job e filtros com cobertura 100%; indicadores 98%, servicos SLA 99%.
- Ruff, formatacao, Bandit, checks Django, migration drift e OpenAPI passaram sem pendencias.
- Migrations chamados.0002, sla.0003 e sla.0004 aplicadas ao banco local; backfill de resultados existentes coberto por teste.
- Revisao independente sem achados importantes; 98 comparacoes independentes SQLite entre filtro SQL e indicador sem divergencias, incluindo fronteiras 80%/100% e pausa aberta.
- Violacoes de resolucao tardia registradas mesmo sem job, com regressao reproduzida RED e corrigida GREEN seguida de suite completa.
- Dados internos de triagem/escalada somente pela API da equipe, nunca pelo solicitante; EventoChamado nao registrado no Admin.
- Decisoes tecnicas: indicador geral resume o pior resultado; latch conserva vencimento em ciclo ativo mesmo apos ampliar prazo; primeira resposta ausente ao resolver e finalizada VIOLADO. Cancelamento interrompe obrigacoes pendentes, preservando conclusoes anteriores.
- Ajuste de portabilidade: CAST explicito de minutos para IntegerField na aritmetica de duracoes SQLite/PostgreSQL. Filtro executado no banco antes de paginar, sempre no queryset visivel.
- Modo continuo local implementado e testado com interrupcao simulada; nenhum processo permanente ou agendador global foi iniciado. Producao ainda requer configuracao de agendamento e verificacao PostgreSQL/locks.
- Sem Docker, Git, publicacao ou novas dependencias nesta etapa. README atualizado com rotas, regras e comandos.
- Proxima etapa: metricas de gestao e consulta de auditoria pela API.
