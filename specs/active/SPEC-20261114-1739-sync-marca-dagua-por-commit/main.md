# SPEC-20261114-1739: Sync não pula mudanças do main commitadas tarde

**Status:** active
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:39
**Ativada:** 2026-11-16 05:36
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** sync, last_sync, watermark, marca-dagua, ObjectChange.time, auto_now_add, transação-longa, ChangeDiff.current, conflito, 2PC
**Features:** sync-merge-revert, change-tracking
**Branch:** `spec/20261114-1739-sync-marca-dagua-por-commit`
**Programa:** —
**Relacionadas:** SPEC-20261114-1736 (cenário `branch-sync-watermark`)
**Origem:** DIAGNOSTICO F3, F4 e F15.
**Resumo:** A marca d'água do sync (`time__gt=last_sync`) assume que o `ObjectChange.time` reflete a ordem de commit. Não reflete: o `time` é o momento do `save()`. Uma transação do main que salvou antes da leitura do sync e commitou depois nunca é sincronizada, e o branch diverge para sempre.

## Objetivo

O upstream já corrigiu metade do problema: `sync_started` é gravado **antes** da leitura (`models/branches.py:943-946`, ver o comentário). Ainda sobra esta janela:
1. Um request no main (por exemplo um bulk apply do Diode, numa transação longa) grava um ObjectChange com `time = T0`.
2. O sync começa em `T1 > T0`. O SELECT ainda não vê a linha, porque ela não foi commitada.
3. A transação commita em `T2 > T1`. O sync grava `last_sync = T1`.
4. Todo sync seguinte filtra `time > T1` e pula essa mudança para sempre.

Agravantes:
- **F4:** `ChangeDiff.current` só é atualizado para branches READY (`signal_receivers.py:134-135`), e o merge não exige sync prévio. Um merge posterior pode sobrescrever o main sem acusar conflito.
- **F15:** branch e main commitam em duas conexões sem 2PC (`:969-973`). Uma falha entre os dois commits deixa o branch commitado e o `last_sync`/ChangeDiff do main revertidos.

## Escopo

**DENTRO:**
- Marca d'água que respeita a visibilidade de commit. Duas alternativas a decidir no journal com medição:
  - (a) `last_sync` recuado por uma margem de segurança + deduplicação por ObjectChange já aplicado (o equivalente de `AppliedChange` para sync);
  - (b) marca d'água por `xmin`/snapshot do Postgres (`pg_current_snapshot()`), relendo o que estava em andamento no snapshot anterior.
- Sync idempotente: reaplicar uma mudança já sincronizada não muda o estado.
- `ChangeDiff.current` também atualizado em SYNCING; o merge recusa (ou alerta) quando há mudanças do main ainda não sincronizadas no mesmo objeto.
- Ordem de commit à prova de falha entre conexões: registro de progresso que permite retomar o sync.

**FORA:**
- Lock de escritas no branch → SPEC-1738.

## Invariantes
- NUNCA uma mudança commitada no main deixa de chegar ao branch em algum sync posterior.
- Aplicar o mesmo sync duas vezes é inócuo.

## Critério de aceite
- [x] Teste que **falha antes**: transação no main aberta antes do sync e commitada depois → o segundo sync traz a mudança | verify: `./manage.py test netbox_branching.tests.test_sync_watermark`
- [x] Teste: sync repetido não duplica nem altera estado (inclusive depois de perder o commit da conexão default) | verify: `./manage.py test netbox_branching.tests.test_sync_replay` (2026-11-16 15:40)
- [x] Teste: mudança do main no mesmo objeto, inclusive durante sync/migração, acusa conflito | verify: `./manage.py test netbox_branching.tests.test_sync_replay` (2026-11-16 15:40)
- [x] Cenário `branch-sync-watermark` (SPEC-1736): main × branch idênticos depois do 2º sync em 5/5 | evidence: manual @aliothbl — 2026-11-16 08:18: 5/5 (`bench/results/20261116-075335-*`), aguarda conferência
