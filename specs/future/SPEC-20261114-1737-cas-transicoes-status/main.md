# SPEC-20261114-1737: Transições de status do Branch com compare-and-set

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:37
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** status, compare-and-set, CAS, merge-duplo, sync-duplo, rqworker, transição, signal-handler, finally
**Features:** sync-merge-revert
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1738 (bloqueio de escritas; usa o mesmo ponto de transição); SPEC-20261114-1736 (cenário `branch-double-merge`)
**Origem:** DIAGNOSTICO F1 e F14.
**Resumo:** Toda transição de status (READY→SYNCING/MERGING/MIGRATING/REVERTING e as de volta) passa a ser um compare-and-set atômico. Assim, dois jobs nunca operam o mesmo branch ao mesmo tempo, e uma falha nunca devolve READY a um branch que outro job já levou a MERGED.

## Objetivo

`sync()`, `merge()`, `revert()` e `migrate()` checam `self.ready` numa instância em memória e depois fazem `Branch.objects.filter(pk=self.pk).update(status=X)` sem condição sobre o status atual (`models/branches.py:957,1069,1156,1232`). O `except` do merge faz `update(status=READY)` incondicional (`:1180`). Com dois rqworkers e dois pedidos de merge (duplo clique, retry de cliente):
- os dois jobs passam pela checagem e reaplicam o changelog. Um changelog só de UPDATEs é aplicado duas vezes sem erro;
- se o segundo falhar (por exemplo, IntegrityError nos CREATEs), o `except` devolve READY a um branch que o primeiro já levou a MERGED. O branch volta a aceitar escrita e merge.

Além disso, o handler `post_save` de `record_applied_change` só é desconectado no caminho feliz ou no `except` (`:1162-1199`). Uma exceção depois do commit, por exemplo em `post_merge`, deixa o handler conectado no processo (F14).

## Escopo

**DENTRO:**
- Helper único de transição: `UPDATE ... SET status=<novo> WHERE pk=<pk> AND status=<esperado>`. Se nenhuma linha for afetada, o job aborta sem efeito colateral e registra o motivo.
- Aplicar o helper em sync, merge, revert, migrate, provision e archive, inclusive nos caminhos de rollback (`READY` só volta se o status ainda for o transitório que este job colocou).
- A transição para o status transitório acontece **antes** de ler o changelog. Esse é o ponto que a SPEC-1738 usa para o lock.
- `post_save.disconnect` em `finally`.
- Ação da API (`api/views.py`): devolver 409 quando o branch não está no status esperado, em vez de enfileirar um job que vai abortar.

**FORA:**
- Bloquear escritas de requests no branch durante merge/sync → SPEC-20261114-1738.

## Invariantes
- NUNCA dois jobs de sync/merge/revert/migrate em execução sobre o mesmo branch.
- NUNCA um rollback sobrescreve um status terminal (MERGED, ARCHIVED) colocado por outro job.

## Critério de aceite
- [ ] Teste com duas execuções concorrentes de `merge()` no mesmo branch: exatamente uma aplica, a outra aborta, e o status final é MERGED | verify: `./manage.py test netbox_branching.tests.test_status_transitions`
- [ ] Teste: falha no 2º merge não devolve READY a um branch MERGED | verify: `./manage.py test netbox_branching.tests.test_status_transitions`
- [ ] Teste: exceção em `post_merge` não deixa `record_applied_change` conectado | verify: `./manage.py test netbox_branching.tests.test_status_transitions`
- [ ] Cenário `branch-double-merge` (SPEC-1736) sem duplicação em 5/5 execuções | evidence: manual @aliothbl
