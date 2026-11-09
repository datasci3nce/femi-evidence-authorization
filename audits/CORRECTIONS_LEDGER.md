# Research corrections ledger (post-hoc, not a consolidated paper)

**Prepared:** 2026-11-08. **Inputs:** original FEMI-1 execution packet, live-results ZIP, independent result review, ACTION-ID revised pilot report, and Swarm Research Audit. No new model calls and no rescoring of recorded outcomes.

| ID | Correction | Verified basis | Scope / what remains unchanged |
|---|---|---|---|
| R01 | FEMI-1 has **20 auditor-visible content templates** (4 certificate patterns × 5 treatments), each repeated **24** times. There are 160 distinct literal JSON requests because of 32 opaque IDs × 5 treatments, repeated three times. | Frozen 480-row request manifest, canonical JSON; only replace `case_[0-9a-f]{20}` with a placeholder. | Still 32 underlying generated ML cases. All 480 factual verdicts unchanged. Not 480 independent reasoning tasks. |
| R02 | Distinguish checksum of execution ZIP from uploaded live-results ZIP. | SHA-256 from local bytes and `manifest_sha256.json`. | Execution packet `7d9a0c5201eac2e475c2b7385963da4f4df675c8b93ddd0daf0fab061a41e75e`; results ZIP `eff6dbb490e63949269da459d6505fe4e4250661204f723d845773acb95729d6`. The old review mislabeled the execution-packet checksum. |
| R03 | Three evidence-absent APPROVE decisions were violations of the instruction to defer; prompt expectation of an upcoming record is only a **possible untested contributor**, not a demonstrated cause. | Absent controls and common system instruction. | 3 APPROVE, 4 DEFER, 1 malformed; no downstream real authorization performed. |
| R04 | Preserve the FEMI null result as a targeted valid negative finding: competing text did not change the supplied-verdict decision **in these 20 templates**. | Frozen request/response hashes; complete main responses. | Do not call it broad evidence reasoning or generalized attack resistance. |
| R05 | LinuxArena 189 lexical hits are **unreviewed candidates**, not 189 inspected negatives and not verified certificate misuse. The scanned-trajectory denominator was not independently established in uploaded outputs. | Candidate rows; scanner description; missing raw tool windows. | Zero *confirmed* instances means zero verified so far, not evidence of zero prevalence. |
| R06 | SALT 1,804/8,148 is a historical episode-label transition, not stale-certificate reuse. The `collusion == both_accept` equality is a label/definition check, not independent detector validation. | Reproduced derived table and label notes. | Numerical counts unchanged; original SALT source export not available for full trace audit. |
| R07 | ACTION-ID 13 correct decisive verdicts address factual correctness, not source support or explanation. Six full-evidence deferrals remain descriptive. | Original 36 decision records and prior correction ledger. | No identified mechanism of distrust or swarm amplification. |
| R08 | Absence of provenance graph-node citations was **not a model failure** because the agent interface did not supply those IDs. | `stage_input()` interface in original package. | Structural graph checks remain valid bookkeeping, not semantic proof. |
| R09 | Do not claim selective record acquisition or blame attribution follows automatically from current results. Identifiability of which record helps is an additional feasibility condition. | Distinct targets in protocols; existing dataset screens. | A future research choice, not a correction to any frozen outcome. |

## Artifact integrity

- FEMI-1 frozen execution packet (used for live run): `7d9a0c5201eac2e475c2b7385963da4f4df675c8b93ddd0daf0fab061a41e75e`.
- FEMI-1 actual live-results archive: `eff6dbb490e63949269da459d6505fe4e4250661204f723d845773acb95729d6`.
- Local preregistration: **not externally timestamped**. A ZIP hash proves integrity of the bytes, not a preregistration date.
- ACTION-ID original 36-decision ledger, original FEMI responses, and SALT/LinuxArena outputs were not modified.

## Scientific interpretation to retain

The pilot demonstrated limited but genuine phenomena: no complete-claim promotion in tested no-tool handoffs, at least one narrower source-attribution error, perfect adherence to the explicit trusted verdict under the fixed FEMI interventions, and three approvals that attributed support to a missing record. The size and interface conditions sharply limit generalization. The research target remains **whether a specific verification decision is justified by the observations actually available**, not necessarily which agent should be blamed.
