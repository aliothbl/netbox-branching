# Feature: ci-tests

**Keywords:** testes, concorrência, assertNumQueries, benchmark, harness, py-spy, pg_stat_statements
**Arquivos principais:**
  - netbox_branching/tests/
  - (diode) bench/
**Resumo:** Cobertura de testes e benchmarks do plugin.

## Specs desta feature
### Concluídas
—
### Planejadas (future/)
- SPEC-20261114-1736 | Reprodução e benchmark | nada de concorrência é testado hoje

## Estado atual
Segundo o diagnóstico, não há teste de concorrência (threads ou dois jobs), nem de corrida na marca d'água do sync, nem de revert após mudanças no main, nem `assertNumQueries` nos caminhos de request e merge. O harness de benchmark de ponta a ponta existe no fork do diode (`bench/`) e roda NetBox 4.7.0 com este plugin carregado.

## Decisões arquiteturais ativas
—

## Alternativas consideradas e rejeitadas
—

## Gotchas
—
