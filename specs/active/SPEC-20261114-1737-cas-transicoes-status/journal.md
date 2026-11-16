# Journal — SPEC-20261114-1737-cas-transicoes-status

## SNAPSHOT
- **Fase:** implementada, testes unitários verdes; validando no bench (`branch-double-merge` ×8) e com a suíte completa.
- **Antes (código atual, com F2 corrigido; `aliothbl/diode:bench/results/20261115-213541-*` e `...-215426-*`):** o F1 **piorou** com o lock da SPEC-1738, porque o segundo merge agora espera o primeiro e roda depois:
  - `create` 3/3: o 2º merge falha em duplicata e o rollback dele escreve READY sobre o MERGED do 1º. **O branch termina READY com os dados já no main** (antes da 1738, era um READY transitório de ~3 s).
  - `update` 5/5: os dois merges "terminam" e há 2 eventos MERGED.

## Decisões
- **DEC-1 — helper único `_transition_status(expected, new, **fields)`** (`UPDATE ... WHERE pk AND status IN expected`). Aplicado na entrada de sync (READY→SYNCING), merge (READY→MERGING), revert (MERGED→REVERTING) e migrate (READY|PENDING_MIGRATIONS→MIGRATING), em todos os rollbacks (só voltam se o status ainda for o transitório deste job) e nas transições finais (SYNCING→READY com `last_sync`, MERGING→MERGED com `merged_time`/`merged_by`, REVERTING→READY, MIGRATING→READY/FAILED).
- **DEC-2 — transição final sem `save()` do status.** O status e os campos de ciclo de vida vão no UPDATE condicional; depois `save(update_fields=[...])` só com os outros campos, para os receivers de `post_save` continuarem disparando sem reescrever o status.
- **DEC-3 — F14:** `post_save.disconnect(record_applied_change)` em `finally` no merge e no revert.
- **Pendente do escopo:** provision e archive ainda usam UPDATE incondicional, e as ações da API continuam respondendo 400 (não 409) quando o branch não está no status esperado. O duplo clique já é coberto pelo CAS no modelo: o 2º job aborta sem efeito. Trocar 400 por 409 muda o contrato público e fica para decisão do owner.

## LOG
- 2026-11-15 22:17 — SPEC ativada (branch criado às 21:42 a partir de `main` `0b23777`, num worktree para não mexer no checkout que o bench montava durante a medição "antes"). Testes novos em `tests/test_status_transitions.py` (6): CAS básico, 2º merge e 2º sync abortam sem tocar o branch, rollback de merge falho não reabre um branch MERGED por outro job, transição final condicional, exceção em `post_merge` não deixa o receiver conectado. Com `test_merge_concurrency`: 13/13 (`aliothbl/diode:bench/evidence/logs/20261115-nbb-test-1737.log`).
