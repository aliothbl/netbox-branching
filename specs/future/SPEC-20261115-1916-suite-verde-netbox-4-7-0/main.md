# SPEC-20261115-1916: Suíte verde (e comportamento correto) no NetBox mínimo declarado, 4.7.0

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-15 19:16
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** testes, CI, compatibilidade, min_version, 4.7.0, cabo, CablePath, terminations, merge, revert, sync, query count
**Features:** merge, sync, revert, routing
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1741 (a validação dela encontrou isto); SPEC-20261114-1736 (harness)
**Origem:** suíte completa rodada em 2026-11-15 com o NetBox **4.7.0** (imagem `diode-bench/netbox:v4.7.0`, runner `aliothbl/diode:bench/tools/nbb-test.sh`). O `main` intacto (`d091fd3`) tem **33 falhas** (29 F + 4 E de 581 testes), as mesmas no branch da SPEC-1741. Logs: `aliothbl/diode:bench/evidence/logs/20261115-nbb-test-full-main-baseline.log` e `...-full-1741.log`.
**Resumo:** O plugin declara suporte a partir do NetBox 4.7.0 (`min_version = '4.7.0'`, `COMPATIBILITY.md`), mas o CI só testa contra o NetBox `main` (`.github/workflows/test.yml`, `netbox-ref: main`). No 4.7.0, 31 das 33 falhas são de **cabos em merge, revert e sync**, o que sugere que quem roda o 4.7.0 pode ter cable paths quebrados depois de mergear ou reverter um branch. É preciso descobrir, para cada grupo, se a diferença é só no teste ou se o comportamento está errado no 4.7.0, e então corrigir o código ou subir a versão mínima declarada.

## Falhas (NetBox 4.7.0, `main` intacto)

| Qtde | Sintoma | Testes |
|---|---|---|
| 15 | `ethN has no cable path` | iterative: revert cable move_a_end / move_both_ends / reorder_terminations / set_profile; squash: merge cable create / create_with_edited_endpoint / move_a_end / move_both_ends / reorder_terminations / set_profile; squash: revert cable delete / move_a_end / move_both_ends / reorder_terminations / set_profile |
| 5 | `Lists differ: [(N, N, None, None)] != []` | iterative + squash: merge cable clear_a_end / clear_b_end; sync cable_clear_end |
| 4 | `Exception: Only merged branches can be reverted.` (ERROR) | iterative + squash: revert cable clear_a_end / clear_b_end (o merge anterior não chegou a MERGED) |
| 4 | `AssertionError: N != N` | iterative: merge cable move_a_end / move_b_end / reorder_terminations; sync cable_reorder_terminations |
| 3 | `Lists differ: [['N:N'], ['N:N'], []] != [...]` | iterative: revert cable move_b_end; squash: merge/revert cable move_b_end |
| 1 | `None != <Branch: Branch N>` | `test_request.test_background_api_request_activates_branch_from_query_param` |
| 1 | query count de `branch:list_objects_with_permission` mudou | `test_views.test_list_objects_with_permission` (número fixado em `tests/query_counts.json`) |

## Escopo

**DENTRO:**
- Para cada grupo, diagnóstico: diferença do NetBox 4.7.0 × `main` (changelog do NetBox 4.7.x, especialmente cable paths/terminations) e se o **comportamento** do plugin está errado no 4.7.0 (cable path quebrado após merge/revert/sync) ou se só o teste assume o `main`.
- Correção conforme o caso: código compatível com 4.7.0, **ou** subir `min_version` (e `COMPATIBILITY.md`) para a primeira 4.7.x em que tudo funciona.
- CI: incluir na matriz o `min_version` declarado (além do `main`), para a promessa de compatibilidade ser testada.
- Os 2 casos fora de cabos: `test_background_api_request...` e o query count (o contador pode depender da versão do NetBox: fixar por versão ou relaxar).

**FORA:**
- Mudanças de comportamento de merge/revert além do necessário para os cabos.

## Invariantes
- Toda versão dentro de `min_version`–`max_version` tem a suíte verde.
- Merge, revert e sync de cabos deixam os cable paths corretos em toda versão suportada.

## Critério de aceite
- [ ] Diagnóstico por grupo registrado no journal (teste × comportamento), com a versão do NetBox em que cada um passa | evidence: manual @aliothbl
- [ ] Suíte completa verde no NetBox 4.7.0 (ou `min_version` elevado com justificativa) | verify: `bench/tools/nbb-test.sh netbox_branching.tests` (repo aliothbl/diode)
- [ ] CI testa o `min_version` declarado | verify: `.github/workflows/test.yml` com `netbox-ref` do `min_version`
