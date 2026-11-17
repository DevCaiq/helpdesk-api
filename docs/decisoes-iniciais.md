# Gestão de Chamados — decisões iniciais

Consolidado em 2026-11-16 a partir das respostas do responsável pelo projeto.
Complementa o plano original; não representa implementação concluída.

## Objetivo e ambiente

- Projeto de portfólio, com regras funcionais para atendimento em equipe.
- API REST, Swagger e Django Admin; frontend fora da primeira versão.
- Workspace: `D:\gsti`. Publicação no GitHub após finalizar localmente; hospedagem ainda não escolhida.
- Python, Django 5.2 LTS, Django REST Framework, uv e Docker.
- Atualizado por solicitação do responsável: desenvolvimento local e testes usam SQLite; PostgreSQL somente em produção. `.venv` criado e dependências instaladas via uv.
- Recomendação técnica: testes adicionais com PostgreSQL para concorrência, bloqueios e constraints; SQLite não comprova esses comportamentos em produção.
- Agendamento por management command, sem Celery nesta versão.

## Atendimento e SLA confirmados

- Chamados nascem em N1; solicitantes não escolhem N2.
- Assumir altera ABERTO ou REABERTO para EM_ATENDIMENTO e registra histórico; não conta como primeira resposta.
- Primeira resposta: primeiro comentário público de atendimento por Analista ou Gestor.
- Prazo inicial de primeira resposta: 2 horas após abertura, independentemente da prioridade. Substitui a tabela original de primeira resposta.
- Indicadores de primeira resposta e resolução são separados.
- SLA em tempo corrido, com timestamps conscientes de fuso e persistência em UTC.
- AGUARDANDO_SOLICITANTE exige resposta pública de atendimento e pausa apenas resolução.
- Reabrir inicia novo ciclo de resolução, preserva ciclos anteriores e não reinicia primeira resposta.
- Alterações de política valem apenas para novos chamados; parâmetros aplicados devem ser preservados.
- Somente Analista ou Gestor altera prioridade. Recalcular desde o início do ciclo, preservando pausas e violações já registradas.
- Prazos de resolução do plano original continuam como referência: crítica 4h, alta 8h, média 24h e baixa 72h.

## Resolução e fechamento

- Solicitante dispõe de 2 dias para reabrir após resolução.
- Fechamento automático após 2 dias sem interação do solicitante.
- FECHADO é terminal; reabertura ocorre a partir de RESOLVIDO.
- Gestor também pode reabrir dentro da janela, com justificativa, conforme proposta aceita anteriormente.
- Confirmado: 2 dias correspondem a 48 horas corridas. A janela de reabertura é fixa desde a resolução; comentários do solicitante reiniciam somente o contador de fechamento automático. Um comentário público não reabre por si só um chamado RESOLVIDO: a reabertura exige ação explícita. Após FECHADO, nenhuma edição, comentário ou reabertura é permitida, inclusive pelo Gestor.
- Limite temporal proposto: reabertura permitida antes de completar 48h; a partir de 48h o job pode fechar, se também satisfeita a inatividade. API e job devem serializar operações concorrentes.

## Atribuição e escalonamento

- Analista assume chamado sem responsável e compatível com seu nível.
- Somente responsável ou Gestor conduz atendimento.
- Escalada manual exige justificativa, mantém status, remove responsável e transfere para fila N2.
- Analista N2 assume o chamado transferido antes de conduzir atendimento.
- Automação após triagem N1: resolução em risco em N1, ou prioridade crítica sem responsável por 10 minutos desde a abertura. Antes da triagem, essas condições geram apenas alerta, nunca transferência para N2.
- AGUARDANDO_SOLICITANTE, RESOLVIDO, FECHADO e CANCELADO não escalam automaticamente.
- Confirmado: triagem humana N1 é obrigatória antes de qualquer transferência para N2. Solicitante não pode realizá-la.
- Decisão técnica proposta: ação explícita de triagem, com analista N1, data e justificativa registrados; assumir não marca triagem automaticamente. Gestor não substitui essa etapa na primeira versão.

## Acesso e edição

- Cadastro público cria apenas Solicitantes; Gestor cria Analistas e Gestores.
- Solicitante edita título, descrição e categoria somente em ABERTO; após isso, complementa por comentários.
- Notas internas são ocultas para o solicitante do chamado, mesmo que também seja Analista.
- Visibilidade do Analista deve incluir seus próprios chamados como solicitante, fila do seu nível e chamados atribuídos a ele; acesso não implica autorização de conduzir atendimento.
- Perfil de negócio não concede automaticamente is_staff ou is_superuser.

## Correções necessárias no plano de execução

1. Criar usuário customizado e AUTH_USER_MODEL antes da primeira migration.
2. Antecipar models mínimos de política, ciclo de SLA, histórico e auditoria ao núcleo de chamados.
3. Acrescentar impacto, urgência, referência/snapshot da política, ciclos de resolução e eventos de escalonamento à modelagem.
4. Separar testes resolver → reabrir e resolver → fechar.
5. Usar pyproject.toml e uv.lock consistentemente em desenvolvimento, CI e Docker.
6. Definir contratos de alteração de prioridade, políticas, métricas e campos editáveis por perfil/estado.
7. Registrar concorrência, idempotência, integridade e limites da imutabilidade na arquitetura.

## Situação

Desenho aprovado em 2026-11-16. Conflito sobre triagem resolvido. Início pela fundação do projeto; andamento e verificações registrados no plano de implementação.
