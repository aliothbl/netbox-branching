# ROADMAP — ordem de execução do backlog

> Priorização humana das SPECs future (proposta inicial do diagnóstico de 2026-11-14; o owner reordena por PR dedicado). A SPEC 1741 também está no programa cross-repo `aliothbl/diode:specs/programs/diode-stack-hardening.md`, junto com o seu par no diode.

> Regra 8 do README: corrida e performance só fecham com reprodução antes/depois, então a 1736 vem primeiro.

1. SPEC-20261114-1736-benchmark-reproducao-branching — onda 0 (habilitadora: reproduz F1/F2/F3/F6, mede F7–F9)
2. SPEC-20261114-1737-cas-transicoes-status — onda 1 (alta/baixa; pré-requisito da 1738)
3. SPEC-20261114-1738-bloqueio-escritas-merge-sync — onda 1 (**crítica**/média; perda silenciosa de dados)
4. SPEC-20261114-1741-http-branch-indisponivel — onda 1 (alta/baixa; par com diode SPEC-20261114-1748)
5. SPEC-20261114-1742-router-fast-path — onda 2 (performance em todo request; alto valor/baixo esforço)
6. SPEC-20261114-1739-sync-marca-dagua-por-commit — onda 2 (alta/média)
7. SPEC-20261114-1740-revert-com-conflitos-e-dependencias — onda 2 (alta/média)
8. SPEC-20261114-1744-autorizacao-ativacao-branch — onda 3 (média/média; segurança)
9. SPEC-20261114-1743-merge-escalavel — onda 3 (média/baixa)
10. SPEC-20261114-1745-sequences-tabelas-novas-na-migracao — onda 3 (média/baixa; confirmar antes)
11. SPEC-20261114-1746-conexoes-por-branch — onda 4 (média/média; medir antes)

## Fora deste repo
- **Versão em uso:** o stack de teste do diode-netbox-plugin fixa `netboxlabs-netbox-branching==1.2.0`. A 1.2.3 corrige #672 (500 em vez de 400 com branch indisponível) e #675 (webhooks/scripts quebrados no NetBox 4.7), que afetam o Diode. → `aliothbl/diode-netbox-plugin:specs/future/SPEC-20261114-1747-bump-netbox-branching-1-2-3`.
