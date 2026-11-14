# Journal — SPEC-20261114-1736-benchmark-reproducao-branching

## SNAPSHOT
- **Fase:** 1 — cenário `branch-merge-race` (F2) implementado; primeira execução em andamento.
- **Código do harness:** `aliothbl/diode` branch `perf/bench-vs-upstream`, `bench/`:
  - `compose.branching.yaml`: monta `BRANCHING_SRC/netbox_branching` sobre o pacote pip 1.2.0 da imagem;
  - `branch_scenarios.py`: driver dos cenários;
  - `run.sh`: cenários `branch-*`; seed por `plugin-rev + nbb-rev`.
- **Versão sob teste:** fork `aliothbl/netbox-branching` (main + specs; código = upstream `bb2f951`, ≈ v1.2.3+).
- **Próximo passo:** validar a primeira execução, depois ≥5 execuções para taxa de reprodução; em seguida F1 (`branch-double-merge`) e F7 (`router-overhead`).

## Decisões
- **DEC-1 — Merge e provisionamento síncronos via `nbshell`**, em vez de RQ. `MergeBranchJob.run` só tira um snapshot de resumo e chama `Branch.merge()` (`jobs.py:199-219`). `BranchJobRunner.branch_status` é só metadado e não muda o status no enqueue (`jobs.py:66-91`). A chamada direta reproduz a mesma janela, sem depender de worker.
- **DEC-2 — Medida do F2 por objeto, não por changelog.** `AppliedChange.change` aponta para os ObjectChanges que o merge cria no main (`models/changes.py:391-397`), então não casa 1:1 com os do branch. Perda = chave natural (device, device/interface, IP/máscara) presente no schema do branch e ausente em `public` depois do merge.
- **DEC-3 — O pacote do fork é montado sobre `site-packages`.** O `sys.path[0]` vazio poderia favorecer `/opt/netbox/netbox`, mas não é garantido sob o granian.

## LOG
- 2026-11-14 18:17 — SPEC ativada no branch `spec/20261114-1736-benchmark-reproducao`.
- 2026-11-14 19:01 — **F2 reproduzido (1ª execução válida).** Merge disparado com 240/540 assentados. O merge leu 500 ObjectChanges; o branch terminou com 569. **69 mudanças (5 devices, 31 interfaces, 33 IPs) ficaram só no schema do branch.** Branch marcado MERGED sem erro; o Diode registrou essas entidades como APPLIED (0 FAILED). Perda silenciosa nos dois lados. Antes disso, três falhas do *harness* (não do plugin), corrigidas:
  - (a) o parser não aceitava o prefixo `>>> ` do console;
  - (b) no console interativo, um `try/except` sem linha em branco não executa, e o "merge de 6 ms" era isso. Agora o script vai num único `exec(...)`;
  - (c) o boot do `nbshell` (vários segundos) atrasava o merge para depois da carga. Agora o shell sobe antes e espera o gatilho `/tmp/bench-merge-go`.

  Rodando 5 execuções para a taxa de reprodução.
- 2026-11-14 18:25 — Cenário `branch-merge-race` implementado (60 devices, 540 entidades; merge disparado com 40% assentado; `CONCURRENCY=4`). Primeira execução com `--keep` iniciada.
