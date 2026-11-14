# Feature: permissions

**Keywords:** permissão, view_branch, owner, merge_branch, revert_branch, object-permissions
**Arquivos principais:**
  - netbox_branching/utilities.py (get_active_branch)
  - netbox_branching/api/views.py
  - netbox_branching/models/branches.py (owner)
**Resumo:** Quem pode ver, ativar, escrever, sincronizar, mergear e reverter branches.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1744 | Autorização para ativar branch | qualquer autenticado usa qualquer branch

## Estado atual
As actions da API checam permissões de modelo (ex.: `revert_branch`, `api/views.py:123`). **Ativar** um branch não checa nada: basta o `schema_id` (`utilities.py:607-646`). `owner` (`models/branches.py:191`) não restringe uso. A resposta 400 do middleware sai antes da autenticação e permite enumerar `schema_id`.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
—
