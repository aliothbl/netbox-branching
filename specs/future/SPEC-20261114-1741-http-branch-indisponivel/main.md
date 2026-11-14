# SPEC-20261114-1741: Códigos HTTP corretos para branch indisponível

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:41
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** http-400, 503, Retry-After, 409, 410, BranchNotReady, X-NetBox-Branch, diode, reconciler, branch-padrão
**Features:** routing, integration-diode
**Branch:** _(a definir na ativação)_
**Programa:** `aliothbl/diode:specs/programs/diode-stack-hardening.md`
**Relacionadas:**
  - `aliothbl/diode:specs/future/SPEC-20261114-1748-retry-branch-indisponivel` (**par obrigatório**: o reconciler consome estes códigos)
  - SPEC-20261114-1738 (durante o lock do merge/sync, os clientes recebem o código definido aqui)
**Origem:** DIAGNOSTICO F6. Verificado no código em 2026-11-14 (`middleware.py:51-56`).
**Resumo:** Hoje todo request para um branch que não está READY recebe `400 Bad Request`, inclusive durante um sync de minutos. O 400 diz "o request está errado, não repita", e o reconciler do Diode marca o lote como falha. O status passa a dizer se a condição é transitória ou permanente.

## Objetivo

`BranchMiddleware` devolve `HttpResponseBadRequest('Selected branch is not ready.')` para `BranchNotReady` (`middleware.py:55-56`) e `400 'Invalid branch identifier'` para branch inexistente (`:53-54`). Para o Diode isso causa dois problemas:
- **Status transitório** (provisioning, syncing, merging, migrating, reverting): um sync no branch padrão transforma toda a ingestão do intervalo em falha.
- **Status terminal** (merged, archived, failed): o Setting de branch padrão do diode-netbox-plugin continua apontando para o branch, e a ingestão falha **para sempre**. Os 400 não se distinguem de um payload inválido.

## Escopo

**DENTRO:**
- Status transitório → `503 Service Unavailable` + `Retry-After` (estimativa configurável).
- Status terminal (merged, archived, failed, pending-migrations) → `409 Conflict`. Inexistente → `404 Not Found`.
- Corpo JSON nas requisições de API com `{"branch": <schema_id>, "status": <status>, "retryable": bool}`. A UI mantém o comportamento atual (mensagem + redirect).
- Documentar o contrato em `docs/rest-api.md` (no fork, sob `specs/`, até haver PR upstream).

**FORA:**
- O comportamento do reconciler → SPEC par no diode.
- Autorização para ativar o branch → SPEC-20261114-1744.

## Invariantes
- Request de API para branch indisponível NUNCA recebe 400. 400 fica reservado para payload inválido.
- O contrato (código + campos do corpo) é o que a SPEC par do diode consome. Mudar exige atualizar as duas SPECs.

## Critério de aceite
- [ ] Testes de API para cada status: transitório → 503 com `Retry-After`; terminal → 409; inexistente → 404; corpo JSON com `retryable` | verify: `./manage.py test netbox_branching.tests.test_api_branch_status`
- [ ] UI sem mudança de comportamento (testes de view existentes verdes) | verify: `./manage.py test netbox_branching.tests`
