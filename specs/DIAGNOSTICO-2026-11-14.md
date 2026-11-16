# Diagnóstico do netbox-branching (main @ bb2f951, ≈ v1.2.3)

O pior risco é a perda silenciosa de dados quando o Diode escreve num branch durante um merge (F2). Isso fica permanente quando o branch é arquivado, que dá `DROP SCHEMA`. Logo atrás vêm dois jobs de merge/sync que podem rodar ao mesmo tempo no mesmo branch (F1) e mudanças do main que um sync deixa de fora (F3). Tudo aqui saiu da leitura do código: não rodei testes nem nada que pesasse na máquina, e não alterei nenhum arquivo.

## Arquitetura (resumo)
- **Provisionamento:** cada branch vira um schema PostgreSQL (`branch_<schema_id>`). As tabelas são copiadas em paralelo a partir de um snapshot exportado (`provisioning.py`). O `id` das tabelas copiadas continua usando a **sequence do main**, então os IDs não colidem entre schemas (`provisioning.py:359-368`).
- **Roteamento:** o request processor `ActiveBranchContextManager` (`utilities.py:693`) põe o branch na contextvar `active_branch`. O `BranchAwareRouter` (`database.py:24-51`) manda as queries para o alias `schema_<schema>`. O `DynamicSchemaDict` monta esse alias com `search_path=branch,public`. O `BranchMiddleware` resolve o branch de novo e só cuida do cookie e dos erros 400.
- **Registro de mudanças:** cada ObjectChange gera ou atualiza um `ChangeDiff` (`signal_receivers.py:108`), que é a base da detecção de conflito.
- **Sync, merge e revert:** são jobs RQ que reaplicam o changelog, numa transação só.

## Achados

| ID | Sev. | Área | Resumo | Evidência | Status |
|---|---|---|---|---|---|
| F1 | alta | concorrência | Mudanças de status sem compare-and-set: dois jobs podem rodar ao mesmo tempo no mesmo branch | `models/branches.py:933,957,1139,1156,1180`; `api/views.py:70-80,98-108` | **reproduzido 9/9 → corrigido 8/8** (2026-11-16). Com o lock do F2 (SPEC-1738), o F1 piorou antes da correção: create 3/3 terminava READY de vez com os dados já no main; update 5/5 mergeava 2×. Depois (SPEC-1737, `ee957fe`): exatamente um merge aplica, o outro aborta sem efeito, status final MERGED (`aliothbl/diode:bench/results/20261116-042348-*`, `-044607-*`) |
| F2 | **crítica** | concorrência/dados | Escritas no branch que estão em andamento quando o merge começa nunca são mergeadas, e o branch fica MERGED | `models/branches.py:1148,1156`; `utilities.py:609-613` | **reproduzido 6/6 → corrigido 5/5** (2026-11-15). Antes: 41–76 (14/11) e 45–112 (15/11, com F6 corrigido) objetos perdidos por merge. Depois (SPEC-1738, `bd9e7be`): **0 perdidos** em 5/5 (`aliothbl/diode:bench/results/20261115-204522-*`) |
| F3 | alta | sync | A marca d'água por `time` perde mudanças do main ainda não commitadas | `models/branches.py:946,949,397,1029`; NetBox `core/models/change_logging.py` (`time` com `auto_now_add`) | **reproduzido 5/5** (SPEC-1736, 2026-11-15: mudança salva antes do sync e commitada depois fica no main e nunca chega ao branch; o sync seguinte não a enxerga) |
| F4 | média | conflitos | O `ChangeDiff.current` só é atualizado para branches READY, e o merge não exige sync | `signal_receivers.py:134-135`; `api/views.py:36-55` | verificado |
| F5 | alta | revert | O revert não checa conflito nem dependências; desfazer um CREATE faz delete em cascata no main | `models/changes.py:186-191,193-196`; `api/views.py:118-133` | verificado (sem checagem); cascata plausível |
| F6 | alta | Diode | Branch em sync, merge ou com migração pendente devolve **HTTP 400** a todo request; o reconciler marca o lote como falho | `middleware.py:55-56`; `diode-server/reconciler/ops.go:663-665` | **reproduzido 5/5 → corrigido 5/5** (2026-11-15). Antes: sync de ~38 s → 190–265 de 540 entidades FAILED, 21–29 devices nunca chegam ao branch. Depois (SPEC-1741 `44f5b50`+`e3bcd51`, diode SPEC-1748, plugin `163d202`+`938afa0`): **0 FAILED, nada faltando, 0 timeouts** em 5/5 (`aliothbl/diode:bench/results/20261115-162825-*`) |
| F7 | média | performance | O router chama `supports_branching()` em **toda** query ORM, antes de ver se há branch ativo | `database.py:31,35`; `utilities.py:244-293` (`# TODO: Make this more efficient`) | **medido** (SPEC-1736, 2026-11-15): `supports_branching` 2,38 µs/chamada (0,08 µs com cache por modelo, 30×); `db_for_read`/`db_for_write` 3,0–3,2 µs sem branch ativo; **1,36% das amostras de py-spy dentro do request do Diode** (1,04% em `supports_branching`). Ganho do cache estimado em ~1% do tempo de request: real, mas pequeno |
| F8 | baixa-média | performance | Cada UPDATE/DELETE no main faz um SELECT extra em ChangeDiff, mesmo sem nenhum branch | `signal_receivers.py:124-136` | verificado |
| F9 | baixa | performance | Branch buscado 2× por request com header (processor e middleware), mais ~5 `reverse()` por request | `utilities.py:576-583,609-610,693-721`; `middleware.py:47,52,62`; `constants.py:46` | verificado |
| F10 | média | performance | Merge/revert carregam todo o changelog na memória e fazem N+1 (`changed_object_type`, `user`) por mudança | `models/branches.py:1148`; `merge_strategies/iterative.py:29-38`; `models/changes.py:111` | N+1 verificado; memória plausível |
| F11 | média | segurança | Nenhuma autorização para ativar um branch: qualquer usuário autenticado lê e escreve em qualquer branch pelo `schema_id`; `owner` não é aplicado; a resposta 400 antes da autenticação revela se o branch existe | `utilities.py:609-613,619,644`; `models/branches.py:191` | verificado |
| F12 | média | migração | Tabela nova criada por `migrate` no branch ganha sequence própria e pode colidir de ID com o main | `models/branches.py:1043-1113` (sem ajuste de sequence) vs `provisioning.py:359` | plausível |
| F13 | média | operação | Cada branch abre uma conexão persistente por thread ou worker: N branches × workers pode estourar `max_connections` | `utilities.py:93-142` | plausível |
| F14 | baixa | robustez | O handler `post_save` do merge/revert fica conectado se algo falha depois do commit (falta `finally`) | `models/branches.py:1163,1186-1200,1239,1259-1276` | verificado; o fork do RQ limita o efeito |
| F15 | baixa | sync | Commit em duas conexões sem 2PC: o branch pode commitar e o ChangeDiff/`last_sync` no main fazer rollback | `models/branches.py:969-973` | plausível |

Schema e SQL estão bem cuidados: usam `quote_ident`, o `schema_id` não é editável e o token de snapshot é validado por regex. Não achei injeção.

## Detalhe dos achados crítico e altos

**F2 (crítica).** `merge()` lê e materializa o changelog do branch na linha 1148 e só depois marca MERGING (1156). O middleware só olha `ready` no começo de cada request.
- Cenário: o Diode, com branch padrão configurado, está no meio de um `bulk-plan-apply` de 30 s no branch quando alguém dispara o merge.
- Tudo o que esse request commita depois da linha 1148 fica no schema do branch, mas não entra no main.
- O branch vai para MERGED sem nenhum aviso. Quando é arquivado (inclusive pelo auto-archive), o `DROP SCHEMA` apaga esses dados para sempre.
- O sync tem a mesma janela entre a 949 e a 957, com escritas concorrentes no mesmo schema.

**F1.** `merge`/`sync` checam `self.ready` numa instância em memória e depois fazem `update(status=…)` sem condição. Só o `recover` usa CAS (`:656`).
- Cenário: dois POST `/merge/` (duplo clique ou retry do cliente) e dois rqworkers. Os dois jobs veem READY e os dois reaplicam o changelog.
- Se o segundo falhar por IntegrityError nos CREATEs, o `except` faz `update(status=READY)` (`:1180`) depois que o primeiro já gravou MERGED. O branch, já mergeado, volta a aceitar escrita e um novo merge.
- Se o branch só tem UPDATEs, as duas execuções passam e a mudança é aplicada duas vezes.

**F3.** `ObjectChange.time` é preenchido pelo Python (`auto_now_add`) no momento do `save()`, não no commit.
- Cenário: no main, um request atômico longo (por exemplo um bulk apply do Diode) grava um ObjectChange às T0 e commita às T2. O sync começa em T1 (T0 < T1 < T2) e grava `last_sync = T1`.
- O SELECT do sync não enxerga a linha (ainda não commitada). Todo sync seguinte filtra `time > T1` e pula essa mudança.
- O branch diverge do main para sempre. Como `current` também não é atualizado durante SYNCING (F4), um merge posterior pode sobrescrever o main sem acusar conflito.

**F5.** O revert faz `undo()` em ordem inversa sem comparar com o estado atual do main, e a action da API não chama `_check_conflicts`.
- Cenário: o branch cria um Device e é mergeado. Depois, no main, alguém adiciona interfaces e IPs nesse device.
- O revert faz `instance.delete()` no Device e o CASCADE do NetBox apaga dados criados no main.
- Um UPDATE desfeito também sobrescreve campos que o main alterou depois do merge.

**F6.** Status como syncing, merging, pending-migrations, merged ou archived viram `400 "Selected branch is not ready."`. O Go trata `>=400` como falha e grava um placeholder de falha para cada item do lote (`ops.go:663-665`). Dois cenários:
- Um sync de minutos no branch padrão do Diode transforma toda a ingestão desse intervalo em falha.
- Depois que o branch padrão é mergeado ou arquivado, o Setting continua apontando para ele e a falha fica **permanente**, porque o form só filtra branches `ready` na hora de salvar.

## Sobre o py-spy
`BranchMiddleware.__call__` aparece na stack porque envolve a view; o tempo próprio dele é pequeno (F9). Sem branch, o custo real do plugin está em dois lugares:
- **F7:** a cada query há f-strings, `apps.get_model`, `issubclass`, montagem de lista e `get_plugin_config`. Isso roda antes de checar a contextvar, ou seja, mesmo sem branch ativo.
- **F8:** um SELECT extra por ObjectChange de update ou delete.

## Versões (v1.2.0 → v1.2.3)
O que pesa para um ambiente fixado em 1.2.0:
- **#672:** em 1.2.0, quando o branch não está pronto, `get_active_branch` devolve um `HttpResponseBadRequest`. O processor ativa esse objeto como se fosse o branch e o middleware segue o fluxo. O router então quebra em `.schema_name`, e o request dá **500** em vez de 400.
- **#675:** com NetBox 4.7, scripts e webhooks disparados pela API quebram no worker em `request.headers`. Isso afeta event rules e webhooks das escritas do Diode.
- **#684:** CREATE com FK para CablePath, que é local de cada schema, quebrava o merge.
- Outros: #640 (falsos conflitos depois de um sync), #641 e #650 (delete e undo), #622 (branch preso em status de transição), #668 e #688 (squash).

Já no main depois da 1.2.3, ainda sem tag: #711 (colunas geradas no provisionamento), #713 (renderização de conflitos sem limite) e #728.

**Testes:** não há nenhum teste de concorrência (nem threads, nem dois jobs), nenhum de corrida na marca d'água do sync, nenhum de revert depois de mudanças no main, e nenhum `assertNumQueries` no caminho de request ou merge.

## Como medir (com o harness em `diode/bench/`)
1. **F2:** cenário "candidate + branch", com o reconciler enviando `X-NetBox-Branch` e ingestão contínua. No meio da carga, POST `/api/plugins/branching/branches/{id}/merge/`. Depois comparar `SELECT count(*) FROM branch_<id>.core_objectchange` com o número de linhas em `netbox_branching_appliedchange` para esse branch, e os objetos do branch com os do main. Qualquer diferença confirma.
2. **F1:** subir 2 rqworkers e disparar dois POSTs de merge (ou de sync) em paralelo. Verificar os jobs, o status final e se há ObjectChanges duplicados no main.
3. **F3:** no main, um bulk apply grande (transação longa) e, ao mesmo tempo, um sync. Depois rodar um segundo sync e comparar o main com o branch para os objetos do lote.
4. **F6:** com o Diode no branch, disparar um sync e contar os ingestion logs em falha com 400 dentro da janela do sync.
5. **F7, F8, F9:** A/B do mesmo bulk apply no main, com e sem `netbox_branching` em `PLUGINS`. Medir latência, tempo do py-spy em `database.py`/`supports_branching` e quantas queries em `netbox_branching_changediff` aparecem no `pg_stat_statements`.
6. **F10:** tempo e RSS do worker no merge com 1k, 10k e 50k mudanças. Ver no `pg_stat_statements` as queries em `django_content_type` e `users_user`.
7. **F13:** `pg_stat_activity` com N branches ativos e os workers sob carga.

## Top 5 melhorias (valor/esforço)
1. **Atualizar para 1.2.3** (ou para o main): elimina #672 e #675, que afetam o Diode de forma direta. Esforço mínimo.
2. **Compare-and-set nas mudanças de status:** `filter(pk=…, status=READY).update(status=MERGING)` e abortar se nada for atualizado (F1). Algumas linhas por operação.
3. **Isolar as escritas do merge/sync:** `pg_advisory_xact_lock_shared(branch.pk)` em cada request que escreve no branch e lock exclusivo no merge/sync. Marcar o status *antes* de ler o changelog (F2). Esforço médio, e é o que mais reduz risco.
4. **Fast-path no router:** checar `active_branch.get()` antes de tudo e memoizar `supports_branching` por modelo. Aproveitar para guardar o branch no request uma vez só, sem a segunda busca (F7 e F9). Esforço baixo; ganho em todo request que não usa branch.
5. **Resposta HTTP para branch indisponível:** 503 + `Retry-After` para status transitórios e 410/409 para merged/archived. No Diode, tratar 503 como retry e invalidar o branch padrão quando ele estiver terminal (F6). Esforço baixo, nos dois lados.

Em seguida: sync com marca d'água por id ou `AppliedChange` em vez de `time` (F3) e checagem de conflito e dependências no revert (F5).

---
Verificação manual (2026-11-14): F2 (`models/branches.py:1147-1156`, changelog lido antes do status MERGING) e F7 (`database.py:31-35`, `supports_branching` antes de `active_branch.get()`) conferidos no código.
