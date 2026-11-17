# Autenticação e usuários — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Entregar JWT, cadastro público seguro, gestão de usuários e auditoria das operações dessa etapa.
**Architecture:** Views finas com serializers explícitos, serviços transacionais e permissões por perfil consultadas no banco. Auditoria é inserida na mesma transação das alterações de usuários; falhas de login não armazenam credenciais.
**Tech Stack:** Django 5.2, DRF, SimpleJWT já instalados, SQLite local, pytest.
**Spec:** `docs/desenho-tecnico.md`, seção Contratos de API. Execução autorizada pelo usuário; sem Docker/publicação.

## Global Constraints

- Access 15min, refresh 7 dias, rotação e blacklist; logout revoga refresh próprio, não access emitido.
- Cadastro público apenas SOLICITANTE; perfil/nivel/flags de privilégio rejeitados explicitamente.
- Somente GESTOR lista, cria equipe e altera perfil/nível/ativo. Criar Gestor não concede admin Django.
- Nome obrigatório na API; senha write-only, validadores Django; e-mail único sem distinção de caixa.
- Respostas inválidas: envelope error/code/message/details; 401 sem autenticação, 403 sem perfil.
- Trabalho direto no workspace escolhido, sem Git e sem commits/publicação nesta etapa.

## Review Focus

1. Tentativa de mass assignment de campos privilegiados no cadastro.
2. Refresh de usuário desativado ou excluído, token malformado/expirado/rotacionado.
3. Logout de outro usuário; papéis alterados devem valer inclusive com access já emitido.
4. Troca parcial de perfil/nível não pode violar integridade; evitar autodesativação/rebaixamento do Gestor pela API.
5. Senhas/tokens não podem aparecer nas respostas ou auditoria; histórico não pode ser alterado pelo ORM comum.

## Task 1 — Cadastro e autorização

Files: `apps/usuarios/{serializers,services,permissions,views,urls}.py`, `apps/core/{exceptions,pagination}.py`, `config/{urls.py,settings/base.py}`, `tests/test_api_usuarios.py`.
Interfaces: `criar_usuario(*, dados, ator=None, request=None) -> Usuario`; `alterar_usuario(*, usuario, dados, ator, request=None) -> Usuario`; `IsGestor.has_permission(request, view)`.

- [x] Criar testes de cadastro, duplicidade, senha fraca, rejeição de privilégios, me protegido e autorização por perfil.
- [x] Rodar testes e observar 404 antes da implementação.
- [x] Implementar POST/GET usuarios/, GET me/, POST staff/, PATCH {id}/ e paginação 20/máximo100.
- [x] Testar mudança de perfil/nível, conta inativa, autorrestrições e permissões com JWT real.

## Task 2 — JWT e auditoria

Files: `apps/usuarios/{auth_serializers,auth_views}.py`, `apps/auditoria/{models,services,admin,apps}.py`, migration, `tests/test_api_auth.py`, `tests/test_auditoria.py`.
Interfaces: `registrar_evento(*, acao, ator=None, entidade_id=None, antes=None, depois=None, request=None) -> LogAuditoria` com allowlist dos campos de usuário; sem corpo completo da requisição.

- [x] Testar login/refresh/logout, expiração, tokens inválidos, replay, ownership, usuário inativo e excluído, com relógio controlado.
- [x] Observar falha pelos endpoints ausentes.
- [x] Configurar JWT e implementar views, logout validando ownership e refresh tratando usuário excluído.
- [x] Criar auditoria append-only via model/queryset/admin e integrá-la à criação, alteração e login/logout.
- [x] Testar login falho/sucesso, ausência de segredos e atomicidade das alterações.
- [x] Configurar throttles de login/cadastro/escrita com escopos distintos e testar limite 429.

## Task 3 — Documentação e validação

Files: `docs/openapi.yaml`, README, este registro.

- [x] Documentar payloads, respostas e exemplos no OpenAPI com extend_schema.
- [x] Rodar suíte inteira com cobertura >=85%, Ruff, Bandit, Django check, migration drift e schema sem warnings.
- [x] Aplicar migrations locais; revisar segurança com revisor independente antes do relatório final.

## Registro

- Planejamento escrito; usar serviços e exceções compartilhados entre tarefas para manter transações e respostas consistentes.
- Context7 consultado, mas retornou ferramenta indisponível; documentação oficial e código instalado usados como fallback.

## Resultado verificado

- 71 testes passaram com SQLite; cobertura de apps: 97,64%.
- Ruff, formatação, Bandit, Django check, migration drift e OpenAPI passaram.
- Migration de auditoria aplicada ao SQLite local.
- Revisão independente encontrou bypass por bulk_create(update_conflicts=True); regressão reproduzida (RED) e bloqueada (GREEN), seguida de suíte completa verde. Nenhum outro achado importante.
- Decisões técnicas: bloquear autodesativação/rebaixamento do Gestor; correção de importação tardia do relógio de throttle nos testes; enums de perfis distintos no schema.
- Limitações: cache de throttle local por processo; configurar cache/proxy compartilhado na implantação. Imutabilidade não cobre SQL direto. Sem execução local de Docker/PostgreSQL, conforme escopo.
- Próxima etapa: núcleo de chamados, histórico, comentários e ampliação de auditoria.
