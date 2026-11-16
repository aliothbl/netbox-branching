# Journal — SPEC-20261115-1916-suite-verde-netbox-4-7-0

## SNAPSHOT
- **Fase:** concluída no fork (suíte verde em 4.7.4 e 4.7.5); falta o CI do fork rodar a matriz nova e mover o bench do diode para 4.7.4+.
- **Diagnóstico:** as 33 falhas são do **NetBox core 4.7.0**, não do plugin. A mesma árvore (`main` `89d0b78`) passa inteira no 4.7.5 (605 testes, 0 falhas).

## Decisões
- **DEC-1 — Diagnóstico por versão do NetBox** (imagens oficiais `netboxcommunity/netbox:v4.7.x`, runner `aliothbl/diode:bench/tools/nbb-test.sh` com `NBB_IMAGE`). Os 33 testes que falham no 4.7.0:

  | NetBox | Falhas | O que sobra |
  |---|---|---|
  | 4.7.0 | 33 | tudo (cabos ×31, request em background, query count) |
  | 4.7.1 | 33 | idem |
  | 4.7.2 | 12 | cabos "clear end" (merge/revert/sync), reorder no sync, request em background, query count |
  | 4.7.3 | 1 | só `test_views.test_list_objects_with_permission` (número de queries fixado no teste) |
  | 4.7.4 | 0 | — |
  | 4.7.5 | 0 (suíte completa: 605) | — |

  O diff do core 4.7.0 → 4.7.5 mostra o mecanismo: o 4.7.x passou a registrar no changelog a desconexão das terminações de um cabo apagado (antes, `UPDATE` direto, sem ObjectChange; `dcim/signals.py`, `nullify_connected_endpoints`), a respeitar o alias da deleção e a só retraçar o status quando ele foi escrito. O merge/revert/sync do plugin reaplica o changelog; o que o core não registra não é reaplicado, e os cable paths ficam errados no destino. **Ou seja, é um defeito funcional para quem usa o 4.7.0–4.7.2, não só de teste.**
- **DEC-2 — `min_version = 4.7.4`**, a primeira em que a suíte inteira passa. A 4.7.3 já tem o comportamento de cabos correto; a única falha nela é um número de queries fixado no teste. Escolha conservadora: a invariante da SPEC é "suíte verde em toda a faixa suportada".
- **DEC-3 — CI testa o mínimo:** `netbox-ref: v4.7.4` na matriz, além de `main`. `.copier-answers.yml` alinhado (`netbox_min_version`, `netbox_test_min_ref`).
- **Efeito colateral (fora deste repo):** o bench do diode (`aliothbl/diode:bench`) usa a imagem NetBox 4.7.0 e monta o `main` deste fork; com o `min_version` novo, o plugin não carrega mais nela. O bench precisa ir para 4.7.4+.

## LOG
- 2026-11-16 10:45 — **Validado.** Suíte completa no NetBox 4.7.4 (`main` `89d0b78`): 605 testes, 0 falhas (`...-full-main-netbox474.log`). Com o código desta SPEC (`min_version` 4.7.4): carrega no 4.7.4 (`test_config` OK) e é recusado no 4.7.0 ("requires NetBox minimum version 4.7.4"; `...-1916-on-470.log`).
- 2026-11-16 09:57 — SPEC ativada (branch a partir de `main` `89d0b78`, num worktree). Suítes: 4.7.5 completa OK (`aliothbl/diode:bench/evidence/logs/20261116-nbb-test-full-main-netbox475.log`); os 33 testes em 4.7.1–4.7.4 (`...-nbb-test-33-netbox4.7.{1,2,3,4}.log`). Mudanças: `min_version`, CI, `.copier-answers.yml`, `COMPATIBILITY.md` (linha "_next_" + nota sobre cabos), exemplos em `docs/netbox-docker.md`, `AGENTS.md`. Rodando a suíte completa no 4.7.4.
