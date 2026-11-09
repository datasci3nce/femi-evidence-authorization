# D1-SOURCE-FAITHFULNESS-v2

**Runnable local Colab GPU experiment: unsteered vs instruction-steered vs activation-steered vs random-sham LiquidAI/d1-3B.** This is an independent semantic source-checking study associated with FEMI, not a gate for missing-record authorization.

## Quick start

Open `notebooks/Colab_D1_Source_Faithfulness_V2.ipynb` in a **GPU** Colab runtime. Upload the entire `D1_SOURCE_FAITHFULNESS_V2_20261108.zip` to its first cell. The notebook:

1. Runs six offline software tests (synthetic data only).
2. Clones the official RAGTruth repository if not already present and records its git commit; this downloads only public data.
3. Freezes a source-disjoint, three-task balanced data bank: 48 TRAIN response items / 60 DEV / 120 TEST.
4. Installs the publisher-documented `transformers>=5.14`, resolves and pins the exact Hugging Face d1 model revision, then loads the 3.12B model on GPU.
5. Probes a compatible complete transformer block on TRAIN only; fail closed if model internals do not support hooks.
6. Learns one mean contrastive direction from 24 TRAIN pairs and selects dose on DEV; stores vectors and metadata.
7. Runs the fixed four-arm **480-decision** TEST, with resumable private checkpoint and independent analysis.
8. Optionally runs the post-test source-removal diagnostic (60 supported rows × 2 arms = 120 more local decisions).
9. Exports a ZIP containing the frozen inputs, model revision, vectors, raw per-arm probabilities and audit report. No API key or model weight files are included.

**The supplied packet has not run d1 inference.** Tests cover synthetic dataset/score/hook conditions; the model-specific hook behavior must pass on your Colab GPU. If it fails, report the raw error and do not reselect a layer or dose after seeing test outcomes.

## Command line alternative (inside packet root)

```bash
python -m unittest discover -s tests -v
# Clone https://github.com/ParticleMedia/RAGTruth in your environment.
python src/prepare.py --source-file /content/RAGTruth/dataset/source_info.jsonl --response-file /content/RAGTruth/dataset/response.jsonl --out runs/d1
python src/d1_experiment.py preflight --dir runs/d1
# Set D1_HF_REVISION to exact model commit hash BEFORE GPU inference.
python src/d1_experiment.py probe --dir runs/d1
python src/d1_experiment.py fit --dir runs/d1
python src/d1_experiment.py test --dir runs/d1
python src/d1_experiment.py analyze --dir runs/d1
python src/d1_experiment.py ablate --dir runs/d1  # optional post-test
```

## Cautions

- `trust_remote_code=True` runs external publisher code; inspect what you execute and check the publisher's license.
- The dataset's gold is **annotation-based response faithfulness**, not code-checkable evidence authorization. Absence of an annotated span is not a proof of factual support.
- The source-removal diagnostic is not a replacement for the main heldout dataset.
- Preserve a frozen run: the builder intentionally refuses to overwrite `runs/d1`.
- Intended heldout four-arm `system_one` calls are **local** (no OpenRouter/Groq charges), but require enough GPU memory for d1-3B.
- If a notebook run crashes during heldout, rerun only the heldout cell; its `d1_heldout_PARTIAL.jsonl` checkpoint validates completed IDs.
