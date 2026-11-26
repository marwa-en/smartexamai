# Correspondance ATT&CK · OWASP · tests · détection

| Menace | MITRE ATT&CK / ATLAS | OWASP | Test(s) `pentest/` | Détection (`soc/sigma`) |
|---|---|---|---|---|
| Brute force / spraying | T1110, T1110.003 | API2:2023 | `test_02` | 01, 02 |
| Jeton forgé / rejoué | T1550.001, T1078 | API2:2023 | `test_01`, `test_08` | 04 |
| IDOR / BOLA, escalade | T1068, T1078.004 | API1, API5 | `test_03` | 05 |
| Upload malveillant | T1190, T1505.003 | API8, CWE-434 | `test_04` | 05 |
| CSRF / site tiers | T1189 | A01, CWE-352 | `test_07` | 03 |
| Prompt injection | ATLAS AML.T0051 | LLM01 | `test_05` | 06 |
| Sortie LLM non fiable (note) | ATLAS AML.T0048 | LLM02, LLM09 | `test_05` | 06 |
| Évasion de conteneur / DoS ressources | T1611, T1496 | CIS Docker 5.x | `test_06` | — (supervision Docker) |
| Désactivation de la défense / logs absents | T1562 | A09:2021 | `test_09` | toutes |
| Fuite de secrets / BD versionnée | T1552.001 | A05 | `test_09` | gitleaks (CI) |
| Vol de jeton via XSS | T1539 | A03 | `test_10` | — |
