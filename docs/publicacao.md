# Preparação para GitHub

O repositório Git local foi inicializado na branch main. Nenhum repositório remoto, push ou release
foi criado nesta etapa. GitHub Actions ainda precisa rodar no repositório publicado.

## O que incluir

Código em apps/config, testes, scripts, migrations, uv.lock, documentação,
coleção Postman pública, ambiente exemplo vazio, licença MIT e configurações de CI.
O histórico de implementação em docs/superpowers/plans registra as verificações.

Não incluir .env, bancos SQLite, .demo, ambientes Postman privados, ferramentas,
caches, staticfiles ou skills locais de .agents. O .gitignore possui teste
automatizado com Git real para esses casos. .dockerignore também exclui credenciais.

## Verificação local

```powershell
python -m pytest
ruff check apps config tests scripts manage.py
ruff format --check apps config tests scripts manage.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file docs/openapi.yaml
python scripts/smoke_postman.py
```

O último comando precisa de Newman conforme docs/demo.md. Não valide o comando
seed contra dados de produção. Não há recuperação de senha ou verificação de
e-mail na v1; as limitações estão documentadas no README.

## Inicialização local do Git

O versionamento local usa seleção explícita dos arquivos. Para reproduzir em uma cópia sem Git:

```powershell
git init --initial-branch=main
git add .gitignore .gitattributes .dockerignore .github apps config collections docs scripts tests
git add .env.example
git add manage.py pyproject.toml uv.lock Dockerfile compose.yaml README.md LICENSE CHANGELOG.md plano-api-gestao-chamados.md
git status --short
git diff --cached --stat
git diff --cached --check
```

Revise o conteúdo selecionado antes do primeiro commit. Credenciais só podem
existir em arquivos locais ignorados; não use prints do ambiente privado na demo.
Defina título/descrição do repositório, identidade de autoria e destino do remoto
antes da publicação. A licença usa o nome coletivo Help Desk API contributors;
ajuste autoria se desejar antes de publicar.

## Ao publicar

- Criar repositório conforme visibilidade desejada e conectar o remoto correto.
- Enviar o código revisado e acompanhar os jobs de SQLite/PostgreSQL, Docker e Postman.
- Corrigir falhas antes de marcar release; não afirmar CI verde antes da execução.
- Adicionar links reais e badges no README somente quando existirem.
- Manter branch principal protegida e revisão de mudanças conforme o uso do projeto.

Hospedagem não é GitHub: o deploy Django/PostgreSQL e o agendamento de produção
serão configurados separadamente. Docker e PostgreSQL não foram executados
localmente nesta sessão; os jobs preparados no CI farão verificações adicionais.
