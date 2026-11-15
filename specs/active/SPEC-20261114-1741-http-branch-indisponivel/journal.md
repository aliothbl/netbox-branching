# Journal — SPEC-20261114-1741-http-branch-indisponivel

## SNAPSHOT
- **Fase:** implementação (middleware + testes).
- **Contrato decidido** (DEC-1, DEC-2): API com branch transitório → `503` + `Retry-After`; terminal → `409`; corpo JSON `{"detail": "Selected branch is not ready.", "retryable": <bool>}`, sem nome nem status do branch. Branch inexistente segue `400`. UI sem mudança.
- **Evidência que motiva:** F6 reproduzido 5/5 (SPEC-1736; `aliothbl/diode:bench/results/20261115-094726-*`).
- **Próximo passo:** implementar, testar na suíte, então a SPEC par do diode (1748) e o bench `branch-sync-ingest`.

## Decisões
- **DEC-1 (owner, 2026-11-15 12:16) — corpo sem nome e sem status do branch.** A resposta sai antes da autenticação, e o upstream fixa num teste (#672) que nome e status do branch não vazam nela. O corpo leva só `detail` (a mensagem estática atual) e `retryable`. O código HTTP (503 × 409) já diz ao cliente se deve esperar. Isso substitui o `{"branch", "status", "retryable"}` do escopo original.
- **DEC-2 (owner, 2026-11-15 12:16) — branch inexistente continua `400`.** Menor mudança de contrato (também fixada em teste no upstream), e o F6 não depende disso. Substitui o `404` do escopo original.

## LOG
- 2026-11-15 12:16 — SPEC ativada no branch `spec/20261114-1741-http-branch-indisponivel` (a partir de `main` `d091fd3`). DEC-1 e DEC-2 registradas.
