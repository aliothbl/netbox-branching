# specs/ — sistema SPEC-driven do fork `aliothbl/netbox-branching`

Este diretório adota o padrão SPEC-driven do projeto **wynk_crm** (schema `sdd-4.0`), o mesmo já usado nos forks `aliothbl/diode`, `diode-sdk-python` e `diode-netbox-plugin`. Referência: `wynk_crm/docs/RULES.md` e `wynk_crm/docs/rules/formats.md`. A estrutura, os campos e a gramática dos critérios de aceite são os mesmos.

## Por que `specs/` e não `docs/`

`docs/` pertence ao upstream (netboxlabs) e é publicado via mkdocs (`mkdocs.yml`). Qualquer `.md` lá dentro seria publicado. Um diretório **que não existe no upstream** tem duas vantagens: (1) nenhuma sincronização com o upstream gera conflito, e (2) nenhum documento interno é publicado por engano.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `specs/future/SPEC-<YYYYMMDD-HHMM>-<slug>/main.md` | SPEC planejada (`Status: draft`). Só `main.md`. |
| `specs/active/` | SPEC em execução: `main.md` + `journal.md` (SNAPSHOT + LOG append-only). Vazio em `main`; SPEC ativa vive em branch. |
| `specs/archive/`, `specs/discard/` | Concluídas / descartadas, com `digest.md`. Nunca deletar. |
| `specs/features/<area>.md` | Memória viva por área: estado atual, decisões (DEC-…), gotchas, SPECs da área. |
| `specs/TAXONOMY.md` | Áreas canônicas. Toda SPEC vincula ≥1 área daqui. |
| `specs/ROADMAP.md` | Ordem de execução (priorização humana) das SPECs future. |
| `specs/DIAGNOSTICO-2026-11-14.md` | Diagnóstico que originou as SPECs (leitura de código, achados F1–F15). |

Dependências com outros repos (ex.: o reconciler do Diode consumindo códigos HTTP deste plugin) entram no programa cross-repo `aliothbl/diode:specs/programs/diode-stack-hardening.md`.

## Regras essenciais (resumo de wynk_crm RULES R.1–R.17)

1. ID = `SPEC-YYYYMMDD-HHMM-slug`, com timestamp real (HHMM válido). Proibido sequencial ou reuso.
2. `main.md` é o **contrato** validado por humano. Plano, progresso e decisões vão no `journal.md`, não no main.
3. Critério de aceite por porte: **P** usa `specctl check`/marcação com timestamp+commit. **M/G** usam `| verify: \`cmd\``. Humano: `| evidence: manual @user`. `[x]` só com timestamp e evidência.
4. Deferir, aceitar incompleto ou reduzir escopo **só com autorização explícita do usuário** (`[aceito-incompleto: "<citação>" ts]`).
5. Commits sob SPEC ativa levam o trailer `Spec: SPEC-<id>`.
6. Segredo em `specs/` é proibido (`<REDACTED:tipo>`).
7. **Upstream-first como regra de longo prazo**: uma melhoria vira PR em `netboxlabs/netbox-branching` e fica no fork só até o merge. **Decisão vigente do owner (2026-11-14): nada vai para a NetBox Labs por enquanto.** O trabalho fica no fork, e cada PR upstream exige um OK explícito.
8. **Medir antes de mudar**: SPEC de performance ou de concorrência só é concluída com reprodução antes/depois. O harness é `aliothbl/diode:bench/`, estendido pela SPEC-20261114-1736.

## Testes

A suíte roda dentro de um NetBox (ver `docs/development/` e `CLAUDE.md`/`AGENTS.md` na raiz). Toda SPEC que corrige corrida ou perda de dados precisa de um teste que **falhe antes** da correção.

## Sincronização com upstream (runbook manual)

```bash
git remote add upstream https://github.com/netboxlabs/netbox-branching.git   # uma vez
git fetch upstream --tags
git rev-list --left-right --count main...upstream/main          # "<nossos> <deles>"
git switch main && git merge --ff-only upstream/main || git merge --no-ff upstream/main
git push origin main --follow-tags
```
