# Journal — SPEC-20261114-1738-bloqueio-escritas-merge-sync

## SNAPSHOT
- **Fase:** implementação feita e testes unitários verdes; validando no bench (`branch-merge-race` ×5) e com a suíte completa.
- **Antes (medido com o código atual, F6 já corrigido):** `branch-merge-race` ×5 (`aliothbl/diode:bench/results/20261115-193520-*`): cada merge perdeu 45–112 objetos (devices 4–11, interfaces 19–50, IPs 22–51), o Diode registrou tudo como APPLIED (0 FAILED). Os perdidos são as escritas em andamento no momento em que o merge leu o changelog: nenhum request chegou depois do MERGING (0 respostas 503).

## Decisões
- **DEC-1 — lock de sessão na conexão default, não `pg_advisory_xact_lock`.** Um request de escrita no branch atravessa várias transações em mais de uma conexão (schema do branch + default), então o lock é de sessão, tomado pelo middleware antes da view e solto no fim do request (`finally`). O lock de transação da SPEC original não cobriria o request inteiro.
- **DEC-2 — o request não espera o lock: `pg_try_advisory_lock_shared`.** Se uma operação já segura o lock exclusivo (está lendo o changelog), a escrita recebe 503 retryable na hora (SPEC-1741), em vez de bloquear um worker por toda a duração do merge.
- **DEC-3 — status relido sob o lock.** `get_active_branch()` leu o status antes do lock; um merge pode ter trocado o status e estar esperando justamente este lock. O middleware relê o status depois de pegar o lock e recusa se não for READY.
- **DEC-4 — ordem no merge e no sync: status → lock exclusivo → leitura do changelog.** Antes: leitura → status. O lock exclusivo é tomado num savepoint com `lock_timeout` local (`write_drain_timeout`, padrão 300 s); estourar devolve o branch a READY e falha a operação (`BranchWriteLockTimeout`).
- **DEC-5 — só métodos não seguros (POST/PUT/PATCH/DELETE) tomam o lock.** Leituras não precisam (escopo da SPEC). Escritas fora de request HTTP (scripts e jobs com `activate_branch`) não são cobertas: limitação registrada.
- **Fora desta entrega (fica no escopo da SPEC):** verificação ObjectChange × AppliedChange no fim do merge e a proteção do `DROP SCHEMA` no archive.

## LOG
- 2026-11-15 20:26 — SPEC ativada (branch criado às 19:39 a partir de `main` `f45bfcf`). Implementação: `acquire_branch_write_lock` / `release_branch_write_lock` / `branch_exclusive_lock` em `utilities.py`; middleware toma o lock compartilhado em escritas e relê o status; `merge()` e `sync()` reordenados (`_merge_locked`, `_sync_locked`); setting `write_drain_timeout`. Testes novos em `tests/test_merge_concurrency.py` (7): lock preso durante a escrita, GET sem lock, 503 com o lock exclusivo tomado, status relido sob o lock, timeout do merge devolve READY, merge e sync leem o changelog já em MERGING/SYNCING e com o lock exclusivo. `test_merge_concurrency` + `test_request`: 28/29, e a falha é a que já existe no `main` (SPEC-1916). Log: `aliothbl/diode:bench/evidence/logs/20261115-nbb-test-1738.log`.
