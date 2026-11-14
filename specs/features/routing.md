# Feature: routing

**Keywords:** routing, X-NetBox-Branch, _branch, cookie, active_branch, contextvar, BranchAwareRouter, DynamicSchemaDict, search_path, BranchMiddleware, supports_branching
**Arquivos principais:**
  - netbox_branching/utilities.py (get_active_branch, supports_branching, ActiveBranchContextManager, DynamicSchemaDict)
  - netbox_branching/database.py (BranchAwareRouter)
  - netbox_branching/middleware.py (BranchMiddleware)
  - netbox_branching/contextvars.py
**Resumo:** Decide qual branch está ativo em cada request e manda as queries ORM ao schema correto.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1741 | Códigos HTTP para branch indisponível | 400 para tudo
- SPEC-20261114-1742 | Fast-path do router | custo por query sem branch
- SPEC-20261114-1744 | Autorização para ativar branch | sem checagem
- SPEC-20261114-1746 | Conexões por branch | N×W conexões (plausível)

## Estado atual
Branch ativo vem do header `X-NetBox-Branch` (API), de `?_branch=` ou do cookie (`utilities.py:595-650`). Não há checagem de permissão nem de `owner`. O request processor `ActiveBranchContextManager` (`utilities.py:693`) põe o branch na contextvar `active_branch`. `BranchAwareRouter._get_db` (`database.py:24-37`) chama `supports_branching(model)` **antes** de olhar a contextvar. `supports_branching` (`utilities.py:244-293`) recalcula tudo a cada chamada (`# TODO: Make this more efficient`). `BranchMiddleware` (`middleware.py:44-56`) resolve o branch de novo e devolve **400** para branch inexistente ou não-READY. Cada branch usado vira um alias `schema_<id>` com `search_path=branch,public` e conexão própria (`utilities.py:93-142`).

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261114-1742 | `BranchMiddleware.__call__` aparece em toda stack de py-spy, mas o custo próprio dele é pequeno; o custo está no router (2026-11-14 17:42)
- SPEC-20261114-1741 | Até a v1.2.0, `get_active_branch` devolvia um `HttpResponseBadRequest` que era ativado como se fosse branch → 500 (#672, corrigido na 1.2.x) (2026-11-14 17:41)
