# Demonstração local e preparação do repositório — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans com testes antes da implementação e revisão independente final.

**Goal:** Entregar seed_demo seguro/idempotente, cenários reproduzíveis, coleção Postman executável e arquivos de preparação para GitHub, sem publicação.
**Architecture:** App demo mantém manifesto de IDs/UUID sem senhas; criação usa serviços existentes em uma transação. Simulação histórica usa freezegun somente no comando de desenvolvimento. Ambiente Postman privado fica em .demo/, coleção pública contém apenas variáveis.
**Tech Stack:** Django, SQLite, pytest/freezegun existentes; Postman Collection v2.1 e Newman opcional para validar a coleção HTTP real. Nenhuma dependência adicional de runtime.
**Spec:** desenho técnico aprovado, seed_demo e coleção do plano original. Trabalho em D:\gsti, sem Git ou publicação.

## Global Constraints

- Seed permitido somente em configurações de desenvolvimento/teste por ALLOW_DEMO_SEED; produção desabilitada. freezegun importado somente após essa verificação.
- Cinco contas: dois Solicitantes, Analista N1, Analista N2 e Gestor, sem is_staff/is_superuser.
- Senhas fortes aleatórias por conta; DEMO_PASSWORD opcional deve passar validadores Django. Não imprimir credenciais, gravar em manifesto ou versionar ambiente privado.
- Onboarding pela API não muda; seed é comando local explícito, não etapa automática de inicialização.
- Manifesto único portfolio-v1 com IDs/UUID e referência temporal. Reexecução preserva contas, estados, histórico, senhas e políticas existentes.
- Colisão com e-mails/categorias não pertencentes ao manifesto aborta sem alteração. Manifesto inválido não autoriza redefinir conta alheia.
- Rotação de senhas somente com --rotacionar-senhas explícito, restrita às contas próprias do manifesto, nunca contas com flags administrativas.
- Artefato existente de outro manifesto não pode ser sobrescrito. Falha de exportação reverte alterações do banco; arquivos são escritos atomicamente.
- Cenários: aberto, atendimento N1 com nota interna, aguardando solicitante, fila N2, resolvido, fechado, cancelado, reaberto, crítico triado elegível a automação, crítico não triado e chamado de outro solicitante.
- Criar eventos via serviços com relógio simulado, sem update/delete do histórico. Seed não executa job global nem modifica chamados alheios.
- Coleção usa variáveis, salva tokens/IDs em ambiente, cobre ciclo completo e controles de acesso. Preparar ambiente exemplo vazio e privado gerado; repetir coleção cria um novo chamado de fluxo, não reabre fechados.
- Adicionar licença MIT conforme plano original, gitignore/dockerignore para dados locais/ferramentas, gitattributes e checklist de publicação; não criar remoto ou push.

## Review Focus

1. Reexecutar seed não pode alterar tickets interativos nem sobrescrever senhas/perfis.
2. Colisão de identidade e manifesto adulterado não pode causar elevação ou reset de conta alheia.
3. Falha no arquivo privado não pode deixar contas/dataset parcialmente criados.
4. Históricos/pausas/SLA devem ter cronologia coerente e automação deve demonstrar N2 somente após triagem.
5. Coleção e documentos públicos nunca devem conter senhas/tokens reais; scripts devem funcionar em execução HTTP real.

## Task 1 — Dataset e comando

Files: apps/demo/{apps,models,services,exportacao,cenarios}.py, migration, command seed_demo, settings e tests/test_demo.py.
Interface: seed_demo(*, ambiente, rotacionar=False) -> dict com IDs/UUID/criado; comando --ambiente PATH opcional.

- [x] Escrever testes de seed, reexecução após mudança, colisão, flag de produção, rotação explícita, manifesto inválido e falha de exportação.
- [x] Observar comando ausente.
- [x] Implementar manifesto, criação auditada e exportação privada; cenário temporal depende apenas de extras dev já instalados.
- [x] Validar estados, IDs e ausência de credenciais no output/DBmanifesto.

## Task 2 — Coleção e materiais

Files: collections/postman/, docs/demo.md, docs/publicacao.md, LICENSE, CHANGELOG.md, .gitattributes, ignores e scripts de smoke.

- [x] Criar coleção v2.1 e ambiente exemplo sem valores secretos; scripts pm.environment.set e testes de status/visibilidade.
- [x] Verificar JSON e executar coleção via Newman contra servidor temporário com SQLite isolado.
- [x] Preparar arquivos de publicação, sem criar repositório remoto ou credenciais compartilhadas.

## Task 3 — Validação e entrega

- [x] Aplicar migration local e executar seed autorizado, sem imprimir credenciais geradas.
- [x] Rodar suíte completa, Ruff, Bandit, schema OpenAPI e migration drift.
- [x] Revisão independente, correções importantes com teste RED→GREEN e atualização README.

## Registro

- Node está disponível; Newman será instalado apenas em diretório auxiliar ignorado, para verificação.
- Formato de variáveis conferido na documentação oficial do Postman; schema público v2.1 será usado na validação por Newman.

## Resultado verificado

- 258 testes passaram em SQLite, 22 novos nesta etapa; cobertura global apps 97,96%.
- Newman6.2.3 executou29requisicoes e35assercoes HTTP reais, zero falhas, com SQLite/servidor temporarios. Corrigido encerramento da arvore do launcher Windows; smoke terminou com exit0 e limpeza dos temporarios.
- Ruff, formatacao, Bandit, checks Django, migration drift e OpenAPI passaram.
- Demo migration aplicada ao banco local; seed executado com sucesso, criando5contas e11chamados. Senhas nao impressas; ambiente em .demo/local.postman_environment.json ignorado.
- Revisao independente identificou colisao de categoria por maiusculas/minusculas; regressao reproduzida RED e corrigida GREEN. Guarda CI tambem cobre e-mails legados nao normalizados.
- Falha apos publicacao do ambiente e falha de rotacao foram reproduzidas e corrigidas com rollback do banco e limpeza/restauracao do arquivo proprio. Cronologia de criacao de atores/categorias anterior aos chamados historicos coberta por teste.
- Seed nao executa automacao global; teste garante que chamado alheio elegivel nao e escalado durante seed. Reexecucao preserva alteracoes e senhas, sem reset implicitamente.
- Ambientes privados exigem sufixo postman_environment.json, sem example; Git ignora esses arquivos e inclui apenas exemplo vazio. Regra validada usando Git em repositorio temporario, inclusive Windows stdin NUL.
- Preparados README, guia demo/publicacao, arquitetura, ER, estados, ADRs, MIT, changelog, gitattributes e job Postman no CI.
- Nenhum repositorio Git local/remoto, push ou release criado nesta etapa. Docker/PostgreSQL/CI remoto continuam pendentes de ambiente/publicacao.
- Newman e ferramenta opcional instalada somente em .tools-node ignorado; nenhuma nova dependencia de runtime Python. Freezegun somente no seed dev/teste, apos guarda de producao.
- Proxima etapa: revisao de entrega e publicacao no GitHub.
