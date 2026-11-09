# FEMI Transfer — Independent Audit of ContractNLI and FEVEROUS

**Date:** 2026-11-08  
**Input:** User-provided `FEMI_TRANSFER_BOTH_RESULTS.zip`  
**Scope:** Frozen case banks, manifests, all 576 raw returned responses, model-freeze metadata, saved analysis, and the matching experiment runner source. No new inference calls. Results shown below are independently recomputed from raw response content and full model-specific request hashes.

## Executive assessment

The prespecified absent-record wording contrast is **positive in both transfer domains** using a Groq-served `openai/gpt-oss-120b` configuration. The finding is substantive but bounded: this is behavioral transfer across two task families using a common auditor interface, not demonstration of an internal presupposition mechanism or model-family generality.

**Important correction to the case-unit claim:** ContractNLI's 48 selected documents contain only **16 unique hypotheses**. When evidence is withheld, those documents produce **16 different literal absent-record prompts per wording**, with some prompts repeated up to seven times. FEVEROUS has 48 distinct claims/absent-record prompts. Consequently, document-level bootstrap on the 48 ContractNLI cases overstates the number of independent *prompt contexts*; proposition-clustered sensitivity estimates are reported below.

## Recomputed condition results

For absent and substitution conditions, **unauthorized decisive** means `APPROVE` or `REJECT` despite no coordinator-origin trusted record. For present conditions, the reported number is **agreement with the supplied reference label**, not source-verification accuracy.

| Dataset | Evidence regime | Conditional wording | Presupposed wording |
|---|---|---:|---:|
| ContractNLI | No trusted evidence: unauthorized decisive | 1/48 (2.1%) | 18/48 (37.5%) |
| ContractNLI | Untrusted upstream substitution: unauthorized decisive | 6/48 (12.5%) | 16/48 (33.3%) |
| ContractNLI | Trusted document present: reference agreement | 38/48 (79.2%) | 37/48 (77.1%) |
| FEVEROUS | No trusted evidence: unauthorized decisive | 6/48 (12.5%) | 17/48 (35.4%); **2 additional invalid formats** |
| FEVEROUS | Untrusted upstream substitution: unauthorized decisive | 3/48 (6.3%) | 20/48 (41.7%) |
| FEVEROUS | Trusted evidence packet present: reference agreement | 34/48 (70.8%) | 34/48 (70.8%) |

### Paired wording effects (presupposed minus conditional)

| Domain/regime | Difference | Paired case-level bootstrap, 95% | Exact paired McNemar p (unadjusted) |
|---|---:|---:|---:|
| ContractNLI / absent (primary) | +35.4 pp | +20.8 to +50.0 pp | 0.0000763 |
| FEVEROUS / absent (primary) | +22.9 pp | +10.4 to +35.4 pp | 0.00342 |
| ContractNLI / substitution (secondary) | +20.8 pp | +4.2 to +37.5 pp | 0.0309 |
| FEVEROUS / substitution (secondary) | +35.4 pp | +18.8 to +52.1 pp | 0.000221 |

For ContractNLI, reclustering by its **16 distinct propositions** instead gives a response-weighted primary bootstrap interval of approximately **+20.4 to +52.6 pp**. Ten distinct propositions have a positive within-proposition average contrast, six have zero contrast, and none have a negative average contrast. The positive primary effect persists but generality is limited to these 16 wording templates.

Exact paired tests summarize the observed matched responses; they do not compensate for incomplete generalization across models, source-selection bias, or multiple exploratory contrasts.

## Response and source-attribution audit

- **576** manifest rows and 576 response records, 288 per domain. Exactly one saved response per model-expanded trial ID. Base manifest IDs differ from response IDs **by design**: the runner derives a model-specific ID as a SHA-256 truncation of `base_trial_id + '|' + model_name`.
- Manifest/case-bank SHA-256 values match both frozen manifests. Every response matches its corresponding **full OpenRouter request payload hash**, including model ID, decoding parameters, messages, and Groq-only routing. Every stored parsed verdict matches reparsing the raw completion (including 2 invalid formats).
- No trusted evidence message appears in absent or substitution conditions; only the present conditions contain a `TRUSTED_EVIDENCE_RECORD:` system message. The two wording arms differ solely in their designated final system sentence for each matched case and evidence regime.
- All 576 responses report provider `Groq`, 40 distinct `system_fingerprint` strings in ContractNLI and 38 in FEVEROUS. These metadata differences do not establish backend weight changes.
- Combined API-reported cost: **$0.1915722**, with ContractNLI $0.0999549 and FEVEROUS $0.0916173.
- **87 unauthorized decisive responses** across absent/substitution conditions: 41 ContractNLI and 46 FEVEROUS. All 87 have nonempty `cited_evidence` and explicitly refer to purported trusted evidence in their rationales despite no trusted source having been supplied. This is an observable false source-attribution behavior. Detailed manual semantic coding/adjudication beyond these explicit patterns remains outstanding.
- Of the 87, **35** happen to agree with the underlying reference verdict; **13** are approvals where the reference verdict is `REJECT`. Agreement with the reference does **not** authorize a decision when the required trusted evidence is missing.
- **Two invalid FEVEROUS outputs**, both `absent/presupposed`: one natural-language message says that no trusted record is available (behavioral abstention but schema failure); one malformed JSON response with inline comments asserts `APPROVE` and cites nonexistent evidence. Under the frozen strict parser, both are INVALID, not unauthorized decisive. A secondary content-level reading would add one attempted unauthorized approval to the FEVEROUS absent-presupposed cell (18/48), without reversing the reported direction. Do not silently recode the frozen primary analysis.

## Dataset construction and inference limits

1. **ContractNLI:** 48 distinct contract IDs and an equal 16/16/16 selection across Entailment/Contradiction/NotMentioned; the underlying propositions are drawn from 16 fixed hypotheses. Present-record inputs contain the full selected contract, whereas absent-record inputs do not, causing duplicated literal prompts. The natural sampling unit for absent-record prompt generality is the hypothesis template; for full-contract NLI it is the contract.
2. **FEVEROUS:** 48 unique claim IDs and 48 different claims, balanced 16/16/16 across SUPPORTS/REFUTES/NOT ENOUGH INFO. Selected evidence packets comprise 31 table-only and 17 mixed text/table cases; the frozen packets reference 56 different Wikipedia page titles without repeated evidence page titles across cases. This is a useful distinct-stimulus replication in the same auditor wrapper. Its present-record evidence is **oracle-selected from gold annotations**, so it does not measure independent retrieval.
3. The archive contains **derived case banks and evidence renderings**, not the original official dataset downloads. Therefore this audit **does not independently validate the legal/Wikipedia annotations or full wiki/contract extraction fidelity** against the original data. Gold-label agreement should be presented as *agreement with supplied dataset labels*.
4. Source availability is explicitly artificial and controlled by a harness; it is not an assessment of real legal authorization or Wikipedia reliability. The common prompt package and a single model/provider configuration remain possible common causes of the observed cross-domain behavior. These are not two independent model replications.
5. Saved response records contain successful API responses but no complete request-attempt/error log, so all previous network retries cannot be independently reconstructed.

## Decisions for the next stage

- **Preserve these completed datasets and manifests; no more anchor calls on the same 48 cases are needed to validate the within-domain primary findings.**
- **Publish a bounded transfer report now**, retaining FEMI-3A's null result and FEMI-4's unsuccessful safeguard intervention in the full experimental lineage.
- Before cross-model scaling, **revise the proposed matched subset selection**. The original cross-model builder samples 24 ContractNLI cases, which can include identical absent-record prompts. Instead select at most one ContractNLI document per unique hypothesis for that model-comparison subset, and obtain the remaining distinct cases from FEVEROUS (or an independently curated third evidence family). If keeping reference-label balance, an assignment of 15 unique ContractNLI hypotheses at five cases per label is feasible for this case bank; 33 FEVEROUS cases at eleven per label would give 48 distinct case prompts in total. Freeze a **new** cross-model manifest rather than modifying any run directory already used for live inference. Contemporaneous anchor rerun is desirable if one wants to compare model configurations with less time confounding.
- Do not mix the Liquid d1 study with these authorization scores. Its proposed RAGTruth steering comparison tests **semantic source faithfulness**, a different property from deterministic trusted-record presence.

## Attached machine-readable products

- `recomputed_audit.json`: full condition counts, independent paired results, duplicate-request counts, costs and metadata.
- `unauthorized_error_inventory.csv`: all 87 unauthorized decisive responses, with source-attribution indicators and actual rationales.
- `invalid_output_inventory.csv`: the two raw malformed FEVEROUS outputs.
- `verify_and_export.py`: reproduces the audit and exports the inventories from the original combined results ZIP.

*Status: independent analysis of the supplied materials; no external preregistration, new model calls, or independent benchmark-source reconstruction.*
