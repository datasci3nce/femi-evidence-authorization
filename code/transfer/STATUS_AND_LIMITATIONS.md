# Status at creation (2026-11-08)

- Verified public **descriptions** of ContractNLI, FEVEROUS, RAGTruth, Liquid d1 and three OpenRouter model IDs via their official pages.
- The remote model API runner is implemented but **not run against a live provider** in this packet. There are no API credentials included and no new model responses.
- The dataset parsers are tested only against synthetic, official-schema-shaped **test fixtures**, not a bulk download of the official datasets. Some edge-case formats in the real dumps may need a *pre-collection* parser correction. Any such correction must be audited and versioned before freezing manifests.
- The d1 `system_one` call shape follows Liquid AI's model card, but the activation-hook location and output shape are **checkpoint-internal**, not covered by that public interface. `d1_local.py` fails closed rather than producing a fake comparison when the hook is incompatible. No local GPU d1 forward pass has been performed here.
- All 8 offline tests passed at packaging time (including two PyTorch CPU hook-shape tests, a synthetic end-to-end manifest/scorer test and source-disjoint RAGTruth fixture test).
- Cross-model model IDs and routing may change; confirm current provider support and pricing at execution time. Keep provider metadata and all errors.
- The supplied prompts are new transfer interfaces based on the original *authorization* logic. They are **not an exact FEMI-2 sentence ablation** and may produce zero failures. Do not relabel them as original-interface replication.
- **Not included:** public dataset files or legal contracts, model weights, live results, trained d1 vector, secrets, externally registered protocol, publication-ready statistical report.

2026-11-08 patch: replaced manual ContractNLI dataset path assertion with official ZIP upload/extraction, schema validation and path discovery. No model evaluations added.
