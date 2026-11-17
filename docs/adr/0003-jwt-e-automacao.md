# ADR0003 — JWT e management commands

Status: aceito.

JWT com access15min, refresh7dias, rotação e blacklist facilita clientes REST.
O perfil é consultado no banco, evitando que um claim antigo mantenha permissões
revogadas. Logout revoga refresh; access existente dura até expirar, salvo conta
desativada. Recuperação de senha/verificação de e-mail ficam fora da primeira versão.

Usar management command para SLA, alertas, escalonamento e fechamento. Celery/Redis
foram adiados para manter o ambiente local simples. Modo contínuo permite demo;
produção requer agendamento/supervisão conforme a hospedagem escolhida.

Seed de demonstração é explícito e só habilitado em dev/teste; freezegun é usado
apenas para compor os cenários históricos. Não há criação automática de contas
conhecidas na inicialização da API ou em produção.
