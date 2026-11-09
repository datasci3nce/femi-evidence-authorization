# Implementation-only notes (does not change preregistered experiments)

- Built `femi1_cases.py` after the protocol was locally frozen, implementing the two real scikit-learn task families and all four intervention configurations at seeds 101, 103, 107, and 109. Model fitting uses `StandardScaler` plus logistic regression for the reported candidate models, and a most-frequent dummy baseline. The inspector re-fits recorded models and recomputes the audit predicates from actual split/score/selection events.
- Copied the earlier frozen `femi1_stimuli.py` unchanged. Its message strings, treatment role/placement, output request, model parameters, seed/shuffle and primary contrasts are not altered.
- Implemented an OpenRouter runner with exact request-byte hashing, append-only transport-attempt/response logs, strict JSON verdict parsing, fixed max two transport retries, resume protection, and mandatory externally timestamped Git commit reference for live calls.
- Implemented a complete-case cluster bootstrap (10,000 within-family resamples) and intention-to-test outcome accounting, plus a blind manual rationale-coding worksheet.
- Added unit tests with deliberately fake model responses; these are testing fixtures, *not* empirical results and are not in the released outcome folders.
- Live status: NOT RUN; no credentials available in this execution environment. Running Colab on a remotely committed frozen packet is the next experimental step.
