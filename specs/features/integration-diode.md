# Feature: integration-diode

**Keywords:** diode, diode-netbox-plugin, branch-padrão, default-branch, X-NetBox-Branch, reconciler, 400, 503
**Arquivos principais:**
  - netbox_branching/middleware.py
  - (diode) diode-server/netboxdiodeplugin/client.go
  - (diode) diode-server/reconciler/ops.go
  - (diode-netbox-plugin) Setting de branch padrão
**Resumo:** Contrato entre este plugin e o ecossistema Diode, que escreve no NetBox em lote e pode mirar um branch padrão.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1741 | Códigos HTTP | 400 vira falha permanente no reconciler (par: diode SPEC-20261114-1748)
- SPEC-20261114-1738 | Bloqueio em merge/sync | bulk-plan-apply longo do Diode é o caso típico de escrita perdida

## Estado atual
O diode-netbox-plugin guarda um branch padrão (Setting) e o reconciler o envia em `X-NetBox-Branch`. O reconciler trata qualquer `>=400` do bulk-plan-apply como falha do lote inteiro (`diode-server/reconciler/ops.go:663-665`). Este plugin devolve 400 para branch não-READY, o que inclui um sync em andamento. Um branch padrão mergeado/arquivado continua no Setting (segundo o diagnóstico, o form filtra `ready` só ao salvar; não verificado), e aí a falha é permanente. No benchmark do Diode (2026-11-14) todo request de apply passou por `BranchMiddleware`, mesmo sem branch.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261114-1741 | Stack de teste do diode-netbox-plugin fixa netbox-branching 1.2.0, anterior às correções #672/#675 (2026-11-14 17:41)
