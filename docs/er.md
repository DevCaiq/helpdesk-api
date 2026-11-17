# Modelo de dados

```mermaid
erDiagram
    USUARIO ||--o{ CHAMADO : solicita
    USUARIO o|--o{ CHAMADO : atende
    CATEGORIA ||--o{ CHAMADO : classifica
    CHAMADO ||--o{ COMENTARIO : recebe
    CHAMADO ||--o{ HISTORICO_STATUS : registra
    CHAMADO ||--o{ EVENTO_CHAMADO : possui
    CHAMADO ||--|{ CICLO_RESOLUCAO : possui
    CICLO_RESOLUCAO ||--o{ PAUSA_SLA : pausa
    CICLO_RESOLUCAO ||--o{ ALERTA_SLA : gera
    USUARIO o|--o{ LOG_AUDITORIA : atua
    USUARIO {
        bigint id PK
        string email UK
        string perfil
        string nivel
    }
    CHAMADO {
        bigint id PK
        bigint solicitante_id FK
        bigint responsavel_id FK
        bigint categoria_id FK
        string status
        string prioridade
        string nivel_atual
        json sla_snapshot
        datetime triado_em
    }
    CICLO_RESOLUCAO {
        bigint id PK
        bigint chamado_id FK
        datetime inicio
        datetime prazo
        datetime encerrado_em
        string resultado
        datetime violado_em
    }
    POLITICA_SLA {
        bigint id PK
        string prioridade UK
        int minutos_resolucao
    }
    DEMO_DATASET {
        bigint id PK
        string chave UK
        uuid uid UK
        json dados
    }
```

A política não possui FK no chamado: suas durações são copiadas no snapshot para
preservar comportamento após alterações. Primeira resposta é obrigação por chamado;
resolução é por ciclo. Só pode existir um ciclo aberto por chamado e uma pausa
aberta por ciclo. Uma escalada por chamado e um alerta por ciclo/motivo.

Usuários/categorias usados são protegidos contra exclusão. Campos de autor de
histórico/evento/auditoria podem ser nulos para o sistema. O manifesto demo guarda
IDs/UUID e referência temporal, sem FKs ou senhas; sua integridade é conferida pelo seed.
