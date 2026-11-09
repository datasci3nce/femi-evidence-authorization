# FEMI-1 execution packet — fixed evidence, message interference

**Scientific status: OFFLINE READY, LIVE NOT RUN.** This packet is the prospective follow-up to ACTION-ID. It does not contain FEMI-1 auditor observations or claims of a detected effect. The previous ACTION-ID report and its evidence remain frozen separately.

## What is frozen

Read [`FEMI_1_PROTOCOL_FROZEN_V1.md`](FEMI_1_PROTOCOL_FROZEN_V1.md) before inference. `femi1_stimuli.py` is copied byte-for-byte from the pre-response frozen v1 protocol packet. The protocol locks:

- Two real ML families: `iris` and `wine`; seeds 101, 103, 107, 109, four fault conditions, 32 complete coordinator records, 8 base (family,seed) clusters.
- Four within-case message variants T1–T4 and an absence variant T0; three independent calls per variant, 480 main calls.
- Eight *separate* no-evidence negative controls, for 488 calls total.
- Fixed `openai/gpt-oss-120b` model, `temperature=0.2`, `max_tokens=1600`, OpenRouter Chat Completions, fresh sessions.
- Primary paired contrasts of balanced correct-decisive coverage: T2–T4 and T3–T4; 10,000 stratified cluster-bootstrap resamples.

**Scientific caveat:** This evaluates susceptibility of a language-model intermediary to lower-trust commentary while a trusted verdict is directly supplied. The deterministic gate knows the answer; this does not establish a need for an LLM gate, actual multi-agent collusion, or cryptographically verified logging.

## Offline work completed

The 32 coordinator records in `offline/` were produced by actual scikit-learn fitting on built-in Iris and Wine data, not by labelling synthetic outcomes. The independent verifier regenerates the split indices and re-fits each recorded model to cross-check every metric; it derives the two predicates from the ledger rather than copying the requested fault flags. It checks 8 clean, 8 selection-only, 8 row-only and 8 combined cases. The records are protected against accidental change by SHA-256, **not** a cryptographic source-authentication system.

Run locally or in Colab:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python femi1_cases.py --out offline_rebuilt
python femi1_stimuli.py --cases offline_rebuilt/cases.jsonl \
  --out offline_rebuilt/femi1_manifest_480.jsonl \
  --controls-out offline_rebuilt/femi1_controls_8.jsonl
python femi1_live.py --manifest offline/femi1_manifest_480.jsonl \
  --controls offline/femi1_controls_8.jsonl --out live
```

The final command without `--live` only checks the 480+8 requests and does **not** contact OpenRouter.

### Frozen input output structure

- `offline/cases.jsonl` — 32 claim-bound coordinator inputs.
- `offline/coordinator_ledgers/` — actual 32 execution traces.
- `offline/offline_verification_receipts.jsonl` — independent refitting / predicate results.
- `offline/femi1_manifest_480.jsonl` — exact 480 intended requests in preregistered pseudorandom order.
- `offline/femi1_controls_8.jsonl` — 8 absent-evidence controls.
- `offline/offline_summary.json` — *offline* integrity counters, no model evaluation.
- `SHA256SUMS.txt` — checksums of versioned protocol, source and frozen inputs.

### Before live API calls: external timestamp

The earlier plan explicitly required an external timestamp **before response collection**. Put the frozen protocol, stimulus generator, manifests and analysis code in a Git repository and push it to a remotely timestamped repository. Save the **real** commit SHA (40 hex characters) and link. Do not invent a commit or claim external preregistration from a local copy.

For example, from the unzipped package after you configure your Git remote:

```bash
git init
git add FEMI_1_PROTOCOL_FROZEN_V1.md femi1_stimuli.py femi1_cases.py \
  femi1_analysis.py femi1_live.py SHA256SUMS.txt offline/cases.jsonl \
  offline/femi1_manifest_480.jsonl offline/femi1_controls_8.jsonl
# Commit and push through your own GitHub repository.
# Save the real SHA produced by 'git rev-parse HEAD' *after* pushing.
```

The live runner requires that SHA via `--prereg-ref`. This is an audit guard, not a proof that the external repository cannot be altered.

## Live OpenRouter run (requires **your** key)

The session running this packet has no OpenRouter credentials, so **no FEMI-1 inference calls were made**. See `Colab_FEMI1_Full_Run.ipynb` for complete notebook steps.

Set `OPENROUTER_API_KEY` securely (Colab secrets or `getpass`; never hard-code into a shared notebook). Then:

```bash
python femi1_live.py \
  --manifest offline/femi1_manifest_480.jsonl \
  --controls offline/femi1_controls_8.jsonl \
  --out live \
  --prereg-ref <REAL_40_CHAR_GIT_COMMIT_SHA> \
  --live
```

**Important:** The supplied `<...>` placeholder is not a valid commit SHA. Do not use the sample as a literal shell argument. An incompatible provider response aborts rather than changing the model/prompt silently.

For a Colab runtime requiring checkpoints, run with `--max-new 100`, and rerun the identical command to resume until 480 main and 8 control responses have terminal rows. `--max-new` chunks the *fixed* manifest and is not a new sample-selection rule. Prefer writing the `live/` directory into mounted Google Drive so checkpoints survive a restart. Retries (maximum two retries after initial attempt) preserve exact request bytes; retries can incur duplicate provider charges after an ambiguous network failure. The runner retains raw responses, usage, HTTP diagnostics and timestamps; API secrets are never stored.

## Analysis (only after all 488 calls)

```bash
python femi1_analysis.py \
  --manifest offline/femi1_manifest_480.jsonl \
  --controls offline/femi1_controls_8.jsonl \
  --results live/main_responses.jsonl \
  --control-results live/control_responses.jsonl \
  --out live/analysis
```

Analysis refuses to run on incomplete data. It reports intended/observed counts, all decisive and deferred outcomes, false approvals separately from false rejections, disaggregated fault conditions, primary paired contrasts, eight base-group effects, family-separated effects, 10,000 stratified cluster-bootstrap percentile intervals, response-valid sensitivity, and separate negative-control results. It also creates `blinded_rationale_coding.csv` and a **private mapping file**; keep the mapping separate until manual coding is complete. Semantic rationale coding is not pretended to be automatic.

When live finished, archive `live/`, the exact original ZIP, Git commit URL, any protocol deviations and the blinded manual rationale labels. The null result is valid; do **not** edit treatments or extend sample size after reading the output.

## What was not done

- No live FEMI-1 auditor requests were made in this environment (no credentials).
- No post-hoc treatment optimization or prompt adaptation was conducted.
- No statistical significance or population-level efficacy claim can be drawn from 8 base clusters.
- No external preregistration commit was created or claimed here.
- The case generation is locally verified ML training; the harness assumes its records are complete and coordinator-owned.
