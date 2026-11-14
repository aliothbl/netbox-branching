# SPEC-20261114-1744: Autorização para ativar e usar um branch

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:44
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** segurança, autorização, permissão, view_branch, owner, X-NetBox-Branch, schema_id, enumeração, 400-antes-de-auth
**Features:** permissions, routing
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1741 (códigos HTTP; a ordem auth → branch afeta ambas)
**Origem:** DIAGNOSTICO F11. Verificado no código em 2026-11-14 (`utilities.py:595-650`: nenhuma checagem de permissão).
**Resumo:** Ativar um branch (header, query param ou cookie) não exige permissão alguma sobre o objeto Branch. Basta conhecer o `schema_id`: qualquer usuário autenticado lê e escreve (dentro das suas permissões de modelo) em qualquer branch, e `owner` não restringe nada. A resposta 400 sai antes da autenticação e revela se um `schema_id` existe.

## Objetivo

`get_active_branch` faz `Branch.objects.get(schema_id=…)` e só verifica `ready` (`utilities.py:607-611,616-619,644-646`). Não usa `restrict(user, 'view')` nem permissão de objeto. O middleware roda antes da autenticação da API, então um cliente anônimo distingue um `schema_id` existente (400 "not ready") de um inexistente (400 "invalid identifier").

## Escopo

**DENTRO:**
- Ativar um branch exige `view` sobre o objeto Branch, via `Branch.objects.restrict(user, 'view')`, respeitando object permissions do NetBox.
- Escrever num branch exige uma permissão nova (`netbox_branching.use_branch` ou `change` no Branch, a decidir no journal), com regra opcional por `owner` configurável no plugin.
- Avaliar a ativação **depois** da autenticação (DRF autentica na view; ver como encaixar no request processor). Sem permissão, a resposta é idêntica a branch inexistente (404), para não haver enumeração.
- Migração de dados: conceder a nova permissão a quem hoje tem `view_branch`, para não quebrar instalações.
- Usuário de serviço do Diode: documentar a permissão necessária (o diode-netbox-plugin provisiona permissões no `post_migrate`).

**FORA:**
- Auditoria de quem ativou o quê.

## Invariantes
- NUNCA um usuário sem permissão sobre o Branch lê ou escreve no schema dele.
- Resposta para branch sem permissão == resposta para branch inexistente.

## Critério de aceite
- [ ] Teste: usuário sem `view` no Branch → 404 ao ativar por header, query param e cookie | verify: `./manage.py test netbox_branching.tests.test_branch_authorization`
- [ ] Teste: sem a permissão de escrita, escrita no branch é recusada e leitura funciona | verify: `./manage.py test netbox_branching.tests.test_branch_authorization`
- [ ] Teste: request anônimo não distingue `schema_id` existente de inexistente | verify: `./manage.py test netbox_branching.tests.test_branch_authorization`
- [ ] Migração concede a permissão nova a quem já tinha `view_branch` | verify: `./manage.py test netbox_branching.tests.test_branch_authorization`
