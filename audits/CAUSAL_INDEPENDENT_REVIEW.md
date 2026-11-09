# FEMI-SOURCE-BINDING-JEV-1 — Independent audit

**Date:** 2026-11-08  
**Input:** `FEMI_CAUSAL_SOURCE_JEV_RESULTS.zip`, SHA-256 `56e2d36c54bce3f8e1ce635e9663e783c0bb14eb424fb23f6f80dc7ef24a1d93`  
**Scope:** Offline audit of a completed locally frozen 36-case, 360-auditor-request and 36-Jev-request experiment. No new API calls.

## Executive assessment

1. Input-level interventions affected the recorded auditor verdicts. Under **no trusted evidence** and **presupposed record wording**, changing only the untrusted upstream verdict between APPROVE and REJECT changed the final verdict on **14 of 36** cases. The prespecified effect on the probability of APPROVE (upstream APPROVE minus REJECT) was **−6/36 = −16.7 percentage points**, with the supplied paired case-bootstrap 95% interval approximately **[−30.6, −2.8] pp**. This direction is counterintuitive: untrusted REJECT messages caused *more*, not fewer, APPROVE outputs. A two-sided exact paired test on APPROVE versus non-APPROVE discordances gives **p=0.0703** (7 versus 1 discordant cases). The percentile bootstrap and exact small-sample test disagree at the conventional 5% threshold; **do not claim a precise directional effect as settled**. The 14/36 verdict-change observation is descriptive, and only one stochastic response was collected per cell.
2. Compared with the absent-record condition, the corresponding present-record/presupposed comparison changed verdicts in **3/36** cases, with **0 percentage point** APPROVE-probability contrast. This is a behavioral source-availability interaction; the present-record source packet is longer and semantically informative, so it does not isolate internal recognition of a trustworthy source.
3. The **wording manipulation** produced a much clearer change in absent-evidence authorization: with an upstream APPROVE assertion, **11/36** unsupported decisive outputs under presupposed wording versus **0/36** under conditional wording; with upstream REJECT, **19/36** versus **1/36**, respectively. Paired exact two-sided tests give **p=0.00098** and **p=0.0000076** for the two contrasts; these are additional diagnostics, not replacements for the prespecified primary contrast.
4. The explicit absence-reminder condition returned **36/36 DEFER**. This suggests a useful input-level safeguard within this tested interface, not a general safety guarantee. Across all absent-record cells, there were **43 unsupported decisive decisions**. All 43 had nonempty `cited_evidence` and their rationales used language attributing support to trusted or official evidence absent from the actual request. Their factual claims are not independently validated by those citations.
5. **Jev did not provide intervention-selection uplift.** Its 36 top choices were 21 × `explicit_absence_reminder` and 15 × `conditional_wording`; both edits yielded DEFER in all 36 cases. Jev changed **11/36** baseline verdicts (all repairs, no harms)—*exactly the same outcomes* as either fixed rule. Its change-rate uplift versus always-conditional was **0/36**, and it did not select the interventions with the most actual verdict changes (neutral: 17/36; flip: 14/36). The target is actual verdict change, which is not identical to beneficial correction.

## Integrity and provenance

- Independently verified SHA-256 of all three frozen source files (`cases_PRIVATE.jsonl`, `manifest.jsonl`, `selector_manifest.jsonl`) against `FREEZE.json`.
- Independently confirmed 36 distinct case IDs, source IDs and claim texts, 360 unique auditor trials with matching model-specific payload SHA-256 hashes, and 36 unique Jev selector trials.
- Reparsed all 360 raw chat completions; each was a valid JSON object with one of the three allowed verdicts. All reported auditor providers were Groq and all auditor served-model identifiers were `openai/gpt-oss-120b`; the backend supplied 20 distinct `system_fingerprint` values.
- Recomputed all 36 raw Jev answer vectors, which match the saved decision scores. All reported Jev providers were TypeSafe; the response model identifiers use a dated `typesafe/jev-1.14-20261014` revision.
- Total API-reported cost: **$0.120027342**, comprising **$0.1182276** for GPT-OSS and **$0.001799742** for Jev.
- The attached amendment `PROTOCOL_AMENDMENT_A_PREEXEC.md` discloses a review of the supplied evidence packets: 26 consistent, 8 needing review, and 2 in direct conflict with assigned FEVEROUS labels. This audit does **not** rely on those gold labels for absent-source authorization or paired intervention outcomes.
- The runner records a post-Jev/pre-auditor configuration-compatibility patch. The frozen manifest and selector hashes match the original freeze; the patch is disclosed rather than hidden. The archive cannot independently prove call-order chronology beyond the saved records and runtime log.

## Raw verdict counts by condition

| Trusted evidence | Wording | Upstream handoff | APPROVE | REJECT | DEFER | Unauthorized decisions |
|---|---|---|---:|---:|---:|---:|
| Absent | Conditional | APPROVE | 0 | 0 | 36 | 0 |
| Absent | Conditional | REJECT | 1 | 0 | 35 | 1 |
| Absent | Presupposed | APPROVE | 4 | 7 | 25 | 11 |
| Absent | Presupposed | REJECT | 10 | 9 | 17 | 19 |
| Absent | Presupposed | Neutral | 9 | 3 | 24 | 12 |
| Absent | Presupposed | Missing-source reminder | 0 | 0 | 36 | 0 |
| Present | Conditional | APPROVE | 11 | 14 | 11 | Not applicable |
| Present | Conditional | REJECT | 10 | 16 | 10 | Not applicable |
| Present | Presupposed | APPROVE | 10 | 13 | 13 | Not applicable |
| Present | Presupposed | REJECT | 10 | 14 | 12 | Not applicable |

The *source-present* rows are behavioral outcomes, not claims of correct evidence interpretation. Their benchmark reference labels are disputed in 10 of 36 supplied evidence packets.

## Jev decision-selection performance

The selection scenario compares the baseline `absent / presupposed / upstream APPROVE` response with four possible modifications on the same case. Jev is asked to forecast **whether the final verdict will change**, not whether a change would be safe.

| Policy | Changed verdict | Repaired an unauthorized verdict | Introduced an unauthorized verdict | Net repairs minus harms |
|---|---:|---:|---:|---:|
| Always conditional wording | 11/36 | 11/36 | 0/36 | +11/36 |
| Always missing-record reminder | 11/36 | 11/36 | 0/36 | +11/36 |
| Always flip upstream verdict | 14/36 | 3/36 | 11/36 | −8/36 |
| Always neutral handoff | 17/36 | 8/36 | 9/36 | −1/36 |
| Jev-selected (21 reminder, 15 conditional) | 11/36 | 11/36 | 0/36 | +11/36 |

Jev's mean forecast probability of a verdict change was approximately 0.152 for flip, 0.199 for conditional, 0.139 for neutral, and 0.216 for reminder; the observed change frequencies were 0.389, 0.306, 0.472, and 0.306. This comparison is descriptive, but shows that the forecaster's ranking did not identify the highest-change intervention. A uniform random selection across the four candidates would have expected change/repair/harm rates approximately 36.8%/22.9%/13.9% based on the complete counterfactual grid (not an actual new run).

## Interpretation and limitations

- **Behavioral causality, not internal neural mechanism:** input manipulations allow causal contrasts in the observed response distributions under the model and prompting environment, but do not identify an internal source-binding representation or circuit.
- **The upstream flip is not simple copying:** when the upstream message switches from APPROVE to REJECT, the model sometimes produces *more* approvals. This may reflect nonlinear prompt interactions, stochastic sampling, source-confusion, or other effects. One response per condition cannot distinguish stable case-level effects from stochastic variability.
- **Source-present behavior is not independently verified source use:** FEVEROUS evidence is oracle-selected and 10 evidence packets have known validity concerns. Changing the availability of the packet also changes available factual content and prompt length.
- **Explanation support must be assessed separately from verdicts:** 43 unauthorized decisions had apparent trusted-source attributions and nonempty citation lists, but those lists were not genuine independently authenticated references. Source claims vary between otherwise matched responses.
- **Jev did not add measurable selection value:** this does not establish that all decision models are ineffective for causal experiment selection; only this interface, four candidate edits, and 36 cases were tested.
- **No d1 arm executed.** The planned optional local comparator is absent from the result archive.
- **Serving and registration caveats:** one temperature-0.2 response per cell, multiple system fingerprints, locally frozen (not externally preregistered) protocol and the disclosed actor-configuration patch.

## Recommendation

Archive this as a **positive behavioral-intervention result with a negative Jev-utility finding**. Include it in the consolidated FEMI research report; do not claim novel mechanistic causality or reliable source-present semantic accuracy. If a new intervention experiment is conducted, prioritize independently adjudicated new cases and repeated stochastic draws on matched inputs over more optimization of the same Jev selector. A deterministic evidence-availability check remains a much stronger authorization baseline.

## Reproducibility

Unzip the original results archive so that `source_causal/` is in the working directory, then run:

```bash
python recompute.py source_causal
```

The script validates the frozen file hashes, the response payload hashes, the model/provider identities and raw verdict counts, then creates recalculated CSV/JSON outputs alongside the input folder. It requires Python 3 and SciPy for the exact paired tests.
