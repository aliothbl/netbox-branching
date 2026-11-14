# SPEC-20261114-1743: Merge e revert escaláveis (memória e N+1)

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:43
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** merge, revert, N+1, select_related, iterator, memória, changelog, changed_object_type, user, merge-strategy
**Features:** sync-merge-revert
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1736 (harness); SPEC-20261114-1738 (merge segura o lock exclusivo enquanto roda, então a duração importa)
**Origem:** DIAGNOSTICO F10.
**Resumo:** Merge e revert carregam o changelog inteiro na memória (`len(changes)`) e fazem consultas N+1 (`changed_object_type`, `user`) por mudança. Isso limita o tamanho de branch viável e, com a SPEC-1738, alonga o tempo de lock.

## Objetivo

`merge()` avalia `len(changes)` sobre o queryset completo (`models/branches.py:1148`), e a strategy iterativa percorre as mudanças acessando FKs sem `select_related` (`merge_strategies/iterative.py:29-38`; `models/changes.py:111`). A memória é proporcional ao changelog, e são 2 queries extras por mudança.

## Escopo

**DENTRO:**
- `select_related('changed_object_type', 'user')` e iteração em blocos (`iterator(chunk_size=…)`) no merge, sync e revert.
- `exists()`/`count()` no lugar de `len()` onde só se precisa saber se há mudanças.
- Medir merge com 1k, 10k e 50k mudanças: tempo, RSS do worker e queries (`pg_stat_statements`).

**FORA:**
- Paralelizar o merge (muda a semântica de ordem).

## Invariantes
- Mesma ordem de aplicação e mesmo resultado final do merge (teste de equivalência sobre um branch de referência).

## Critério de aceite
- [ ] `assertNumQueries` no merge de N mudanças: queries não crescem com 2·N | verify: `./manage.py test netbox_branching.tests.test_merge_scaling`
- [ ] Medição 1k/10k/50k antes e depois registrada no journal (tempo, RSS, queries) | evidence: manual @aliothbl
