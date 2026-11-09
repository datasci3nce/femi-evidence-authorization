# FEMI-CROSS-MODEL-1 v2 — executable, frozen cross-model replication

**Status:** The 48-case bank and its 288 base prompts are **frozen and verified offline**. **No OpenRouter model calls have been made for this cross-model run.** The full suite requires 864 model responses. The model-specific live calls are user-triggered and cost money.

## Get started in Colab

1. Open `notebooks/Colab_FEMI_Cross_Model_V2.ipynb`.
2. Upload `FEMI_CROSS_MODEL_V2_20261108.zip` in the first notebook code cell. It contains its own frozen subset and source archive: no dataset download, no FEVEROUS shard parsing, no builder execution necessary.
3. Run **OFFLINE** tests and preflight. Expected: 9 tests pass, 288 base prompts verified, dry-run reports 864 total model requests and 0 completed.
4. Configure `OPENROUTER_API_KEY` in Colab **Secrets**, and allow notebook access. The key is never part of the ZIP or logged in responses.
5. Execute the explicitly marked **PAID** 24-call transport/parser checkpoint. The three models are interleaved. Count only schema-valid outputs as decisional outputs; if a provider is unavailable, STOP and preserve the checkpoint.
6. Without changing the frozen manifest or model JSON, execute remaining calls in resumable 72-call chunks. Back up the results JSONL to Google Drive if possible.
7. Run analysis and export `FEMI_CROSS_MODEL_V2_RESULTS.zip`. Upload that output for independent review. Do not analyze incomplete runs as complete.

## Exactly what is frozen

| Dimension | Setting |
|---|---|
| Datasets | Existing ContractNLI and FEVEROUS case banks from `FEMI_TRANSFER_BOTH_RESULTS.zip` |
| Cases | 15 ContractNLI **distinct hypotheses** + 33 FEVEROUS **distinct claims** |
| Reference-label balance | In each dataset: 5/5/5 CNLI; 11/11/11 FEVEROUS approve/reject/defer |
| FEVEROUS modalities | 21 table / 12 mixed text+table |
| Evidence regime | absent / substitution / present |
| Availability wording | conditional / presupposed |
| Model families | GPT-OSS-120B (Groq), Llama 3.3 70B (Groq), Gemini 3 Flash Preview (Google AI Studio) |
| Calls | 48 × 3 × 2 × 3 = **864** |
| Inference settings | temperature 0.2, `max_tokens` 1600, standard chat completions; no new response-format or reasoning controls |
| Sampling and order | Seed 81324 for case selection; request order frozen; models interleaved within each base request |
| Main outcome | Unauthorized APPROVE / REJECT when no coordinator-origin trusted evidence was provided |
| Primary comparison | For each model, **presupposed − conditional** error rate in **absent** regime, analyzed using paired cases |
| Primary cross-model question | Do model-specific presupposed-minus-conditional differences diverge from contemporaneous GPT-OSS anchor on the same inputs? |

The three models use the **same `messages` list for each matched trial**; only the API `model`, `provider` and response metadata change. The two wording arms differ only in the one frozen system sentence inherited from earlier transfer studies. A contemporaneous anchor rerun is part of the 864 planned calls. Provider routing is pinned with `allow_fallbacks=false` where supported, but server-side implementation and reasoning defaults are not guaranteed identical across families.

## Offline CLI

Run from extracted root:

```bash
python -m unittest discover -s tests -v
python src/run_and_score.py preflight --dir runs/cross_model
python src/run_and_score.py run --dir runs/cross_model --models models.cross.v2.json
```

The third command is **dry-run only**. It cannot contact the API without explicit `--execute`.

## PAID CLI, resumable

Set `OPENROUTER_API_KEY` securely (Colab Secrets is preferable). For an initial 24-call provider/schema gate:

```bash
python src/run_and_score.py run --dir runs/cross_model --models models.cross.v2.json --execute --max-new 24 --pace 0.85
```

If the gate is satisfactory, keep the same files/settings and execute additional batches:

```bash
python src/run_and_score.py run --dir runs/cross_model --models models.cross.v2.json --execute --max-new 72 --pace 0.85
```

Repeat the last command until dry-run says 0 remaining. `results/responses.jsonl` is append-only; existing trial IDs and **full payload hashes** are checked before resuming. `MODEL_FREEZE.json` blocks drift in model ID, provider constraint, or inference settings. A failed request stops the process; replaying only uncompleted trial IDs is supported.

## Final analysis (no network)

```bash
python src/run_and_score.py analyze --dir runs/cross_model --models models.cross.v2.json
python src/cross_analysis.py --dir runs/cross_model --models models.cross.v2.json
```

Produces `results/analysis.json`, `results/scored.csv`, `results/evidence_attribution_review_BLANK.csv`, `results/CROSS_MODEL_REPORT.json`, and `results/cross_model_recomputed_rows.csv`. Cross-model report includes model- and domain-specific cell counts, paired case-cluster bootstrap CIs for wording contrasts, and model-versus-anchor differences in those contrasts. Treat these intervals as descriptive for the selected case sample; model-family generalization is broader than three named checkpoints.

## Rebuilding: only on a new directory, never after live calls

The archive includes the original source transfer results in `inputs/FEMI_TRANSFER_BOTH_RESULTS.zip`. A reproducible builder is shipped, but **do not rerun it in `runs/cross_model`**, which is already frozen. To independently reproduce into a separate folder:

```bash
python src/build_cross_v2.py --source-zip inputs/FEMI_TRANSFER_BOTH_RESULTS.zip --out /tmp/cross_verify
sha256sum runs/cross_model/manifest.jsonl /tmp/cross_verify/manifest.jsonl
```

The hashes should match. Source ZIP SHA-256: `eb9e2d99ad0095a867053ae1fd28ac56cb3306ecf22777eb7a6d2264219b53ee`.
Frozen manifest SHA-256: `d47eaa528e1ab08b23ba6c6866e70a5d83e40a931d81f5fd031190eb92f32f64`.

## Interpretation guardrails

- This is **cross-model replication on selected previously studied cases**, not new unseen task-family generalization. Selection uses private ground truth for balancing, not for model prompting.
- The original FEVEROUS present-record inputs use **oracle-selected annotated evidence**, not model-initiated retrieval.
- ContractNLI has just 16 original unique hypothesis templates in the 48-case bank; this design uses 15 different hypotheses, not 15 independent novel proposition families.
- Do not describe all decisive outputs as *wrong reference verdicts*: they are **unauthorized** when trusted evidence is absent, even if they agree with a latent source label.
- The parser scores malformed JSON as `INVALID`, not as an abstention or unauthorized decisive answer. Report schema failures alongside behavioral rates.
- Nonempty `cited_evidence` is a **screening flag**, not sufficient to prove fabricated source attribution. Manual rationale review is required, using the blank review sheet.
- This is not an experiment on swarm amplification or observed real-world harms; no downstream approvals are executed.
- If Gemini's default reasoning consumes an output budget, do not silently increase its token cap midway. Preserve all observations, document the incompatibility and freeze a separately named follow-up if necessary.

OpenRouter model information: https://openrouter.ai/openai/gpt-oss-120b , https://openrouter.ai/meta-llama/llama-3.3-70b-instruct , https://openrouter.ai/google/gemini-3-flash-preview .
