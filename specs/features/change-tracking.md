# Feature: change-tracking

**Keywords:** ObjectChange, ChangeDiff, original, modified, current, conflito, signal_receivers
**Arquivos principais:**
  - netbox_branching/signal_receivers.py
  - netbox_branching/models/changes.py
**Resumo:** Registra mudanças por schema e mantém ChangeDiff para detectar conflitos entre branch e main.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1739 | Marca d'água do sync | mudanças do main puladas; current não atualizado em SYNCING
- SPEC-20261114-1742 | Fast-path (F8) | SELECT em ChangeDiff a cada UPDATE/DELETE no main

## Estado atual
Cada ObjectChange cria ou atualiza um `ChangeDiff` (`signal_receivers.py:108`). Mudanças no main atualizam `ChangeDiff.current` só de branches READY (`:134-135`) e fazem um SELECT em ChangeDiff para todo UPDATE/DELETE, mesmo sem branch (`:124-136`).

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
- SPEC-20261114-1739 | `ObjectChange.time` é `auto_now_add`: o momento do save(), não do commit. Não serve como marca d'água de visibilidade (2026-11-14 17:39)
