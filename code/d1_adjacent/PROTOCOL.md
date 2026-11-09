# D1-SOURCE-FAITHFULNESS-v2 — Locally frozen study protocol

Date: 2026-11-08. Prepared for a new run on LiquidAI/d1-3B. **Not run on the real d1 checkpoint yet.** The six offline tests exercise synthetic inputs only. Not externally preregistered.

## Claim under test

Does a training-only contrastive activation direction improve *response-level detection of unsupported claims against the supplied source* on unseen RAGTruth examples, compared with unsteered, instruction-steered, and same-norm random-sham alternatives? Does the fitted model's support probability depend on actual source availability?

This is **not** a test of whether an auditor may authorize an action when a trusted audit record is missing. Code can enforce that authorization boundary. This experiment addresses the more difficult semantic claim-to-source relation.

## Dataset and gold

Official **ParticleMedia/RAGTruth** `dataset/source_info.jsonl`, `dataset/response.jsonl`; original `train` and `test` partitions. Corpus version and SHA-256s are recorded. `source_info` (string or dictionary) and the candidate generated `response` form the entire **model-visible state**. The model does not receive `labels`, `split`, `quality`, `model`, `task_type`, `source_id`, or source metadata. The corpus's span annotation presence is the binary gold: **supported** = no annotated hallucination/unsupported span; **unsupported** = ≥1 annotated span. A span with `implicit_true` is *correct in the outside world but unsupported in the provided context*, and remains unsupported for our task. We don't equate this label with exhaustive proof of source completeness.

We exclude responses marked `truncated` or `incorrect_refusal`, blank responses, and states longer than 12,000 characters. These filters happen before any model calls. The original RAGTruth test split is reserved for testing. Report how many items were filtered in the freeze metadata.

## Source-disjoint allocation

Seed 1947; deterministic selection, no replacement. Three tasks: QA, Summary, Data2txt.

| Partition | Allocation | Number of response items |
|---|---|---:|
| TRAIN | 8 same-source opposite-label response pairs per task | 48 (24 sources) |
| DEV | 10 distinct-source items per label per task, from official TRAIN | 60 (60 sources) |
| HELD-OUT TEST | 20 distinct-source items per label per task, from official TEST | 120 (120 sources) |

The source identifiers in the train, dev and test partitions must be disjoint. The 24 training pairs deliberately have two responses per source; no other source repeats. If counts are insufficient, the builder stops and does **not** silently change quotas.

## Frozen four-arm comparison

1. **Unsteered d1**: documented `system_one` `noul` probability of entire-response support; base question.
2. **Instruction-steered d1**: same state and base model, expanded verification question emphasizing source support; no activation intervention.
3. **Activation-steered d1**: base question and an additive residual perturbation at a single specified model block.
4. **Random-sham d1**: base question, same block, same dose, same vector norm, random isotropic direction; seed fixed.

No fine-tuning, no parameter updates, no rewrites of gold evidence. Same checkpoint for all four arms. Each held-out item is evaluated in deterministic pseudorandom arm order. The model outputs probability of support, not explanations or evidence citations.

## Activation intervention

Use `AutoModel.from_pretrained('LiquidAI/d1-3B', trust_remote_code=True, revision=PINNED_SHA, dtype=...)`. This model's remote implementation is trusted only by explicit choice; review the card/code. Its public API is `system_one`; residual hooks are **undocumented**.

- GPU **TRAIN-only preflight** finds the largest family of complete transformer block modules, probes which fire **exactly once** with a `[1,sequence,hidden]` output, and selects the viable block nearest 75% of that family's depth. Log name, shape and checkpoint SHA. No test or dev labels are used to choose the layer. A manual hook override is possible *before fit* if architecture discovery fails; that deviation must be reported.
- TRAIN: for each of 24 same-source pairs, calculate `h_supported - h_unsupported` at the selected block last token. Mean the pairs, normalize and scale to median pair difference norm. Log mean norm and pair-direction coherence. A near-zero direction stops.
- DEV: test fixed nonzero doses **0.25, 0.5, 1, 2** plus an unsteered reference. Select the nonzero dose with maximum balanced accuracy among doses whose **supported acceptance rate falls by no more than 10 percentage points** from unsteered dev. Break ties by Brier, then smaller dose. If none pass the guardrail, use the predetermined fallback **0.5** and record this failure. **Never choose dose 0 and call it steering.**
- TRAIN sanity check: patched module must fire exactly once and at least one of six train-item probabilities must shift measurably (>1e-7), or fail closed. This checks whether the hook affects output, not whether it is beneficial.
- HELD-OUT TEST: no changes to prompts, hook, vector, dose, threshold, or splits. Test labels are not used for parameter selection. Heldout run is resumable by validated frozen IDs and does not silently overwrite a completed evaluation.

All directions, doses, model commits and seeds must be reported. A small output-probability movement could just be calibration, not improved reasoning; that distinction matters especially after the earlier unsuccessful J-SEAR d1 steering attempts.

## Endpoints and negative controls

**Primary:** paired change in 0.5-threshold **balanced accuracy** of activation-steered vs unsteered, with a prespecified supported-acceptance guardrail of no worse than −5 percentage points on test. Demand improvement relative to random-sham too. This success gate is exploratory; report confidence intervals rather than just a pass/fail threshold.

**Secondary:** unsupported *false acceptance rate*, supported *true acceptance rate*, overall accuracy, Brier score, full QA/Summary/Data2txt stratification, and median local inference time by arm. Always-NO yields balanced accuracy 0.5 and is the trivial comparator. No threshold search on test.

**Uncertainty:** matched, label- and task-stratified bootstrap of test source IDs (3,000 resamples), fixed seed 1471. This resampling conditions on the deliberately balanced test set; it is *not* a population-prevalence estimate. Report all arms and uncertainty, including failed intervention.

**Post-test diagnostic (separate, not used for selection):** remove the supplied source for each of the 60 originally supported held-out items while preserving the generated response. Evaluate unsteered and activation-steered d1. Report probability drop and fraction showing a decrease; do **not** treat these altered items as newly human-annotated hallucinations or as a validated safety authorization benchmark.

## Abort conditions

- Train/dev/test source ID overlap or inconsistent source labels; malformed dataset.
- Cannot run official d1-3B `system_one` on GPU; incompatible Transformers/remote code.
- No complete-block module fires exactly once with safe tensor shape, or patched output is inert on training items.
- Checkpoint SHA changes between probe, fit and heldout.
- Incomplete, duplicated, mismatched or out-of-range heldout predictions.

If any of these occur, **do not invent heldout results or substitute simulated steering outputs**. A baseline-only study requires a new versioned protocol and should not be presented as the four-arm study.

## Interpretation limits

RAGTruth is a public historical corpus and its annotations can be incomplete, contested, or heterogeneous. This does not establish independent real-world source certification, provenance enforcement, or downstream action safety. The intervention uses one model-specific residual hook, not a discovered causal circuit. Success would be a bounded intervention effect on this RAGTruth task and checkpoint, not a proof that d1 can audit FEMI incidents. Record code/dependency versions, exact selected model commit, dataset commit, filters and all negative results.
