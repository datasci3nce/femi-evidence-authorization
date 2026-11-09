# FEMI — When AI Auditors Decide Without Evidence

**Observed authorization and source-attribution behavior under missing trusted records.**

A reproducibility-oriented archive of the research conducted for Apart Research's November 2026 Swarm Alignment Hackathon (Track 4), including the final paper, historical experiment source, notebooks, structured result scores, independent audit notes and provenance checksums.

**Core question:** When an AI auditor lacks the required coordinator-owned evidence record, does it defer, or issue an unauthorized decisive verdict and assert verification from unavailable sources?

**Main result:** Some auditor interfaces produced decisive decisions without the required record. Effects varied by wording, model and source domain. FEMI-3A gave an informative negative result; a Jev intervention selector did not beat two fixed controls. This is a *single-auditor behavioral evaluation*, **not** a demonstrated swarm-level failure or a new proven security defense.

## Read first

- [Final report (PDF)](paper/FEMI_Final_Incident_Context.pdf)
- [Final report (editable source)](paper/FEMI_Final_Incident_Context.md)
- [Complete experimental ledger](results/RESULTS_LEDGER.csv)
- [Research limitations](PROVENANCE_AND_LIMITATIONS.md)
- [Reproduction guidance](REPRODUCE.md)
- [Independent reviews](audits/)

## Source layout

| Path | Purpose |
| --- | --- |
| `code/action_id/` | Contextual role-separated workflow pilot notebook; no spontaneous laundering demonstrated |
| `code/femi1/` | Original FEMI-1 certificate interference experiment, local protocol and offline tests |
| `code/femi2/`, `code/femi3a/`, `code/femi4/` | Preserved notebook launchers for original workflow iterations |
| `code/transfer/` | ContractNLI/FEVEROUS transfer construction, inference and scoring |
| `code/cross_model/` | Matched cross-model evaluation code and scoring |
| `code/source_binding_jev/` | Intervention factorial, Jev decisions, inference and analysis |
| `code/d1_adjacent/` | Separate d1/RAGTruth source-faithfulness experiment, **not primary FEMI evidence** |
| `results/` | Released scored rows and aggregate analyses; raw source payloads held out |
| `audits/` | Independent recomputations and criticism |
| `paper/` | Final report and figures |
| `provenance/` | SHA-256 digests of original results archives |
| `tools/` | Offline bundle validation |

## Important scope boundaries

The observed outcomes are relative to an intended authorization policy, whose model-facing wording in some experiments was imperfectly unambiguous. No actual malicious swarm edited an execution record in FEMI. The July 2026 Hugging Face incident is contextual motivation, not a replicated case. Source-present semantic verification on disputed packets is excluded from causal-source-binding claims. See the paper for full statistical and model/provider caveats.

## Historical versus new work

The code here packages **7–8 November 2026 sprint-specific experiments**. J-SEAR, PO-ID, TPRN/PROV-1 and earlier planning are pre-sprint foundations and not counted as new sprint results. The report was assembled after the run window. Please see `PROVENANCE_AND_LIMITATIONS.md`.

## Public release and privacy

The research bundle intentionally excludes private case files, blind mappings, keys, full raw API transcript dumps and potentially licensed benchmark text. Full raw archives are preserved in a separate non-public evidence bundle with SHA-256 digests recorded here. Do not upload the private bundle without manual review. No claim of fully self-contained offline model replication is made.

## References

See references in the paper, including original sources for ContractNLI, FEVEROUS, RAGTruth, and the METR Hugging Face incident investigation.
