# D1-SOURCE-FAITHFULNESS-v2 — Independent audit

**Date:** 2026-11-08  
**Evidence:** User-uploaded `D1_SOURCE_FAITHFULNESS_V2_RESULTS.zip`; separate packet `D1_SOURCE_FAITHFULNESS_V2_20261108.zip` for code comparison.  
**Status:** Independent verification of frozen data, result inventory, fit association, scoring, paired effects and steering diagnostics. **No checkpoint inference re-executed.**

## Executive finding

The activation-steered arm did **not** improve response-level source-faithfulness detection on the frozen 120-item RAGTruth heldout set. Its balanced accuracy declined from **74.17% (89/120)** to **70.00% (84/120)**. False acceptance of annotated unsupported responses rose from **45.0% (27/60)** to **56.67% (34/60)**, an increase of **+11.67 percentage points** (independently reproduced task/label-stratified paired percentile bootstrap 95% CI **+5.0 to +20.0 pp**). The model accepted two additional supported responses (56/60 to 58/60) but accepted seven additional unsupported responses. The net correct-response count decreased by five.

The direction primarily shifted support probability upward for every heldout example rather than improving discrimination: mean shift +0.03945; all **120/120** changes positive. ROC-AUC was **0.81972** unsteered versus **0.82028** activated. An affine map from baseline to steered logits fit with R² **0.99958**; this is a post-hoc descriptive fit on test data, not a learned deployable calibration model, and does not establish an internal mechanism.

## Frozen result metrics

| Condition | Correct /120 | Balanced accuracy | Unsupported false acceptance /60 | Supported acceptance /60 | Brier score |
|---|---:|---:|---:|---:|---:|
| Unsteered | 89 | 74.17% | 27 (45.0%) | 56 (93.33%) | 0.18920 |
| Instruction-steered | 89 | 74.17% | 28 (46.67%) | 57 (95.0%) | 0.18960 |
| Activation-steered | 84 | 70.0% | 34 (56.67%) | 58 (96.67%) | 0.20251 |
| Random-sham | 88 | 73.33% | 28 (46.67%) | 56 (93.33%) | 0.18996 |

### Paired uncertainty (our independent 10,000-bootstrap resampling)

- Activation minus unsteered: balanced accuracy −4.17 pp, 95% CI approximately [−9.17, 0.00] pp; false acceptance +11.67 pp, 95% CI [+5.00, +20.00] pp; Brier +0.01331, 95% CI [+0.01044, +0.01608].
- Activation minus random-sham: balanced accuracy −3.33 pp, CI [−7.50, +0.83] pp; false acceptance +10.00 pp, CI [+3.33, +18.33] pp; Brier +0.01255, CI [+0.00980, +0.01522].
- Instruction minus unsteered: balanced accuracy 0.00 pp, CI [−4.17, +4.17] pp; no observed primary-task gain.

Uncertainty resamples unique test `source_id` strata by task and gold annotation, conditional on balanced sampling. It is not a population prevalence or model-generalization estimate. The supplied independent seed 1471 bootstrap results agree closely.

## Domain-specific false acceptance

| Domain | Unsteered | Activation-steered |
|---|---:|---:|
| QA | 10/20 = 50% | 13/20 = 65% |
| Summary | 14/20 = 70% | 16/20 = 80% |
| Data2txt | 3/20 = 15% | 5/20 = 25% |

The worsening appears in every evaluated task, although each domain has only 20 negative cases.

## Development selection and intervention validity

Frozen residual module was `model.language_model.layers.22`; the hook probe reports a single `[1,1,2048]` activation per call, 30/30 structurally compatible candidate transformer blocks, and a requested model SHA `051bcc464b01b9f92942b364d9586b0ef5912432`. **Resolved model commit is null** in the saved metadata; only the requested revision, type and code path are recorded. The saved fit direction and sham vectors both have L2 norm approximately **0.96721**, train-pair coherence **0.59004**, and selected steering dose **0.25**. Fitted `.pt` SHA-256 exactly matches all 480 heldout rows' `fit_sha256` value.

The developer-selected dose was the best **nonzero** dev dose, as required by the frozen design, despite being worse than dose 0: dev balanced accuracy 75.0% unsteered versus 73.33% at selected 0.25, falling to 50% at dose 2; unsupported false acceptance rose from 43.33% at dose 0 to 100% at dose 2. The experiment did **not** adapt the heldout test to this warning. This development pattern cautions against framing the heldout decline as surprising.

## Source-withholding diagnostic

For the same 60 originally supported heldout items, removing trusted source content and substituting `[NO TRUSTED SOURCE PROVIDED]` decreased p(supported) in **59/60** examples under each arm. Mean changes were −0.58759 (unsteered) versus −0.58402 (activation-steered); the model nevertheless accepted 2/60 withheld cases unsteered and 4/60 steered. Because the intervention includes an explicit absence marker and these newly modified items lack human labels, the diagnostic establishes sensitivity to this input manipulation, **not** semantic attribution accuracy or an improved authorization gate. No meaningful source sensitivity gain from steering was observed.

## Data and scoring integrity

- 228 frozen input records: train 48 (24 paired sources), dev 60 distinct sources, heldout 120 distinct sources. No `source_id` overlap across train/dev/test. Heldout balanced across QA, Summary, Data2txt with 20 annotated-supported and 20 annotated-unsupported responses per task.
- Frozen data SHA-256 `8203c399047d182e70318470fd9321299de7514b71a7586ebce51a4fa558e932` matches the included JSONL bytes. All 480 predicted `(response_id, arm)` keys are unique and complete; label, task, source ID, data hash and fit hash correspond to frozen rows. All probabilities finite and in [0,1].
- The uploaded `PROTOCOL.md`, `README.md`, `src/prepare.py`, `src/d1_experiment.py`, and `requirements.txt` are byte-identical to the pre-execution experiment packet.
- Metrics and per-task scores, source-withholding summary, and paired change counts were independently recomputed from raw probability records. Supplied bootstrap intervals agree closely with an independent implementation.
- Train/dev/test `source_id` disjointness is established within this archive, but original downloaded RAGTruth `dataset/source_info.jsonl` and `dataset/response.jsonl` are *not included*. Their recorded hashes cannot be independently reconstructed from the ZIP; dataset-to-benchmark faithfulness beyond the frozen material was not reverified.
- The archive includes probabilities, fit tensors and hook-probe metadata, **not full raw model `system_one` return objects or a local execution trace**. Thus we verified the saved records and code semantics, but cannot independently establish actual hidden-state execution or whether the requested HF revision exactly matches the resolved model commit without rerunning the model.

## Interpretation and decision

This experiment supports a **negative, bounded causal intervention result for one frozen RAGTruth source-faithfulness task and one d1 checkpoint configuration**. A matched intervention was applied in the recorded workflow and behavior changed in a direction that raised YES probability across every heldout example without measurably improving ROC-AUC. This is consistent with a largely global output-propensity/calibration-like effect; it does **not** prove that a particular internal circuit or representation was modified.

Do not present it as a FEMI authorization experiment. RAGTruth span absence is not a complete formal proof of textual support; the heldout set was deliberately balanced and not prevalence-representative. The results do not justify deployment of the activation-steered model as an evidence checker, additional dose optimization on these tested examples, or expanding this same task into more expensive steering searches without a new pre-registered hypothesis. Consolidate this as an informative negative result and, if pursuing d1 again, specify an independent semantic attribution benchmark with adjudicated source-support labels and a non-learned verification baseline.

## Files

- `independent_metrics.json` — exact independent scoring results and paired transition summary.
- `independent_bootstrap.json` — 10,000 paired, stratified bootstrap results.
- `paired_predictions.csv` — source IDs, gold labels, four probabilities and matched correctness outcomes for all 120 heldout items.
- `audit.py`, `diagnostics.py`, `paired_intervals.py` — reproducible review scripts (expect unzipped original results under `source/`).
