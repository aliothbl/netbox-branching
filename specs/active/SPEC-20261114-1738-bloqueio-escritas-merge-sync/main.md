# SPEC-20261114-1738: Nenhuma escrita no branch se perde durante merge ou sync

**Status:** active
**Porte:** G
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:38
**Ativada:** 2026-11-15 19:39
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** merge, sync, perda-de-dados, advisory-lock, pg_advisory_xact_lock, janela, changelog, drop-schema, archive, diode
**Features:** sync-merge-revert, routing, integration-diode
**Branch:** `spec/20261114-1738-bloqueio-escritas-merge-sync`
**Programa:** —
**Relacionadas:** SPEC-20261114-1737 (status antes da leitura do changelog); SPEC-20261114-1736 (cenário `branch-merge-race`); SPEC-20261114-1741 (o que o cliente recebe enquanto o lock existe)
**Origem:** DIAGNOSTICO F2 (crítico). Verificado no código em 2026-11-14 (`models/branches.py:1147-1156`).
**Resumo:** Fechar a janela em que um request que já passou pela checagem de `ready` grava no schema do branch depois que o merge (ou sync) leu o changelog. Hoje essas escritas nunca chegam ao main, e o `DROP SCHEMA` do archive as apaga.

## Objetivo

`merge()` materializa o changelog do branch (`get_unmerged_changes()`, `len(changes)`, linha 1148) e só depois muda o status para MERGING (1156). O comentário do código diz isso: *"Retrieve staged changes before we update the Branch's status"*. A checagem de `ready` dos requests só acontece no início de cada request (`utilities.py:609-611`). Um request que começou antes, como um `bulk-plan-apply` do Diode que leva dezenas de segundos, continua gravando no schema do branch depois da leitura.
1. Essas mudanças ficam no schema do branch e não entram no merge.
2. O branch vai para MERGED sem aviso.
3. No archive (manual ou auto-archive), `DROP SCHEMA` apaga os dados para sempre.

O sync tem a janela equivalente (leitura em `:949`, status em `:957`) com escritas concorrentes no mesmo schema.

## Escopo

**DENTRO:**
- Lock por branch no Postgres:
  - todo request que **escreve** num branch adquire `pg_advisory_xact_lock_shared(<chave do branch>)` na transação;
  - merge, sync, revert e migrate adquirem o lock **exclusivo** depois da transição de status (SPEC-1737) e antes de ler o changelog;
  - com isso, o job espera as escritas em andamento terminarem, e escritas novas são recusadas pelo status.
- Timeout de espera do lock configurável. Se estourar, o job falha limpo e volta ao status anterior.
- Verificação de consistência no fim do merge: contagem de ObjectChanges do branch × AppliedChanges. Divergência registra erro e impede o MERGED.
- Archive só faz `DROP SCHEMA` se a verificação acima passou (proteção em profundidade).

**FORA:**
- Código HTTP devolvido aos clientes durante o lock → SPEC-20261114-1741.
- Leituras: não precisam do lock.

## Invariantes
- NUNCA um branch chega a MERGED com ObjectChange no schema do branch sem AppliedChange correspondente.
- NUNCA `DROP SCHEMA` de um branch com mudanças não mergeadas, a menos que o usuário peça explicitamente (descartar).

## Critério de aceite
- [x] Teste que **falha antes da correção**: escrita concorrente durante `merge()` (thread segurando um request de escrita aberto) → depois da correção, a escrita entra no merge ou é recusada antes de gravar | verify: `./manage.py test netbox_branching.tests.test_merge_concurrency` — 2026-11-15 21:16, `bd9e7be` (no código antigo o merge lê antes de trocar o status; os testes de ordem não passam)
- [x] Idem para `sync()` | verify: `./manage.py test netbox_branching.tests.test_merge_concurrency`
- [ ] Merge com divergência ObjectChange × AppliedChange não vira MERGED | verify: `./manage.py test netbox_branching.tests.test_merge_concurrency`
- [x] Cenário `branch-merge-race` (SPEC-1736): 0 objetos perdidos em 5/5 execuções (2026-11-15 21:16, `bench/results/20261115-204522-*`; throughput ±5% ainda não medido); throughput de escrita no branch sem merge em andamento dentro de ±5% do baseline | evidence: manual @aliothbl
