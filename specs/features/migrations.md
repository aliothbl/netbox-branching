# Feature: migrations

**Keywords:** migrate, pending-migrations, schema-drift, sequence
**Arquivos principais:**
  - netbox_branching/models/branches.py (migrate)
**Resumo:** Aplica migrations do NetBox/plugins nos schemas dos branches.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1745 | Sequences de tabelas novas | colisão de ID (plausível)

## Estado atual
Branch com migrations pendentes fica em `pending-migrations` e é recusado pelo middleware (hoje com 400). `migrate()` (`models/branches.py:1043-1113`) aplica as migrations no schema sem religar sequences de tabelas novas.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
—
