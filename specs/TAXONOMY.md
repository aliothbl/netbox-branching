# TAXONOMY.md — vocabulário canônico de áreas

> Toda feature de `specs/features/` DEVE corresponder a uma área daqui (R.4/R.13). Área nova = confirmação explícita do usuário.

## Áreas

- upstream-sync — Sincronização do fork aliothbl/netbox-branching com netboxlabs/netbox-branching (main, tags)
- provisioning — Criação do schema `branch_<id>`, cópia das tabelas a partir de snapshot, sequences de ID compartilhadas com o main
- routing — Seleção do branch ativo (header `X-NetBox-Branch`, `?_branch=`, cookie), contextvar `active_branch`, `BranchAwareRouter`, aliases e conexões por schema, `BranchMiddleware`
- change-tracking — `ObjectChange` por schema, `ChangeDiff` (original/modified/current), detecção de conflitos
- sync-merge-revert — Jobs de sync, merge, revert e archive; transições de status do Branch; merge strategies (iterative, squash); `AppliedChange`
- migrations — Migrations aplicadas em branches, status `pending-migrations`, schema drift entre main e branch
- permissions — Autorização para ver, ativar, escrever, sincronizar e mergear branches; `owner`
- integration-diode — Contrato com o ecossistema Diode: branch padrão do diode-netbox-plugin, header `X-NetBox-Branch` vindo do reconciler, códigos HTTP para branch indisponível
- ci-tests — Suíte de testes, cobertura de concorrência, benchmarks, workflows
