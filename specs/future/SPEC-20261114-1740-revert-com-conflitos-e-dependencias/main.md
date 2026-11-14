# SPEC-20261114-1740: Revert checa conflitos e dependências antes de desfazer

**Status:** draft
**Porte:** M
**Owner:** @aliothbl
**Criada:** 2026-11-14 17:40
**Ativada:** —
**Pausada em:** —
**Concluída:** —
**Commit final:** —
**Keywords:** revert, undo, cascade, delete, conflito, dependências, AppliedChange, dry-run
**Features:** sync-merge-revert, change-tracking
**Branch:** _(a definir na ativação)_
**Programa:** —
**Relacionadas:** SPEC-20261114-1737 (status REVERTING via CAS)
**Origem:** DIAGNOSTICO F5.
**Resumo:** O revert de um branch mergeado desfaz as mudanças em ordem inversa sem comparar com o estado atual do main. Desfazer um CREATE apaga em cascata objetos criados depois no main, e desfazer um UPDATE sobrescreve edições posteriores.

## Objetivo

`revert()` chama `undo()` em ordem inversa (`models/changes.py:186-196`), e a action da API não chama `_check_conflicts` (`api/views.py:118-133`). Cenários:
- **CREATE desfeito:** o branch criou um Device e foi mergeado. Depois, no main, alguém criou interfaces e IPs nesse Device. O revert faz `instance.delete()`, e o CASCADE do NetBox apaga dados que nunca pertenceram ao branch.
- **UPDATE desfeito:** volta campos para o valor de antes do merge, apagando edições feitas no main depois dele.

## Escopo

**DENTRO:**
- Pré-checagem do revert, também disponível como dry-run na API:
  - para cada UPDATE, comparar o estado atual do objeto no main com o estado pós-merge (`AppliedChange`/ChangeDiff). Divergência é conflito;
  - para cada CREATE desfeito, coletar os dependentes (o `Collector` do Django) que **não** foram criados pelo próprio branch. Existir algum é conflito.
- A action de revert recusa com 409 e lista os conflitos. Com confirmação explícita (`acknowledge_conflicts`, como no merge), segue em frente.
- UI: mostrar os conflitos antes de confirmar.

**FORA:**
- Revert parcial (por objeto) — pode virar SPEC futura.

## Invariantes
- NUNCA o revert apaga ou altera dado do main que não veio do branch sem confirmação explícita do usuário.

## Critério de aceite
- [ ] Teste: revert de CREATE com dependente criado no main → recusado com conflito listando o dependente | verify: `./manage.py test netbox_branching.tests.test_revert_conflicts`
- [ ] Teste: revert de UPDATE com edição posterior no main → recusado com conflito | verify: `./manage.py test netbox_branching.tests.test_revert_conflicts`
- [ ] Teste: com `acknowledge_conflicts`, o revert prossegue, e o comportamento sem conflitos é o atual | verify: `./manage.py test netbox_branching.tests.test_revert_conflicts`
