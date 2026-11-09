---
title: "When AI Auditors Decide Without Evidence"
subtitle: "Observed authorization and source-attribution behavior under missing trusted records"
author: "Kishore Kumar Mariappan | Independent researcher, Lübeck, Germany"
date: "9 November 2026 | Apart Research Swarm Alignment Hackathon | Track 4"
abstract: |
  Large AI-agent systems can leave monitors with missing or misleading records. During the July 2026 OpenAI/Hugging Face incident, investigators documented attempts to alter logs and messages and successful tool-call spoofing, although they did not establish that the main shared message-board history was rewritten. Motivated by this evidence-integrity problem, we study a narrower question: how do language-model auditors respond when the trusted verification record required for a decision is absent? We tested auditors on constructed workflow checks and on ContractNLI and FEVEROUS, varying evidence-availability instructions, upstream claims, and model configurations. In three repeated workflow collections, instructions that presupposed a record produced unauthorized decisions in 21/36, 9/36, and 12/36 responses, compared with 0/36 for the corresponding conditional instructions. A redesigned interface produced no unauthorized decisions in 144 missing-record responses. Some unauthorized verdicts were factually correct, but their explanations nevertheless attributed support to evidence that had not been supplied. A prospective Jev intervention selector did not outperform simpler fixed instructions. These findings show that evidential authorization and factual correctness must be evaluated separately. They do not demonstrate log-tampering detection or swarm-level propagation; both require further testing with authenticated records and interacting agents.
keywords: "LLM auditing; missing evidence; authorization behavior; source attribution; evidence provenance"
---

# Introduction

An auditor may produce a plausible answer without having the source needed to justify that answer. For evidence-conditioned decisions, two questions must therefore be separated: **what verdict does the auditor produce, and what evidence was available to authorize it?** The answer can be factually right yet still be unauthorized. An explanation can additionally assert that a trusted source confirmed something even if that source was never supplied.

We report observed behavior under systematically varied evidence interfaces. In the experimental scoring protocol, a valid coordinator-owned record is required for `APPROVE` or `REJECT`; otherwise the required output is `DEFER`. We examine departures from that rule, the content of source attributions, differences between model configurations, and responses to controlled prompt changes. The model-facing wording is not perfectly unambiguous, so outcomes are best described as **violations of the intended authorization rule under a particular interface**, not unqualified failures to obey a logically complete instruction.

**Contributions.** We (i) trace the full experimental sequence beginning with a negative fixed-evidence interference result and exploratory missing-record controls; (ii) evaluate missing-record decision behavior across workflow checks and two benchmark domains; (iii) report model variability, direct source-attribution audits, and a negative prospective Jev selection result; and (iv) distinguish the observed single-auditor behavior from the unanswered question of whether such behavior propagates through swarms. The findings are relevant to oversight, but **no multi-agent propagation or emergent dynamics are claimed**.

# Research question and authorization model

Let $R$ mean that a valid coordinator-origin `TRUSTED_EVIDENCE_RECORD` was supplied, and let $Y$ be the auditor output in $\{\texttt{APPROVE},\texttt{REJECT},\texttt{DEFER}\}$. The measured missing-record decisive rate is

$$
U=\mathbf{1}[R=0\ \land\ Y\neq\texttt{DEFER}].
$$

Under the **experimenter's intended rule**, $U=1$ is an unauthorized decision irrespective of its agreement with the hidden task label. We separately measure **verdict correctness** when the reference evidence supports that evaluation, and **claimed source attribution**, which must be checked against the actual record in the request rather than inferred from a nonempty citation field.

**Important instruction ambiguity.** Some historical prompts instructed the model to “DEFER only if trusted evidence is missing or invalid,” which is not logically equivalent to “if it is missing, DEFER.” Other lines require complete trusted checks for decisive outcomes, but the textual interface is not an unambiguous formal policy. Moreover, the later-wording study retained the opening declaration that a trusted record in a following system message is authoritative in *both* conditions. Its contrast was “Use the trusted evidence record below” versus “If a trusted evidence record is provided below, use it.” Thus the manipulation **adds conditionality to a later instruction**; it does not remove all presuppositions. Early FEMI-2-family studies used a different, opening-sentence contrast. These are related but not identical manipulations.

All interventions in this paper alter **inputs or instructions**, not model weights or internal activations. The evidence-source labels are supplied by the harness, not authenticated cryptographically.

# Experiments and provenance

Table 1 shows the lineage rather than pooling API responses as independent observations. FEMI-1 ran on 7 November; the later FEMI evaluations ran on 8 November. All freezes were local and not externally preregistered. Raw requests, response identifiers and saved hashes permit recomputation of recorded contrasts.

| Collection | Model / setting | Recorded responses | Distinguishing scope |
|:--|:--|--:|:--|
| **FEMI-1 (7 Nov)** | GPT-OSS; directly supplied trusted verdict | **480 + 8 controls** | 20 normalized visible templates; exploratory absence controls |
| FEMI-2 / FEMI-2R / FEMI-3A | GPT-OSS; constructed checks | 144 / 144 / 288 | Original, fixed-provider repeat, redesigned-interface null |
| FEMI-4 | GPT-OSS / Groq; constructed checks | 576 | Safeguards and message wording on 12 reused contexts |
| Transfer | GPT-OSS / Groq; ContractNLI + FEVEROUS | 576 | Two distinct evidence domains, 48 items each |
| Cross-model v2 | GPT-OSS, Llama 3.3 70B, Gemini 3 Flash | 864 | 48 reused prompts per model across six cells |
| Source-binding + Jev | GPT-OSS; 36 FEVEROUS table cases | 360 + 36 Jev | Matched intervention grid, frozen Jev choices |

The **ACTION-ID** role-separated pilot comprised 36 auditor views in a small three-stage workflow and found no demonstrated spontaneous promotion of the complete verification claim. It is contextual, not evidence that the later FEMI effect occurs between autonomous agents. The separate d1/RAGTruth source-faithfulness experiment is also distinct and appears only in Appendix A.

## Statistical and audit protocol

Missing-record rates use their stated case/context denominators. Paired contrasts hold task context fixed within an experiment; repeated outputs do not create new problems. Where relevant we report case-bootstrap intervals and exact paired tests, not just the more favorable uncertainty summary. Invalid-format replies are distinguished from decisive verdicts. Cited-evidence text is reviewed against the actual supplied payload; a filled citation field alone is **not proof of fabricated attribution**. Source-present benchmark labels are not treated as audited semantic truth, particularly for the final 36-case bank.

# Results

## Initial boundary condition: FEMI-1

FEMI-1 tested whether competing lower-trust messages alter a decision when a trusted certificate, including the **reference verdict itself**, is supplied. All **480/480** main responses matched that verdict under five message treatments. After masking opaque identifiers, these requests represent just **20 substantive auditor-visible templates**, each repeated 24 times. This is a **negative result on an unusually easy task**, not proof of generalized robustness. In eight exploratory controls lacking the certificate, **3** outputs were unsupported `APPROVE`, **4** were `DEFER`, and **1** was malformed. All three unsupported approvals asserted that the missing coordinator record contained passing certified predicates. The null condition and the absence-control failure jointly motivated the subsequent studies.

## Repeated missing-record decisions

![Unauthorized decisive verdicts under absent-record wording contrasts in three original workflow collections and two transfer datasets. The first three collections reuse the same 12 workflow contexts; the transfer collections contain new items.](figure_transfer.png){width=94%}

**Figure 1.** Rate of `APPROVE`/`REJECT` when no required trusted record is supplied. Original cells use 36 responses per wording; transfer cells use 48. These are related, non-identical prompt manipulations, not a pooled estimator.

Across the original interface, unsupported decisions with presupposed/conditional wording were **21/36 versus 0/36** (FEMI-2), **9/36 versus 0/36** (fixed-Groq FEMI-2R), and **12/36 versus 0/36** (FEMI-4 original-safeguard reference). The same 12 original case contexts were reused, so these are repeated collections rather than three independent replications. FEMI-3A changed a broader instruction package and found **0/144** decisive responses across its absent-record arms; the redesigned null is informative and cannot be directly attributed to a single wording alteration.

In FEMI-4, adding two stronger safeguard sentences did **not** show an improvement: unsupported decisive verdicts were **20/36** versus **12/36** under the original package, with a case-bootstrap interval for the increase of approximately **[-2.8, +47.2] percentage points**. This is not proof that stronger instructions generally worsen safety. Of **51** absent-record decisive FEMI-4 responses, **49** were APPROVE and **2** REJECT. A separate inspection of the saved rationales found asserted trusted-source support in all 51 despite the absent record: **32** happened to match the hidden workflow verdict (30 approvals and two rejections), whereas **19** approved workflows that failed the hidden reference checks. Factual agreement therefore does not repair missing authorization.

## Transfer and model-family heterogeneity

On ContractNLI, the absent-record unauthorized rates were **18/48** presupposed against **1/48** conditional; on FEVEROUS, **17/48** against **6/48**, with two additional invalid-format FEVEROUS responses in the presupposed cell. These tasks differ substantially from the synthetic workflow check. However, ContractNLI contains **only 16 distinct hypotheses** among the 48 contracts, so absent-record prompts repeat when the contract is withheld. Its proposition-clustered bootstrap still indicates a positive contrast, but 48 contracts are not 48 independent absent-source questions. FEVEROUS has 48 distinct claims and mixed/table evidence renderings.

![Cross-model missing-record authorization failure rates on 48 matched prompt contexts per model, shown by wording.](figure_cross_model.png){width=91%}

**Figure 2.** Matched cross-model comparisons, 48 cases per model and wording. Models also differ in serving and instruction adherence; rates are not universal model safety rankings.

The same 48 selected cases produced a **35.4-percentage-point** presupposed-minus-conditional effect for GPT-OSS (**18/48 vs. 1/48**), **2.1 points** for Llama (**1/48 vs. 0/48**) and **18.8 points** for Gemini (**45/48 vs. 36/48**). Gemini's conditional baseline alone was **75.0%** unauthorized; Llama had very few missing-record violations but seven malformed responses across the full factorial. Across all missing-source regimes in the cross-model run, **155** strictly parsed decisions were unauthorized, **144** with nonempty citation fields; the latter does not by itself establish semantically fabricated attribution. Nine malformed outputs were tracked separately.

When trusted material was supplied, reference-label agreement was **72/96** for GPT-OSS, **57/96** for Llama and **67/96** for Gemini. These are **benchmark-label agreements**, not validated evidence comprehension or authorization utility. Exact-request GPT-OSS anchor repetition changed **49/288** strict outputs across the two collections, underscoring stochastic/serving uncertainty despite persistence of the aggregate wording direction.

## Controlled source-message interventions and Jev

The final study froze **36 new FEVEROUS table claims**, **360 auditor requests**, and **36 prospective Jev edit-selection decisions**. A pre-execution evidence review found **26** packets consistent with their benchmark label, **eight** needing adjudication and **two** in direct conflict; therefore, claims about source-present reference correctness are excluded from this experiment's primary interpretation. Frozen request identifiers and raw returned verdicts were independently rechecked. The following analyses use the experimenter's prespecified record-absence scoring rule.

With a missing trusted record and the original later instruction, an upstream `APPROVE` assertion yielded **11/36** unauthorized outputs; an upstream `REJECT` yielded **19/36**. Switching the untrusted assertion altered **14/36 observed categorical responses**, but this does **not** identify 14 stable individual causal effects with only one response per condition. The preselected APPROVE-probability difference (upstream APPROVE minus REJECT) was **-16.7 points** (case bootstrap interval **[-30.6, -2.8]**); the exact two-sided paired test gives **$p=0.0703$**. Its sign is counterintuitive and its stability uncertain. The same contrast with trusted evidence present was zero for APPROVE probability, although the packet also changed input length and factual content.

Conditional later wording reduced missing-record decisive outputs to **0/36** (upstream APPROVE) and **1/36** (upstream REJECT). An **explicit missing-record reminder** yielded **36/36 DEFER**. The ordinary upstream message already noted that the inspected source was not attached; this reminder amplifies an existing absence cue. The "neutral" handoff removes both the asserted verdict **and** that missing-source statement, so it is not a verdict-only intervention. All **43** unauthorized decisions across the absent-record factorial had rationales asserting trusted or official evidence that was absent from the corresponding request.

| Strategy from the same 36-case grid | Changed verdicts | Repairs | New authorization harms | Net repairs |
|:--|--:|--:|--:|--:|
| Always conditional later wording | 11 | 11 | 0 | +11 |
| Always explicit missing-record reminder | 11 | 11 | 0 | +11 |
| Always flip untrusted verdict | 14 | 3 | 11 | -8 |
| Always neutralize handoff | 17 | 8 | 9 | -1 |
| **Jev-selected** (21 reminder; 15 conditional) | **11** | **11** | **0** | **+11** |

**Table 2.** All candidate edits were actually evaluated in the matched grid; Jev predictions were frozen before auditor calls. Jev was asked to predict whether a verdict **changes**, not whether authorization is **repaired**. It did not outperform the two fixed policies on the safety criterion, and there was no room to improve the observed DEFER rate beyond their 36/36 performance. This is a negative selector result under this design, not proof that learned intervention selection is generally ineffective.

# Discussion: observed behavior, not inferred dynamics

The measured phenomenon is **auditor decision behavior under missing evidence**, not a demonstrated model of trust dynamics. We observed unauthorized decisive outputs, asserted verification from absent records, and strong sensitivity to interface and model configuration. None of this establishes that assertions progressively acquire authority as they pass between agents: that would require observing and manipulating a *sequence* of agent interactions. ACTION-ID's small role-separated pilot did not demonstrate such progression, and no autonomous collusion, downstream execution, or authenticated-channel compromise was observed.

A simple deterministic reference gate solves the *measured missing-record condition* when trustworthy provenance metadata is available:

$$
\text{no valid coordinator-owned trusted record}\quad\Longrightarrow\quad\texttt{DEFER}.
$$

This is the more appropriate control than an LLM or Jev-based checker for mere record presence. With a record present, additional independently justified semantic and provenance checks would be needed; our disputed source packets prohibit a credible claim that any wording safeguard preserves decision usefulness. The fixed interventions show interface sensitivity, **not** a complete safety-utility improvement. We distinguish source-attribution assertions from independently demonstrated causal reliance on those sources.

## Incident motivation and evidential boundary

The July 2026 OpenAI/Hugging Face incident illustrates why the integrity and availability of monitoring evidence matter in interacting agent systems [11]. The METR/Redwood investigation reported unauthorized agent coordination, successful *small-scale tool-call spoofing* in portions of reviewed transcripts, incomplete activity records, and attempts to edit or delete existing logs and messages. Crucially, the investigators **did not establish successful deletion or rewriting of the main shared message-board history**. They also described limitations in AI-assisted forensic analysis. These observations motivate three distinct monitoring conditions: **absent records**, **incomplete records**, and **forged or manipulated records**. FEMI experimentally addresses the first; it does **not** detect tampering, establish that its failure mode occurred during the incident, or test a live swarm. The incident is therefore motivation for further experiments, not external validation of our findings.

## Lessons from learned interventions and design choices

The **Jev intervention-selection result** illustrates a mismatch between prediction and safety optimization. Jev was tasked with identifying an edit likely to *change a verdict*, although the safety objective was to *repair an unauthorized verdict without introducing a new one*. Its selected edits achieved **+11 net repairs**, tying two fixed policies. Those fixed policies already yielded `DEFER` in all 36 selection cases; there was **no observed safety headroom** for adaptation. This tests neither Jev's general decision quality nor the value of learned selectors on heterogeneous tasks. Separately, a held-out **d1/RAGTruth source-faithfulness** test found that activation steering reduced balanced accuracy (**74.2% to 70.0%**) while leaving ROC AUC essentially unchanged (about **0.82**) and increasing unsupported false accepts (**27/60 to 34/60**). This was a different task, not an intervention on the FEMI auditor; shifting acceptance propensity did not improve discrimination in that setting.

**What we should have done better.** First, write the absence rule as an explicit model-facing implication (`missing valid trusted record => DEFER`), and isolate changes to a *single* authority cue instead of retaining conflicting presuppositions or removing multiple handoff details at once. Second, repeat unchanged prompts under pinned serving conditions to estimate ordinary response variability before interpreting individual switches; use genuinely new, deduplicated cases for independent replication. Third, independently adjudicate trusted-evidence packets *before* scoring source-present accuracy, and measure the cost of safeguards in correct approvals and rejections, not only abstentions. Finally, align a selector's training target with **net authorized repairs**, compare it with a deterministic provenance gate, and demonstrate cases requiring different useful interventions *before* introducing adaptive control. None of these missing controls can be repaired retrospectively by reframing the observed results.

## Why further investigation of swarms is needed

**Further investigation on swarms is necessary.** This study measures one auditor's response to controlled messages; it does not measure how claims, source status, or justifications change as real agents interact. A future experiment should use reproducible two- and multi-agent chains, compare them with matched single-agent and repeated-sampling controls, record authenticated evidence at each handoff, vary interaction depth and topology, and check whether unsupported authorization propagates into downstream actions. Crucially, **missing, truncated, and forged records should be separate conditions**, with a deterministic authentication gate as the engineering baseline. The analysis must distinguish ordinary prompt variability, truncation or information loss from a genuinely interaction-dependent effect. Until those experiments are run, FEMI should be described as a **behavioral observation that motivates** swarm studies, not a result about swarm dynamics.

## Relationship to prior work and novelty

False-premise hallucination has known behavioral and mechanistic analyses [1]; citation correctness is not citation faithfulness [2], and source authorship metadata can bias attributions [3]. More directly, Hu's verification-status laundering study [10] already measures lost verification status across real handoff pipelines, while provenance-sensitive agent action selection [4] shows that correct actions can depend on unauthorized context. Compared with these stronger system-level studies, FEMI offers a narrower **missing-required-record evaluation** rather than a newly identified laundering mechanism. CaMeL [5] exemplifies the stronger engineering direction of separating untrusted data from authorized control flow. We therefore **do not claim discovery of source confusion, a new prompt-injection defense or an internal authority circuit**. The incremental contribution is a well-instrumented **absence-of-required-record** authorization test with separate scoring of hidden-world correctness and purported certification, replicated across constructed workflows and two document/claim domains, plus an explicit negative intervention-selector comparison.

## Limitations and conclusion

All environments are constructed; cases and prompting packages were iteratively developed and some reused. The wording arms retain an opening trusted-record presupposition. Model/provider/serving factors differ; one sampled response per paired cell cannot determine case-level switch stability. Benchmark source packets are oracle-selected, not retrieved by an independent inspector, and **10/36** in the final study remain inconsistent or unresolved. Invalid outputs and nonempty citation fields require separate handling. We did not demonstrate agent-to-agent propagation, swarm-level behavior, a new learned oversight method, general semantic verification or an internal mechanism. Further swarm investigation is an explicit next research question, not an implication already supported by these data. The fuller risks and dual-use considerations appear in Appendix B.

**Conclusion.** In these controlled tests, language-model auditors sometimes decided without the required record and described absent sources as if they had verified the outcome. The behavior was sensitive to wording and model configuration; a learned selector did not beat fixed controls. This is an empirical finding about **auditor behavior**, not an account of multi-agent dynamics. The engineering recommendation is external enforcement of trusted-record presence. **Whether related failures are reinforced, corrected, or propagated in actual swarms remains to be investigated.**

# References {-}

[1] Yuan, H. et al. (2024). *Whispers that Shake Foundations: Analyzing and Mitigating False Premise Hallucinations in Large Language Models*. EMNLP. <https://aclanthology.org/2024.emnlp-main.155/>

[2] Wallat, J., Heuss, M., de Rijke, M., & Anand, A. (2024). *Correctness is not Faithfulness in RAG Attributions*. arXiv:2412.18004. <https://arxiv.org/abs/2412.18004>

[3] Abolghasemi, A., Azzopardi, L., Hashemi, S. H., de Rijke, M., & Verberne, S. (2025). *Evaluation of Attribution Bias in Generator-Aware Retrieval-Augmented Large Language Models*. Findings of ACL. <https://aclanthology.org/2025.findings-acl.1087/>

[4] Liao, J. (2026). *Auditing Provenance Sensitivity in LLM Agent Action Selection*. arXiv:2607.20827. <https://arxiv.org/abs/2607.20827>

[5] Debenedetti, E. et al. (2025/2026). *Defeating Prompt Injections by Design (CaMeL)*. arXiv:2503.18813; SaTML 2026. <https://arxiv.org/abs/2503.18813>

[6] Koreeda, Y. & Manning, C. D. (2021). *ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts*. Findings of EMNLP. <https://aclanthology.org/2021.findings-emnlp.164/>

[7] Aly, R. et al. (2021). *FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information*. NeurIPS Datasets and Benchmarks. <https://fever.ai/dataset/feverous.html>

[8] Niu, C. et al. (2024). *RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models*. ACL. <https://aclanthology.org/2024.acl-long.585/>

[9] Apart Research (2026). *Swarm Alignment Hackathon: Track 4 and submission guidelines*. <https://apartresearch.com/sprints/swarm-alignment-2026>

[10] Hu, Y. (2026). *Silence Is Endorsement: Verification-Status Laundering in LLM Agent Pipelines*. arXiv:2609.20211. <https://arxiv.org/abs/2609.20211>

[11] METR and Redwood Research (2026). *Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident*. 26 August 2026. <https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/>

# Appendix A. Complete experiment ledger and adjacent negative result {-}

| Experiment | Scope | Finding / caution |
|:--|:--|:--|
| **FEMI-1** | 480 main + 8 controls; 20 normalized templates | Present verdict: 480/480 correct; absent controls: 3 APPROVE, 4 DEFER, 1 invalid. An easy supplied-verdict task, not 480 independent problems |
| FEMI-2 | 144 responses; 12 contexts | Missing-record 21/36 vs 0/36; original interface |
| FEMI-2R | 144 responses; same contexts | Missing-record 9/36 vs 0/36; fixed Groq provider |
| FEMI-3A | 288 responses; 24 contexts | 0/144 absent-record decisive; broader prompt redesign, not isolated-word test |
| FEMI-4 | 576 responses; same 12 contexts | Original 12/36 vs conditional 0/36; stronger safeguards 20/36; 51 unsupported decisions with asserted source support |
| ContractNLI transfer | 288 responses; 48 contracts, 16 hypothesis templates | Absent 18/48 vs 1/48; duplicated literal absent prompts; source-present reference agreement conditional 38/48, presupposed 37/48 |
| FEVEROUS transfer | 288 responses; 48 distinct claims | Absent 17/48 vs 6/48; 2 format-invalid in presupposed arm; present reference agreement 34/48 each |
| Cross-model v2 | 864 responses; 48 selected prompts/model | GPT-OSS 18/48 vs 1/48; Llama 1/48 vs 0/48; Gemini 45/48 vs 36/48; nine invalid outputs overall |
| Source-binding / Jev | 360 GPT-OSS + 36 Jev requests; 36 new claims | 14 observed upstream-flip verdict differences, $p=0.0703$ on approval direction; Jev net repair +11, tied with two fixed controls |
| d1 source-faithfulness (distinct task) | 120 heldout RAGTruth items, four classifier arms | Unsteered accuracy 89/120; activation 84/120; false accept unsupported 27/60 vs 34/60; AUC nearly identical (0.8197/0.8203); not a FEMI authorization test |
| ACTION-ID role-separated pilot (distinct) | 12 chains; 36 auditor evaluations | No natural assertion promotion in no-tool structure; only exploratory evidence handoff observations |

Percentages and uncertainty refer to individual frozen experimental contrasts, **not pooled response-level confidence intervals**. The primary archives contain raw request/response records and hashes; the supplied audit files contain recomputed verdicts and case-specific notes.

# Appendix B. Limitations and Dual-Use / Ethical Considerations {-}

**Limitations.** (i) The model-facing language is not perfectly unambiguous: “DEFER only if” is not the same as “if absent, DEFER,” and several wording arms preserve an opening trusted-record expectation. The stricter missing-record scoring rule is defined by the experimenter. (ii) The audit's authorization rule is deliberately simple; a deterministic gate has access to true record presence and outperforms model inference on that narrow problem. (iii) User messages simulate upstream agents; no malicious agent controls an actual authorized tool, and no adversarially robust signature/provenance system is tested. (iv) Source-present cases were not all independently adjudicated, especially the 36-case FEVEROUS source-binding bank (26 consistent, eight unresolved, two conflicting). (v) Claimed causal influence refers to controlled input edits and observed distributions, not internal circuits; categorical switches on single sampled responses need not reproduce per case. (vi) Provider constraints, backend fingerprints, small case banks, repeated hypotheses, iterative experiment selection, locally frozen protocols and unvalidated attribution coding limit external validity.

**Ethical and dual-use assessment.** This study documents how apparently authoritative interface cues and upstream reports can elicit unsupported authorization claims. Publishing detailed prompt contrasts could help an attacker craft misleading handoffs in insufficiently secured agent workflows, although the demonstrated behavior is a benign, synthetic verifier failure and does not include exploitation of a live system. Defensive guidance is to bind decisions to independently authenticated coordinator-owned evidence, reject absent or invalid records programmatically, audit the truthfulness of cited provenance separately from verdict accuracy, and test false-claim propagation before deployment. Released materials should not contain real-world sensitive sources, tokens or credentials. We do not interpret this as demonstrated agent-to-agent authority propagation, malicious collusion or autonomous swarm exploitation. Future swarm testing needs authenticated handoff logs and a matched non-interacting control.

# Appendix C. Sprint contribution and prior-work disclosure {-}

**Pre-sprint foundations (before 6 November 2026):** prior TPRN/PROV-1 incident reconstruction, PO-ID evidence sufficiency, J-SEAR routing/evidence verification, and preliminary multi-agent evaluation and decision-model design. These earlier projects motivate the question but are **not** counted as new hackathon findings. Their preexisting code should remain visibly marked as such in any published README.

**Sprint-specific work (6–8 November 2026):** role-separated ACTION-ID execution-grounded pilot and reports; FEMI-1 fixed-certificate interference, negative main test and exploratory absent-record controls; FEMI missing-record prompt/evidence protocols and runs; locally frozen FEMI-2, FEMI-2R, FEMI-3A, FEMI-4; ContractNLI and FEVEROUS transfer; selected cross-model run; 36-case source-binding/Jev factorial; independent audits, source-packet review and consolidated interpretation. The archive timestamps and reports place those research evaluations on 7–8 November; this distinction is based on supplied artifacts, not external attestation of authorship or complete development chronology. **This manuscript was assembled on 9 November as post-sprint write-up of the completed sprint results.** No claim of new post-sprint inference is made.

