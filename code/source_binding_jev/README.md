# FEMI source-binding causal experiment + Jev selector

**No new API/GPU runs are included.** The packet provides offline-tested code, a frozen experimental design, and a Colab notebook. The public FEVEROUS dump is not included; reuse your already extracted `/content/datasets/feverous/FeverousWikiv1` folder and `feverous_dev_challenges.jsonl`.

## Quick start in Colab

Open `notebooks/Colab_FEMI_Source_Binding_Jev.ipynb` and upload this whole ZIP. Follow the cells in order. **Never rerun the builder after any paid request is collected.** If the dataset builder fails, preserve the error and review the source validity instead of changing the random seed after viewing any outcomes.

## CLI (run from project root)

```bash
python -m unittest discover -s tests -v
python src/build.py --dev /content/datasets/feverous/feverous_dev_challenges.jsonl \
    --wiki /content/datasets/feverous/FeverousWikiv1 --out runs/source_causal \
    --n 36 --seed 81227 --min-table 12
python -c "import sys; sys.path.insert(0,'src'); from core import verify; print('PREPARED:', len(verify('runs/source_causal')[1]), 'frozen requests')"
python src/execute.py jev --dir runs/source_causal          # DRY RUN
python src/execute.py auditor --dir runs/source_causal      # DRY RUN
# PAID; set OPENROUTER_API_KEY via Colab Secrets, not in plaintext:
python src/execute.py jev --dir runs/source_causal --execute --max-new 2
python src/execute.py jev --dir runs/source_causal --execute
python src/execute.py auditor --dir runs/source_causal --execute --max-new 10
python src/execute.py auditor --dir runs/source_causal --execute
python src/analyze.py --dir runs/source_causal
# OPTIONAL, separate GPU runtime / transformers >= 5.14:
python src/run_d1_optional.py --dir runs/source_causal --execute
python src/analyze.py --dir runs/source_causal
```

The runner uses HTTP, requires `--execute` for paid calls, and resumes verified trial IDs from `results/*.jsonl`. Do not copy or publish your API key. The project does not silently install packages or switch providers.

## Primary artifacts

- `runs/source_causal/FREEZE.json`, `manifest.jsonl`, `selector_manifest.jsonl`, `cases_PRIVATE.jsonl`
- `runs/source_causal/results/jev_responses.jsonl` — prospective selector predictions
- `runs/source_causal/results/auditor_responses.jsonl` — all 360 actual counterfactual auditor outputs
- `runs/source_causal/results/INDEPENDENT_RECOMPUTATION.json` — causal comparisons and selector baselines
- `runs/source_causal/results/rationale_annotation_BLANK.csv` — **manual** attribution review, never positive support inferred from citation-list length

The official FEVEROUS dataset itself is **not** bundled in the export, so separately preserve its source split and original Wikipedia snapshot provenance.
