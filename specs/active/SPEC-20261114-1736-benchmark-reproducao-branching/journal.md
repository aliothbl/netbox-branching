# Journal — SPEC-20261114-1736-benchmark-reproducao-branching

## SNAPSHOT
- **Fase:** 1 concluída: F2 reproduzido 6/6. Próximo: F1 (`branch-double-merge`) e F7 (`router-overhead`).
- **Código do harness:** `aliothbl/diode` branch `perf/bench-vs-upstream`, `bench/`:
  - `compose.branching.yaml`: monta `BRANCHING_SRC/netbox_branching` sobre o pacote pip 1.2.0 da imagem;
  - `branch_scenarios.py`: driver dos cenários;
  - `run.sh`: cenários `branch-*`; seed por `plugin-rev + nbb-rev`.
- **Versão sob teste:** fork `aliothbl/netbox-branching` (main + specs; código = upstream `bb2f951`, ≈ v1.2.3+).
- **Próximo passo:** cenário `branch-double-merge` (F1), depois `router-overhead` (F7/F8/F9) e `branch-sync-ingest` (F6).

## Decisões
- **DEC-1 — Merge e provisionamento síncronos via `nbshell`**, em vez de RQ. `MergeBranchJob.run` só tira um snapshot de resumo e chama `Branch.merge()` (`jobs.py:199-219`). `BranchJobRunner.branch_status` é só metadado e não muda o status no enqueue (`jobs.py:66-91`). A chamada direta reproduz a mesma janela, sem depender de worker.
- **DEC-2 — Medida do F2 por objeto, não por changelog.** `AppliedChange.change` aponta para os ObjectChanges que o merge cria no main (`models/changes.py:391-397`), então não casa 1:1 com os do branch. Perda = chave natural (device, device/interface, IP/máscara) presente no schema do branch e ausente em `public` depois do merge.
- **DEC-3 — O pacote do fork é montado sobre `site-packages`.** O `sys.path[0]` vazio poderia favorecer `/opt/netbox/netbox`, mas não é garantido sob o granian.

## LOG
- 2026-11-15 10:54 — **F7 medido direto: custo real, mas pequeno (~1% do request).**
  - **Microbenchmark** (nbshell, sem branch ativo, 15 modelos que o Diode toca, melhor de 5 × 20 000 chamadas; netbox-branching do fork `5810e84`): chamada vazia 0,04 µs; `supports_branching` **2,38 µs** (1,46–3,41 por modelo); a mesma função atrás de `functools.lru_cache` **0,08 µs**; `db_for_read` 3,04 µs; `db_for_write` 3,24 µs.
  - **py-spy** (std, c=1, 90 s, 100 Hz; worker ocupado: 7422 amostras dentro do request do plugin; netbox-branching 1.2.0 do pip, mesmo router): `netbox_branching/database.py` em **1,36%** das amostras, `supports_branching` em **1,04%**.
  - **Estimativa** (derivada, não medida): a ~11 ent/s com c=1, um request custa ~90 ms por entidade, então o router fica com ~1,2 ms (~400 chamadas de ~3 µs). Com cache por modelo (invalidado quando muda `exempt_models` ou os resolvers), cada chamada cai para menos de 1 µs: **ganho ≤ ~1% do tempo de request**. Isso explica por que o A/B ponta a ponta (ruído ~7–10%) não teve resolução.
  - Evidências em `aliothbl/diode:bench/evidence/f7-20261115-1038/` (`micro.json`, profiles `.folded.gz`, `share.json`); ferramenta `bench/f7_router.py`. A tentativa de py-spy novo falhou (sem pip na imagem); a ferramenta foi corrigida para copiar o binário, mas não reexecutada.
- 2026-11-15 10:14 — **F6 (`branch-sync-ingest`): reproduzido 5/5.** O Diode ingere no branch padrão (60 devices / 540 entidades, `CONCURRENCY=4`, lote 25). O main tem 2000 mudanças com change logging (tags) e o sync é disparado com ~30% da carga assentada (shell pré-aquecido, gatilho `/tmp/bench-sync-go`). Resultados (diode `030b22c`, plugin `ae04547`, netbox-branching `5810e84`):
  - sync de 36,8–38,5 s; as 2000 mudanças chegam ao branch e ele volta para READY;
  - **190–265 entidades FAILED** com `400 Selected branch is not ready.` (35–49% da carga), e o Diode não tenta de novo;
  - objetos que nunca chegam ao branch: devices 21–29, interfaces 84–118, IPs 85–118;
  - em 2 das 5 execuções, 1–2 lotes também estouraram o timeout de apply de 120 s (P-10 do diode, em investigação).
  - Duas execuções de teste antes: (a) com lote 100, o sync caiu dentro de um único request em voo (que passou pelo middleware ainda READY), então 0 FAILED, sem valor como evidência; (b) com lote 25, F6 visível, mas **190 entidades ficaram presas em APPLYING com 0 FAILED**, porque o Diode upstream não conseguia gravar o erro de um corpo não-JSON (P-11, corrigido no fork do diode, `9e453e1`).
  - Resultados: `aliothbl/diode:bench/results/20261115-094726-*`, com logs completos dos containers em `*.logs/`.
  - Correção proposta (mais barata): o middleware responde **503 + `Retry-After`** para estados transitórios (syncing, merging, migrating, pending-migrations) e 409/410 para os terminais. O cliente de apply do Diode já faz retry em 503 (M-1 do fork).
- 2026-11-14 18:17 — SPEC ativada no branch `spec/20261114-1736-benchmark-reproducao`.
- 2026-11-14 21:20 — **F7/F8/F9 (`router-overhead`, A/B ponta a ponta): inconclusivo.** `std`, `CONCURRENCY=4`, ×3 cada. Com netbox-branching (fork): criação 17.8 ± 1.9 ent/s, atualização 17.6. Sem netbox-branching (`compose.nobranching.yaml`): criação 19.0 ± 1.4, atualização 18.3. A diferença média (~7%) fica dentro do ruído, que nesta rodada foi ~10× maior que no lote anterior da mesma configuração (20.08 ± 0.17). Conclusão: o A/B ponta a ponta não tem resolução para um custo de alguns por cento. Próximo: medir direto o tempo de `BranchAwareRouter._get_db`/`supports_branching` (py-spy ou microbenchmark por query) em vez de throughput. Achado colateral **do lado do Diode** (P-9, deadlock no Postgres do reconciler), registrado na SPEC-0807 do aliothbl/diode; não é do netbox-branching.
- 2026-11-14 20:27 — **F1 (`branch-double-merge`): concorrência reproduzida 9/9; dano permanente não observado.** Dois shells de merge liberados juntos sobre o mesmo branch READY (20 devices).
  - **Criação (6/6):** os dois merges sempre rodaram; o perdedor falhou com `IntegrityError` (`extras_tag_pkey`) em ~10.2–10.6 s e fez `update(status=READY)`; o vencedor gravou MERGED em ~12.9–13.8 s. Estado final sempre MERGED, main correto (209 ObjectChanges = branch).
  - **Atualização (3/3):** os dois merges terminaram MERGED, com **2 eventos MERGED** por branch. O main recebeu 81 ObjectChanges, não 160: reaplicar o mesmo valor não gera mudança.
  - **Conclusão:** a falta de CAS é real (o 2º merge nunca é impedido), mas o cenário previsto de "READY depois de MERGED" não ocorreu, porque o perdedor falha antes de o vencedor terminar. Dano observado: (1) janela de ~3 s com o branch READY e os dados já no main; uma escrita nela vai para um branch que vira MERGED logo depois, como no F2; (2) histórico de eventos com merge duplicado e trabalho em dobro. Severidade efetiva menor que a do F2; a SPEC-1737 continua válida (pré-requisito da 1738). Resultados: `bench/results/20261114-195103-*`, `-195928-*`, `-200356-*`, `-201651-*`.
  - Harness: chave do seed agora pelo hash de árvore do código (`HEAD:netbox_branching`, `HEAD:netbox_diode_plugin`), então commits só de specs não recriam o seed.
- 2026-11-14 19:35 — **F2: taxa de reprodução 6/6** (validação + 5 execuções; diode `6dbe897`, netbox-branching `631943c` = código upstream `bb2f951`; 60 devices / 540 entidades; `CONCURRENCY=4`). Merge disparado com 240–300/540 assentados. O merge leu 495–527 dos 569 ObjectChanges que o branch acabou tendo. Perdidos por merge (objetos só no schema do branch): devices 4–7, interfaces 18–33, IPs 19–34 (**41–76 objetos**). Branch sempre MERGED sem erro; o Diode registrou 0–1 FAILED. Resultados: `aliothbl/diode:bench/results/20261114-185707-*` e `20261114-191036-*`. F2 marcado como reproduzido no DIAGNOSTICO.
- 2026-11-14 19:01 — **F2 reproduzido (1ª execução válida).** Merge disparado com 240/540 assentados. O merge leu 500 ObjectChanges; o branch terminou com 569. **69 mudanças (5 devices, 31 interfaces, 33 IPs) ficaram só no schema do branch.** Branch marcado MERGED sem erro; o Diode registrou essas entidades como APPLIED (0 FAILED). Perda silenciosa nos dois lados. Antes disso, três falhas do *harness* (não do plugin), corrigidas:
  - (a) o parser não aceitava o prefixo `>>> ` do console;
  - (b) no console interativo, um `try/except` sem linha em branco não executa, e o "merge de 6 ms" era isso. Agora o script vai num único `exec(...)`;
  - (c) o boot do `nbshell` (vários segundos) atrasava o merge para depois da carga. Agora o shell sobe antes e espera o gatilho `/tmp/bench-merge-go`.

  Rodando 5 execuções para a taxa de reprodução.
- 2026-11-14 18:25 — Cenário `branch-merge-race` implementado (60 devices, 540 entidades; merge disparado com 40% assentado; `CONCURRENCY=4`). Primeira execução com `--keep` iniciada.
