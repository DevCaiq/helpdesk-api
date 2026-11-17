# ADR0001 — Django REST Framework e bancos por ambiente

Status: aceito, conforme decisões do responsável.

Usar Python3.12, Django5.2 LTS, DRF e uv com lockfile. Desenvolvimento e testes
padrão usam SQLite para começar sem Docker ou serviço externo. Produção exige
PostgreSQL; settings de produção rejeita SQLite.

Alternativa: PostgreSQL também local. Foi adiada a pedido do responsável para
reduzir a preparação da máquina. Consequência: testes SQLite não provam locks e
concorrência PostgreSQL; CI preparado executa a suíte nos dois bancos.
