# Verification status (9 November 2026)

- `python tools/verify_release.py` — **PASSED** for nine released scoring tables with 480 + 144 + 144 + 288 + 576 + 288 + 288 + 864 + 360 expected rows.
- Historical unit suites for FEMI-1, transfer, source-binding/Jev, and adjacent d1 — **44 passed** on Python 3.13 in the current analysis environment. Command:

```bash
python -m pytest -q code/femi1/tests code/transfer/tests code/source_binding_jev/tests code/d1_adjacent/tests
```

- Cross-model historical tests were **not certified runnable from the public archive**: they require `runs/cross_model/cases_PRIVATE.jsonl`, plus its associated frozen input files deliberately excluded from the public release. In attempted collection they failed on missing frozen assets, not on a scored result. The source is preserved for review.
- Full reexecution of paid model calls was not undertaken during repository packaging. Provider/model behavior may have changed.
- Release scanning checked several common token/key formats and private-key markers and found **no matching credentials**; that is not a comprehensive security review. Before public disclosure inspect all newly added files and verify benchmark text permissions.
