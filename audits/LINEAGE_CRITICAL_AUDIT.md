# FEMI lineage and submission-critical audit — 9 November 2026

**Basis.** Reviewed the compiled Apart report and its evidence ledger, original frozen result archives where available locally, the corrected FEMI-1 independent review retrieved from the user's Library, the independent FEMI-2–4, transfer, cross-model, and causal audits, and Apart's live official Guidelines. External prior work was rechecked against arXiv and the ACL Anthology. This is an offline evidence and interpretation review; no additional inference calls and no external peer review.

## Executive decision

The measured missing-record behavior is a legitimate empirical observation, but the current report **requires material revision before being described as a complete lineage account**. Its strongest claim is operational rather than mechanistic: models sometimes produce APPROVE/REJECT and asserted evidence certification with no coordinator-origin record in the request. The precise internal explanation and applicability to autonomous swarms are not established. The test harness itself is a potentially misleading/incompletely formalized instruction interface.

## Reconstructed lineage

| Stage (source) | Distinct substantive contexts | Executions | Supported result | What it does not prove |
|---|---|---:|---|---|
| ACTION-ID role-separated pilot, Nov 7 | One workflow family, 12 chains / 4 configurations | 36 auditor views | No natural full-report verification promotion in no-tool chains; evidence-use concerns observed | Swarm amplification or attack propagation |
| **FEMI-1 fixed-evidence interference, Nov 7 — OMITTED FROM CURRENT PAPER** | 20 content templates across five treatments (4 logical certificate patterns × 5), 24 responses/template | 480 main + 8 absent controls | **480/480** followed trusted explicit reference verdict despite upstream variations. Absent controls: **3 APPROVE, 4 DEFER, 1 invalid** | Independent reasoning about raw evidence; general downstream-monitor resilience |
| FEMI-2, Nov 8 | 12 workflow contexts | 144 | Missing record: presupposed 21/36 vs conditional 0/36 | Independent context generality; fixed provider |
| FEMI-2R, Nov 8 | Same 12 | 144 | Groq-pinned repetition 9/36 vs 0/36 | Independent case replication |
| FEMI-3A, Nov 8 | 24 redesigned workflow contexts | 288 | **0/144** unauthorized in missing-source arms under redesigned interface | Effect of single instruction or universal presupposition vulnerability |
| FEMI-4, Nov 8 | Same 12 as FEMI-2; 192 unique requests repeated thrice | 576 | Original 12/36 vs conditional 0/36; stronger additional guards 20/36; 51 missing-source decisive responses | Stronger guards generally harmful; independent evidence interpretation |
| ContractNLI transfer, Nov 8 | 48 contracts but just **16 unique hypothesis prompts** without record | 288 | Presupposed 18/48 vs conditional 1/48 | 48 distinct missing-record questions |
| FEVEROUS transfer, Nov 8 | 48 distinct claims, oracle evidence | 288 | Presupposed 17/48 vs conditional 6/48; 2 invalid | Independently verified source extraction or entailment |
| Cross-model transfer subset, Nov 8 | Reuses **15 ContractNLI + 33 FEVEROUS** earlier cases | 864 | GPT-OSS 18/48 vs 1/48, Llama 1/48 vs 0/48, Gemini 45/48 vs 36/48 | New held-out population; provider-controlled model comparison |
| Source-binding/Jev, Nov 8 | 36 new FEVEROUS **all-table** claims; 10 with disputed evidence/labels | 360 GPT-OSS + 36 Jev | Absent original wording: 11/36 vs 19/36 unauthorized with upstream APPROVE/REJECT; 14 observed categorical switches; exact directional p=.0703. Jev no net-repair uplift vs fixed policy | Stable per-case effects, internal mechanism, validated source-present accuracy, useful adaptive selection |
| Liquid d1/RAGTruth, Nov 8 | 120 held-out semantic support items | 4 test arms | Activation steering failed to improve calibrated source-faithfulness task | Direct evidence about FEMI authorization, source-bounded audit fidelity |

## CRITICAL corrections (must address)

**C1 — Omitted negative and positive control:** FEMI-1 is absent from the report and bundled evidence set. Include its actual main null (480/480 with explicit trusted reference verdict; only 20 visible templates) and 3/8 missing-source unauthorized approvals, with 1 invalid. This is the strongest causal-lineage explanation for why FEMI-2 investigated missing records. Add corrected FEMI-1 review and archive to reproducibility package.

**C2 — Model-facing authorization rule is logically incomplete:** prompts use `DEFER only if trusted evidence is missing or invalid`. Formally this states `DEFER => missing`, not `missing => DEFER`. The accompanying 'otherwise REJECT' is also potentially scope-ambiguous. The scoring rubric is unambiguous, but the prompt is not. Rephrase as violating the experiment's *intended* record-presence policy, acknowledge prompt ambiguity as a possible contributor, and do not reinterpret a historical input as if it explicitly said 'If record absent, DEFER'.

**C3 — 'Replicated wording intervention' hides two different treatments:** FEMI-2/2R/4 change an opening *availability assertion* (`record in following SYSTEM message` vs `may or may not appear`). Transfer/cross-model/causal keep that presupposing opening assertion in both arms and vary a later *directive* (`Use the record below` vs `If a record is provided below, use it`). These are related tests of interface sensitivity, not exact replication of one isolated mechanism. Show both exact contrasts.

**C4 — Critical novel prior work omitted:** Yibo Hu, *Silence Is Endorsement: Verification-Status Laundering in LLM Agent Pipelines* (arXiv:2609.20211), directly covers authorization status laundering in full multi-agent handoffs, many models and real pipeline stages. Also directly compare Junchi Liao, *Auditing Provenance Sensitivity in LLM Agent Action Selection* (arXiv:2607.20827). The claim that FEMI first shows verification laundering is indefensible. Distinguish FEMI's deliberately absent trusted record and separately measured claimed-source attribution.

**C5 — Missing genuine swarm-level causal comparison:** ACTION-ID has a staged workflow but no natural promotion or demonstrated amplification. Positive FEMI tests inject constructed user-level handoff text into a single auditor. Do not claim swarm compromise, emergent collusion, or attacker success. Under Apart Track 4 this is a *monitor-component boundary evaluation*, not a swarm-level failure demonstration.

**C6 — Evidence validity and measurement:** Final 36-case FEVEROUS review found 2 clear label/evidence conflicts and 8 unresolved. '26 consistent' is a limited review, not independently established annotation ground truth. The cross-model `cited_evidence` field is a screen rather than an adjudicated invented-citation label; the causal results bundle includes a blank rationale-annotation worksheet. Include a few raw request/response side-by-side examples and distinguish all-sample mechanical detection from one-reviewer textual claims.

**C7 — Not an externally independent or preregistered study:** Frozen request hashes prove internal immutability of supplied bytes, not externally established chronology. The 'independent' audits reparse raw outputs via separate code but are not double-blind outside peer review. Most experiments followed interpretation of previous results; selection and model comparisons are exploratory. Relabel claims appropriately.

## IMPORTANT qualifications

**I1 — Ordinary response variation:** On 288 exactly identical GPT-OSS requests in transfer versus cross-model collections, 49/288 parsed outcomes changed, including invalid. That does not negate population effects, but it challenges interpretation of 14/36 one-draw upstream case switches as stable individual effects. The directional APPROVE contrast's exact p=.0703 should not be overwritten by a percentile bootstrap excluding zero.

**I2 — Effective sample size:** Original FEMI-2, 2R and 4 reuse 12 contexts; ContractNLI absent prompts repeat across 48 contracts; cross-model is 48 previously tested items; Jev tests 36 new cases in a related domain. Never total inference responses and call them independent observations.

**I3 — Stochastic/provider confounding:** Original FEMI-2 used multiple providers while FEMI-2R/4 were Groq; cross-model compares GPT-OSS and Llama on Groq but Gemini on Google AI Studio, with different architectures and serving stacks. Contrast configurations, not intrinsic model alignment properties.

**I4 — Jev objective mismatch:** It forecast **verdict change**, not authorized improvement, and both fixed safe edits reached 36/36 DEFER. There was no observed additional safety headroom for selection. Distinguish a design with no useful action heterogeneity from an intrinsic limitation of learned decision models.

**I5 — Model reasoning vs authorization:** The missing-record test has a deterministic gate with access to metadata. It is a behavioral failure demonstration, not a competitive safety method. Source-present benchmark-label agreement is not independently confirmed source-verification accuracy; final causal case bank has validity issues.

**I6 — Prior work disclosure:** Add FEMI-1 explicitly to November 7 sprint contributions; separate pre-Nov 6 J-SEAR/PO-ID/TPRN and underlying ACTION-ID scaffolding. Archive creation dates and local hashes are incomplete evidence of development chronology; verify actual repo commits if available.

**I7 — Paper basics:** PDF is currently not instantiated from Apart's official template; bibliography omits Hu and shows a truncated Apart hyperlink in render; no public repo URL is in manuscript. Verify render and citations before submission. Apart currently specifies 4–8 body pages, a 150–250 word abstract, required ethical appendix, official template, and clearly labeled prior work.

## Recommendations ranked by urgency

1. Add FEMI-1 main/null and missing-evidence control to narrative, Appendix A and evidence bundle, citing corrected primary audit.
2. Rewrite 'contract' and 'replication' descriptions with exact historical prompt text; do not silently change historical protocol.
3. Incorporate Hu 2026 and Liao 2026 comparisons in Related Work; retract first-discovery/general verification-status-laundering claims.
4. Make findings section center 2–3 fully validated raw excerpts: record absent, user handoff text, exact unauthorized verdict and allegedly authoritative quote; distinguish citation-field nonempty from manually judged fabrication.
5. Downgrade all swarm-specific claims: component-level relevance only, no emergent multi-agent exploitation shown. Include ACTION-ID null.
6. Move d1 (unrelated task) and extended Jev details to optional appendix, preserving negative results without diluting primary claim.
7. Validate template, author affiliation, repo, and links; archive hashes, raw source banks and full reasoning fields with credentials excluded.

## Bottom line

The corrected lineage suggests a more interesting and honest story than the current draft: **when a trusted certificate with an explicit verdict is actually present, conflicting untrusted assessments did not change decisions in a simple pilot; when that record was omitted while its existence was presupposed or left ambiguous, the auditor sometimes produced decisive and source-certified-seeming answers. More explicit interface conditions often suppressed that failure, but effects were model- and prompt-dependent and were not a new swarm-specific exploit.** This is a bounded, reproducible monitor-component evaluation; novelty is incremental relative to provenance auditing and verification-status laundering.

## Sources checked

- `FEMI1_INDEPENDENT_RESULTS_REVIEW_CORRECTED.md`, `CORRECTIONS_LEDGER.md` (user Library)
- `FEMI2_LIVE_RESULTS.zip`, `FEMI2R_LIVE_RESULTS.zip`, `FEMI3A_LIVE_RESULTS.zip`, `FEMI4_LIVE_RESULTS.zip` (attached consolidation artifacts)
- `FEMI_TRANSFER_BOTH_RESULTS.zip`, `FEMI_CROSS_MODEL_V2_RESULTS.zip`, `FEMI_CAUSAL_SOURCE_JEV_RESULTS.zip` (attached original raw outputs)
- independent audit reports for FEMI-4, transfer, cross-model and source-binding
- current `FEMI_Apart_Swarm_Alignment_Report.pdf` / `build/report.md`
- https://apartresearch.com/sprints/swarm-alignment-2026
- https://arxiv.org/abs/2609.20211
- https://arxiv.org/abs/2607.20827
