# Feature: provisioning

**Keywords:** provisioning, schema, branch_<id>, snapshot, cópia-paralela, sequence, nextval
**Arquivos principais:**
  - netbox_branching/provisioning.py
  - netbox_branching/models/branches.py (provision)
**Resumo:** Cria o schema PostgreSQL do branch copiando as tabelas do main a partir de um snapshot exportado.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1745 | Sequences de tabelas novas na migração | colisão de ID (plausível)

## Estado atual
Cada branch é um schema `branch_<schema_id>`. As tabelas são copiadas em paralelo a partir de um snapshot exportado (token validado por regex). O `id` das tabelas copiadas usa a **sequence do main** (`provisioning.py:359-368`), e é isso que evita colisão de IDs no merge. Identificadores via `quote_ident`; sem SQL montado com string de usuário.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261114-1745 | Só o provisionamento religa as sequences; `migrate()` não (2026-11-14 17:45)
