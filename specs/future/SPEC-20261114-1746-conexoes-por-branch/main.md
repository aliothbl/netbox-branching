# SPEC-20261114-1746: Conexões ao Postgres limitadas com muitos branches

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:46
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** conexões, max_connections, CONN_MAX_AGE, alias-por-schema, DynamicSchemaDict, search_path, pgbouncer, operação
**Features:** routing
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1736 (medição com `pg_stat_activity`)
**Origem:** DIAGNOSTICO F13 (plausível; medir antes).
**Resumo:** Cada branch usado gera um alias de banco (`schema_<id>`, com `search_path` próprio) e, portanto, uma conexão persistente por thread/worker (`utilities.py:93-142`). Com N branches ativos e W workers, o total cresce como N×W e pode estourar `max_connections` do Postgres.

## Objetivo

Medir o crescimento real e, se confirmado, desacoplar o número de conexões do número de branches.

## Escopo

**DENTRO:**
- Medir `pg_stat_activity` com 1, 10 e 50 branches usados sob carga e 4 workers.
- Se confirmado, avaliar no journal: (a) uma conexão por worker com `SET search_path` por request (cuidado com o estado da conexão), (b) `CONN_MAX_AGE` curto para aliases de branch, (c) fechar aliases ociosos. Escolher pela medição.
- Documentar o dimensionamento recomendado (`max_connections`, pgbouncer em modo session).

**FORA:**
- Mudar o modelo de schema por branch.

## Invariantes
- Isolamento entre branches intacto: uma query nunca roda com o `search_path` de outro branch.

## Critério de aceite
- [ ] Medição antes registrada (conexões × branches × workers) | evidence: manual @aliothbl
- [ ] Se corrigido: conexões não crescem linearmente com o número de branches usados, e o teste de isolamento passa | verify: `./manage.py test netbox_branching.tests.test_connections`
