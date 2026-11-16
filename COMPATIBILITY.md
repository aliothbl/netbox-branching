# Compatibility Matrix

| Release | Minimum NetBox Version | Maximum NetBox Version |
|---------|------------------------|------------------------|
| _next_  | 4.7.4                  | 4.7.x                  |
| 1.2.3   | 4.7.0                  | 4.7.x                  |
| 1.2.2   | 4.7.0                  | 4.7.x                  |
| 1.2.1   | 4.7.0                  | 4.7.x                  |
| 1.2.0   | 4.7.0                  | 4.7.x                  |
| 1.1.3   | 4.4.1                  | 4.6.x                  |
| 1.1.2   | 4.4.1                  | 4.6.x                  |
| 1.1.1   | 4.4.1                  | 4.6.x                  |
| 1.1.0   | 4.4.1                  | 4.6.x                  |
| 1.0.5   | 4.4.1                  | 4.6.x                  |
| 1.0.4   | 4.4.1                  | 4.6.x                  |
| 1.0.3   | 4.4.1                  | 4.6.x                  |
| 1.0.2   | 4.4.1                  | 4.6.x                  |
| 1.0.1   | 4.4.1                  | 4.6.x                  |
| 1.0.0   | 4.4.1                  | 4.6.x                  |
| 0.9.1   | 4.4.1                  | 4.6.x                  |
| 0.9.0   | 4.4.1                  | 4.6.x                  |
| 0.8.0   | 4.4.1                  | 4.5.x                  |
| 0.7.4   | 4.4.1                  | 4.5.x                  |
| 0.7.3   | 4.4.1                  | 4.4.x                  |
| 0.7.2   | 4.4.1                  | 4.4.x                  |
| 0.7.0   | 4.4.0                  | 4.4.x                  |
| 0.6.2   | 4.3.2                  | 4.3.x                  |
| 0.6.1   | 4.3.2                  | 4.3.x                  |
| 0.6.0   | 4.3.2                  | 4.3.x                  |
| 0.5.7   | 4.1.9                  | 4.3.x                  |
| 0.5.6   | 4.1.9                  | 4.3.x                  |
| 0.5.5   | 4.1.9                  | 4.3.x                  |
| 0.5.4   | 4.1.9                  | 4.3.x                  |
| 0.5.3   | 4.1.9                  | 4.3.x                  |
| 0.5.2   | 4.1.0                  | 4.3.x                  |
| 0.5.1   | 4.1.0                  | 4.3.x                  |
| 0.5.0   | 4.1.0                  | 4.3.x                  |
| 0.4.0   | 4.1.0                  | 4.3.x                  |

**NetBox 4.7.0 – 4.7.3 and cables.** Before NetBox 4.7.4, some cable changes (clearing a cable end,
moving or reordering terminations, deleting a cable) were not fully recorded in the change log, so
merging, reverting or syncing a branch that contains them could leave cable paths broken. The test
suite shows it: 33 failures on 4.7.0 and 4.7.1, 12 on 4.7.2, 1 (a pinned query count) on 4.7.3, none on
4.7.4 and 4.7.5. Hence the minimum of 4.7.4 for the next release.
