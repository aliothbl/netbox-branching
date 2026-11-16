# Journal — SPEC-20261114-1737-cas-transicoes-status

## SNAPSHOT
- **Fase:** implementada e validada (F1 8/8; suíte sem falhas novas). Pendentes: provision/archive com CAS; 409 na API (decisão do owner).
- **Antes (código atual, com F2 corrigido; `aliothbl/diode:bench/results/20261115-213541-*` e `...-215426-*`):** o F1 **piorou** com o lock da SPEC-1738, porque o segundo merge agora espera o primeiro e roda depois:
  - `create` 3/3: o 2º merge falha em duplicata e o rollback dele escreve READY sobre o MERGED do 1º. **O branch termina READY com os dados já no main** (antes da 1738, era um READY transitório de ~3 s).
  - `update` 5/5: os dois merges "terminam" e há 2 eventos MERGED.

## Decisões
- **DEC-1 — helper único `_transition_status(expected, new, **fields)`** (`UPDATE ... WHERE pk AND status IN expected`). Aplicado na entrada de sync (READY→SYNCING), merge (READY→MERGING), revert (MERGED→REVERTING) e migrate (READY|PENDING_MIGRATIONS→MIGRATING), em todos os rollbacks (só voltam se o status ainda for o transitório deste job) e nas transições finais (SYNCING→READY com `last_sync`, MERGING→MERGED com `merged_time`/`merged_by`, REVERTING→READY, MIGRATING→READY/FAILED).
- **DEC-2 — transição final sem `save()` do status.** O status e os campos de ciclo de vida vão no UPDATE condicional; depois `save(update_fields=[...])` só com os outros campos, para os receivers de `post_save` continuarem disparando sem reescrever o status.
- **DEC-3 — F14:** `post_save.disconnect(record_applied_change)` em `finally` no merge e no revert.
- **Pendente do escopo:** provision e archive ainda usam UPDATE incondicional, e as ações da API continuam respondendo 400 (não 409) quando o branch não está no status esperado. O duplo clique já é coberto pelo CAS no modelo: o 2º job aborta sem efeito. Trocar 400 por 409 muda o contrato público e fica para decisão do owner.

## LOG
- 2026-11-16 04:59 — **Validado: F1 corrigido 8/8.** `branch-double-merge` com dois merges liberados juntos (`aliothbl/diode:bench/results/20261116-042348-*` update ×5, `20261116-044607-*` create ×3; branching `ee957fe`): em todas, **exatamente um merge aplica e termina MERGED**, e o outro aborta em ≤ 11 ms com "not ready to merge (its status changed)". 1 evento MERGED, ObjectChanges no main = os do branch (80 ou 209, aplicados uma vez), status final MERGED (antes: create 3/3 terminava READY; update 5/5 com 2 eventos MERGED). Suíte completa (`...-full-1737.log`): 599 testes, as mesmas 33 falhas do `main` (SPEC-1916), nenhuma nova.
- 2026-11-15 22:17 — SPEC ativada (branch criado às 21:42 a partir de `main` `0b23777`, num worktree para não mexer no checkout que o bench montava durante a medição "antes"). Testes novos em `tests/test_status_transitions.py` (6): CAS básico, 2º merge e 2º sync abortam sem tocar o branch, rollback de merge falho não reabre um branch MERGED por outro job, transição final condicional, exceção em `post_merge` não deixa o receiver conectado. Com `test_merge_concurrency`: 13/13 (`aliothbl/diode:bench/evidence/logs/20261115-nbb-test-1737.log`).
