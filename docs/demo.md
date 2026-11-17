# Demonstração local

Requer Python 3.12 e dependências de desenvolvimento (`uv sync --frozen`). Docker,
Node e Postman não são necessários para usar a API pelo Swagger.

## Preparar

Com `.venv` ativo e SQLite local configurado:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

O comando cria cinco contas sem acesso ao Admin Django e onze chamados fictícios.
As senhas são aleatórias por conta e não aparecem no terminal. O ambiente privado
fica em `.demo/local.postman_environment.json`; abra somente localmente para usar
as credenciais no Swagger, ou importe no Postman. O diretório não é versionado.
Para Admin, continue usando um superusuário criado explicitamente com createsuperuser.

| Variável | Perfil |
|---|---|
| `solicitante_email` / `solicitante_password` | Solicitante principal |
| `outro_email` / `outro_password` | Segundo solicitante, para demonstrar isolamento |
| `n1_email` / `n1_password` | Analista N1 |
| `n2_email` / `n2_password` | Analista N2 |
| `gestor_email` / `gestor_password` | Gestor da API, sem privilégios administrativos |

Os endereços usam o domínio reservado `.example`; não representam pessoas reais.
Opcionalmente, `DEMO_PASSWORD` no ambiente pode definir uma senha forte comum;
ela passa pelos validadores do Django. A ausência dessa variável gera senhas distintas.
Não inclua seu valor em documentos, prints ou comandos versionados.

## Cenários

O ambiente exporta os IDs em variáveis, sem depender de IDs fixos no banco:

| Variável | Cenário inicial |
|---|---|
| `demo_aberto_id` | Aberto em N1 |
| `demo_atendimento_id` | Atendimento N1, resposta pública e nota interna |
| `demo_aguardando_id` | Espera pelo solicitante, SLA de resolução pausado |
| `demo_fila_n2_id` | Triado e escalado manualmente, aguardando N2 assumir |
| `demo_resolvido_id` | Resolvido recentemente, elegível a reabertura |
| `demo_fechado_id` | Fechado definitivamente por prazo |
| `demo_cancelado_id` | Cancelado pelo solicitante |
| `demo_reaberto_id` | Novo ciclo, primeira resposta e ciclo anterior preservados |
| `demo_critico_triado_id` | Crítico com triagem, elegível à escalada automática |
| `demo_critico_sem_triagem_id` | Crítico sem triagem: apenas alerta |
| `demo_outro_id` | Chamado de outro solicitante: deve retornar404 ao principal |

Para demonstrar automação imediatamente:

```powershell
python manage.py verificar_sla
```

O crítico triado passa para N2; o não triado permanece N1 e recebe alerta.
O seed não executa o job global; ele cria somente seus próprios cenários via
serviços de negócio. Datas são simuladas por freezegun apenas nesse comando de
desenvolvimento; a API e os jobs continuam usando o relógio real.

## Repetir sem apagar dados

`seed_demo` é idempotente: preserva senhas, alterações, status, histórico e políticas.
Os cenários envelhecem em tempo real; o comando não reinicia prazos ou chamados.
Colisões de e-mails ou categorias, inclusive por maiúsculas/minúsculas, abortam
sem reaproveitar contas alheias. O manifesto guarda somente IDs/UUID, nunca senhas.

Se o ambiente privado foi perdido ou você quiser redefinir as senhas do demo:

```powershell
python manage.py seed_demo --rotacionar-senhas
```

A rotação é explícita e restrita às contas próprias do manifesto; não altera
outros usuários ou chamados. Se uma conta demo recebeu acesso administrativo,
a rotação é recusada. Arquivos de outro manifesto não são sobrescritos.

Para uma demonstração limpa sem excluir o banco atual, escolha outro SQLite e
outro arquivo privado, mantendo o mesmo ambiente ao iniciar o servidor:

```powershell
New-Item -ItemType Directory -Force .demo
$env:SQLITE_PATH = '.demo/demo-novo.sqlite3'
python manage.py migrate
python manage.py seed_demo --ambiente .demo/demo-novo.postman_environment.json
python manage.py runserver
```

O destino deve terminar em `.postman_environment.json` e não pode ter sufixo
`.example.postman_environment.json`. Ambientes privados são ignorados pelo Git;
somente o exemplo público sem senhas é incluído. Produção mantém ALLOW_DEMO_SEED=False.

## Coleção Postman

Importe `collections/postman/helpdesk.postman_collection.json` e o ambiente
privado gerado. Selecione esse ambiente e execute a coleção inteira, na ordem,
pelo Runner. Ajuste `base_url` se o servidor não usar `http://127.0.0.1:8000`.

O fluxo autentica cada papel, abre um chamado novo, tria/assume, oculta notas
internas, pausa/retoma, escala N2, resolve/reabre/fecha e consulta métricas/auditoria.
No fim valida refresh, logout e rejeição do refresh revogado. Tokens/IDs são
capturados em variáveis; não há credenciais reais na coleção pública.
O uso de `pm.environment.set` segue a [referência oficial do Postman](https://learning.postman.com/docs/tests-and-scripts/write-scripts/postman-sandbox-reference/pm-variables/).

Cada rodada cria um novo chamado de fluxo. A coleção autentica quatro contas;
respeite o limite de dez logins por minuto ao repetir execuções no mesmo servidor.
`local.example.postman_environment.json` é apenas um modelo sem senhas e IDs;
não substitui o ambiente privado gerado.

## Validar com Newman (opcional)

Node é necessário somente para essa verificação, não para rodar Django.
Instale a ferramenta na pasta auxiliar ignorada, sem instalação global:

```powershell
npm.cmd install --prefix .tools-node --no-save --package-lock=false --ignore-scripts --cache .npm-cache newman@6.2.3
python scripts/smoke_postman.py
```

O script cria SQLite e ambiente temporários, aplica migrations, executa seed,
inicia servidor em porta livre de localhost, executa as29requisições/35asserções
e encerra a árvore do servidor. Não usa `db.sqlite3`, não imprime senhas e não
deixa um servidor persistente. A pasta temporária é removida ao terminar.

Para regenerar os JSON públicos após editar a definição da coleção:

```powershell
python scripts/gerar_colecao.py
```
