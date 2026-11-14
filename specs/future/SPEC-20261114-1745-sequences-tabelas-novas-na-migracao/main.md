# SPEC-20261114-1745: Sequences compartilhadas para tabelas criadas por migração no branch

**Status:** draft
**Porte:** P
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:45
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** migrate, sequence, nextval, colisão-de-id, provisioning, pending-migrations, schema-drift
**Features:** migrations, provisioning
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** —
**Origem:** DIAGNOSTICO F12 (plausível; confirmar com teste antes de corrigir).
**Resumo:** No provisionamento, as tabelas copiadas para o branch apontam o `id` para a sequence do main, e isso evita colisão de IDs no merge (`provisioning.py:359-368`). Uma tabela **nova**, criada quando `migrate()` roda dentro do branch, ganha sequence própria (`models/branches.py:1043-1113`). Os IDs criados nela podem colidir com os do main no merge.

## Objetivo

Confirmar com teste e, se for real, fazer `migrate()` religar as sequences das tabelas novas ao main, como o provisionamento faz.

## Escopo

**DENTRO:**
- Teste que reproduz: branch provisionado → plugin ou NetBox com migration que cria tabela → `migrate()` no branch → criar objeto no branch e no main → merge.
- Se reproduzir: após `migrate()`, aplicar a mesma religação de sequence do provisionamento a toda tabela do schema do branch que não aponta para a sequence do main.

**FORA:**
- Migrations que **removem** tabelas.

## Invariantes
- IDs criados no branch nunca colidem com IDs do main, para tabelas antigas e novas.

## Critério de aceite
- [ ] Teste de reprodução registrado (falha antes ou refuta F12 com evidência) | verify: `./manage.py test netbox_branching.tests.test_migrate_sequences`
- [ ] Se confirmado: merge sem colisão depois da correção | verify: `./manage.py test netbox_branching.tests.test_migrate_sequences`
