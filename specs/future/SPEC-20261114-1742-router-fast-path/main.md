# SPEC-20261114-1742: Custo zero do roteamento em requests sem branch

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:42
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** performance, router, BranchAwareRouter, supports_branching, memoização, contextvar, active_branch, ChangeDiff, signal, middleware, reverse
**Features:** routing, change-tracking
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1736 (cenário `router-overhead` = antes/depois)
**Origem:** DIAGNOSTICO F7, F8 e F9. F7 verificado no código em 2026-11-14 (`database.py:31-35`, `utilities.py:244-293`).
**Resumo:** Com o plugin instalado, **toda query ORM de todo request** paga a classificação do modelo antes de o router checar se há branch ativo. Cada UPDATE/DELETE no main paga um SELECT em ChangeDiff, e requests com header buscam o branch duas vezes. O objetivo é que um NetBox com o plugin e sem branch ativo custe o mesmo que sem o plugin.

## Objetivo

- **F7:** `_get_db` chama `supports_branching(model)` (`database.py:31`) antes de `active_branch.get()` (`:35`). A cada query, `supports_branching` monta f-strings, percorre os resolvers de plugins, chama `apps.get_model`, `issubclass` e `get_plugin_config` e monta uma lista nova de modelos isentos. O próprio código marca `# TODO: Make this more efficient` (`utilities.py:288`). É o caminho de **todo** write do Diode no main.
- **F8:** o handler de ObjectChange faz um SELECT em `ChangeDiff` para todo UPDATE/DELETE no main, mesmo sem nenhum branch existente (`signal_receivers.py:124-136`).
- **F9:** com header, o branch é buscado duas vezes por request (request processor e middleware), e há cerca de 5 `reverse()` por request (`utilities.py:576-583,693-721`; `middleware.py:47,52,62`).

## Escopo

**DENTRO:**
- `_get_db`: checar `active_branch.get()` primeiro. Sem branch, retornar `None` imediatamente. Exceção: `core.ObjectChange` mantém a lógica atual.
- Memoizar `supports_branching` por classe de modelo, com invalidação quando um resolver é registrado (`register_branching_resolver`) e config de isentos lida uma vez.
- F8: pular o SELECT quando não existe branch ativo (READY) que possa conter o objeto. Contagem barata e cacheada, invalidada por signal de Branch.
- F9: resolver o branch uma vez por request, guardando no request, e pré-computar os paths isentos.

**FORA:**
- Mudanças no NetBox core.

## Invariantes
- Roteamento idêntico ao atual para todo modelo e todo estado de branch (os testes de routing existentes cobrem; adicionar os que faltarem).
- Modelos históricos de migration (`StateApps`) continuam classificados pelo modelo vivo (comentário em `utilities.py:267-272`).

## Critério de aceite
- [ ] Teste de equivalência: para todo modelo registrado, `supports_branching` memoizado == implementação atual | verify: `./manage.py test netbox_branching.tests.test_routing`
- [ ] `assertNumQueries` no caminho de UPDATE no main sem branch: zero queries em `netbox_branching_changediff` | verify: `./manage.py test netbox_branching.tests.test_routing`
- [ ] Cenário `router-overhead` (SPEC-1736): throughput com plugin e sem branch ativo ≥ 97% do throughput sem o plugin | evidence: manual @aliothbl
