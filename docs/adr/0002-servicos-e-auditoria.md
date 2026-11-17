# ADR0002 — Serviços, selectors e rastreabilidade

Status: aceito.

Concentrar mutações em serviços transacionais e consultas de visibilidade em
selectors. Comparado a regras dispersas em views/serializers, isso permite que
API, job e seed chamem as mesmas operações com autorização/estado consistentes.

Separar histórico de status, eventos sem transição e auditoria por entidade.
Registros imutáveis bloqueiam update/delete/upsert no ORM comum e edição no Admin.
Queries de recursos ocultos retornam404; notas/eventos internos não são mostrados
ao solicitante, mesmo que tenha perfil Gestor.

Consequência: alterações diretas no banco não são cobertas pela garantia de
imutabilidade. Snapshots usam allowlist, sem conteúdo de notas, senhas ou tokens.
