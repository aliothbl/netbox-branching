# Feature: upstream-sync

**Keywords:** upstream, sync, fork, netboxlabs, main, tags
**Arquivos principais:**
  - (git) remotes origin=aliothbl/netbox-branching, upstream=netboxlabs/netbox-branching
**Resumo:** Manter o fork alinhado com netboxlabs/netbox-branching (main + tags) sem conflito com o specs/ local.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
—

## Estado atual
Em 2026-11-14 o fork está idêntico ao upstream: `main` @ `bb2f951`, `git rev-list --left-right --count main...upstream/main` = `0 0`. Última tag `v1.2.3`. No main após a tag: #711 (colunas geradas no provisionamento), #713 (render de conflitos sem limite), #728. Runbook manual em `specs/README.md`.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
—
