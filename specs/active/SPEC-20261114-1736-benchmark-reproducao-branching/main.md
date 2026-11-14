# SPEC-20261114-1736: Reprodução e benchmark do netbox-branching (harness do Diode)

**Status:** active
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:36
**Ativada:** 2026-11-14 18:17
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** benchmark, reprodução, py-spy, pg_stat_statements, merge-concorrente, router, diode-bench, harness
**Features:** ci-tests, routing, sync-merge-revert
**Branch:** `spec/20261114-1736-benchmark-reproducao` (netbox-branching, docs) + `perf/bench-vs-upstream` (aliothbl/diode, código do harness)
**Programa:** —
**Relacionadas:** `aliothbl/diode:bench/` (harness reutilizado); `aliothbl/diode:specs/active/SPEC-20261114-0807-benchmark-performance-vs-upstream` (origem do método)
**Origem:** `specs/DIAGNOSTICO-2026-11-14.md`, seção "Como medir".
**Resumo:** Estender o harness de benchmark do Diode com cenários que reproduzem F2 (perda no merge), F1 (merge duplo), F3 (sync pulando mudança), F6 (400 durante sync) e medem o custo por request de F7, F8 e F9. É o "antes" de todas as outras SPECs.

## Objetivo

O diagnóstico saiu só de leitura de código. Pela regra 8 do README, nenhuma correção de concorrência ou performance é concluída sem reprodução antes/depois. O objetivo é um conjunto de cenários reprodutíveis que (a) **falhem** no código atual quando o achado é real e (b) produzam números comparáveis para os achados de performance.

## Escopo

**DENTRO:**
- Cenários no harness `aliothbl/diode:bench/` (mesmo stack: NetBox 4.7.0 + diode-netbox-plugin + netbox-branching montado a partir do fork):
  - `branch-merge-race` (F2): ingestão contínua do Diode num branch (`X-NetBox-Branch`) + `POST .../merge/` no meio da carga. Medida: objetos/ObjectChanges do branch que não chegaram ao main.
  - `branch-double-merge` (F1): 2 rqworkers + 2 POSTs de merge (e de sync) simultâneos. Medida: status final, jobs executados, ObjectChanges duplicados no main.
  - `branch-sync-watermark` (F3): transação longa no main (bulk apply do Diode) concorrente com um sync; segundo sync; diff main × branch.
  - `branch-sync-ingest` (F6): Diode ingerindo no branch padrão enquanto ocorre um sync. Medida: ingestion logs FAILED com HTTP 400.
  - `router-overhead` (F7/F8/F9): mesmo bulk apply no main com `netbox_branching` em `PLUGINS` e sem ele. Medidas: throughput, py-spy em `database.py`, `pg_stat_statements` de `netbox_branching_changediff`.
- Versão do plugin como parâmetro (`BRANCHING_SRC` = checkout montado), para comparar `v1.2.0`, `v1.2.3` e o fork.

**FORA:**
- Correções (cada achado tem a sua SPEC).
- Escala de merge com 50k mudanças (fica na SPEC-20261114-1743).

## Invariantes
- SEMPRE o mesmo stack do benchmark do Diode, para os números serem comparáveis com o relatório de 2026-11-14.
- NUNCA rodar cenários de corrida "uma vez só": cada um roda ≥5 vezes e reporta a taxa de reprodução.

## Critério de aceite
- [ ] Cada cenário roda por um comando e grava JSON em `bench/results/` | verify: `bench/run.sh --scenario branch-merge-race --version candidate`
- [ ] F2, F1, F3 e F6 reproduzidos (ou refutados, com evidência) no código atual, com taxa de reprodução | evidence: manual @aliothbl
- [ ] Custo de F7/F8/F9 medido (ent/s com × sem plugin, % de CPU em `database.py`) | evidence: manual @aliothbl
- [ ] Resultados registrados no DIAGNOSTICO (achado → verificado/refutado) | evidence: manual @aliothbl
