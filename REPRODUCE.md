# Reproduction guide

## Offline review (no API calls)

1. Read `paper/FEMI_Final_Incident_Context.pdf` and `results/RESULTS_LEDGER.csv`.
2. Check independently recomputed score tables in `results/` and review notes in `audits/`.
3. Run `python tools/verify_release.py`. This verifies the presence and row counts of released score tables and key evidence counts; it does **not** reproduce proprietary model outputs.
4. To run historical unit tests, consult the per-experiment README and install its dependencies. Some tests may require frozen input materials excluded from this public release.

## Cost-bearing re-execution

The `code/` folders preserve original scripts and sanitized Colab notebooks. Check historical protocols and environment constraints. Obtain the benchmark data from their official sources, regenerate inputs using each packet's builder where supported, supply provider keys via environment variables and explicitly opt into live execution. Never commit a local `.env` file.

## Raw evidence

`provenance/ORIGINAL_ARCHIVE_SHA256.json` records checksums for the original raw results. Full unredacted archives were kept in a separate private bundle and **are not part of the public GitHub repository** because some contain source excerpts, private-case files, blind mappings, or unreviewed provider responses. The public release includes structured trial scores and independently recomputed aggregates. This is an auditability limitation, not a claim of complete raw-level public reproducibility.

## Note on naming

Original experiment directory names and notebooks remain largely unchanged so that source checksums/lineage can be reconstructed; imports may rely on the original working directories.

See `TESTING.md` for observed test outcomes and the reason cross-model historical fixtures are absent.
