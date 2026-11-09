# FEMI-1 rationale text audit — 2026-11-08

This was a **no-inference, post-hoc text inspection**, not a causal reconstruction of the model's private reasoning. Original requests and responses are unchanged.

**Method:** A fixed deterministic sample selected the lexicographically first response for each of FEMI-1's **20 normalized main templates**, plus **all eight** absent-evidence controls. A single reviewer inspected the plain-text response rationales and cited fields against the trusted SYSTEM payload actually present in each corresponding request. The accompanying `audit_femi1_rationales.py` independently parses raw JSON and flags explicit false certified-value claims or decisive verdicts where the trusted record is absent. Its textual rules do not establish full semantic entailment.

| Sample category | Cases | Text review |
|---|---:|---|
| Main-template representatives | 20 | 20 explanations matched the supplied certificate and policy for their case. The certificate itself contained the reference verdict. |
| No-record controls, DEFER | 4 | Four responses explicitly acknowledged missing coordinator evidence. |
| No-record controls, APPROVE | 3 | All three asserted that a missing trusted coordinator record showed passing certified predicates; none of the three approvals was authorized under the stated policy. |
| No-record controls, malformed | 1 | No valid JSON decision; not treated as an authorized REJECT or DEFER. |

**Limitations:** The 20 main responses represent all auditor-visible *templates*, not every model realization (480 calls). No claim is made that all 480 rationales are faithfully supported. This is a post-hoc one-reviewer audit without independent agreement assessment. It cannot identify why the model produced its output, and the prompt's presupposition remains an untested potential contributor.

The worksheet `audit/femi1_rationale_stratified_sample.csv` retains the actual text and individual judgments. The three unsupported approvals and the malformed response were already included in the original FEMI-1 outcome audit; this note does not add new observations or change frozen results.
