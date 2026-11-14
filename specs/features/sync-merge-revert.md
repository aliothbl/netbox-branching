# Feature: sync-merge-revert

**Keywords:** sync, merge, revert, archive, status, MERGING, SYNCING, compare-and-set, AppliedChange, merge-strategy, iterative, squash, rq
**Arquivos principais:**
  - netbox_branching/models/branches.py (sync, merge, revert, migrate, archive)
  - netbox_branching/merge_strategies/
  - netbox_branching/jobs.py
  - netbox_branching/api/views.py (actions)
**Resumo:** Jobs RQ que levam mudanças do main ao branch (sync), do branch ao main (merge) e desfazem merges (revert).

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1737 | CAS nas transições de status | merge/sync duplos
- SPEC-20261114-1738 | Bloqueio de escritas em merge/sync | perda silenciosa (crítico)
- SPEC-20261114-1739 | Marca d'água do sync | mudanças puladas
- SPEC-20261114-1740 | Revert com conflitos | cascata apaga dados do main
- SPEC-20261114-1743 | Merge escalável | memória e N+1

## Estado atual
`sync()`/`merge()`/`revert()` checam `self.ready` em memória e fazem `update(status=…)` **sem condição** (`models/branches.py:957,1069,1156,1232`); o `except` do merge volta a READY incondicionalmente (`:1180`). O merge lê e materializa o changelog **antes** de marcar MERGING (`:1147-1156`; o comentário diz isso). O sync grava `sync_started` antes da leitura (`:943-946`), o que fecha só parte da janela. Cada um roda numa transação. O revert faz `undo()` em ordem inversa sem checar conflito (`models/changes.py:186-196`; `api/views.py:118-133`). O archive faz `DROP SCHEMA`.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261114-1738 | Escrita em andamento no branch durante o merge fica fora dele e some no archive (2026-11-14 17:38)
- SPEC-20261114-1737 | Handler `post_save` de AppliedChange desconectado sem `finally` (2026-11-14 17:37)
