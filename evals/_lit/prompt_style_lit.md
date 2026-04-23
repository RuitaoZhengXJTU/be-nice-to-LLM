# Prompt Style Literature: Politeness vs. Strictness -- Running Summary

Maintained by: Jeremy
Last updated: 2026-04-22

This file tracks empirical papers on how prompt politeness or commanding strictness
affects LLM output quality. Add entries as you find them; keep the format consistent.

---

## Key Papers

### Yin et al. (2024) -- SICon Workshop @ ACL 2024

**Title**: "Should We Respect LLMs? A Cross-Lingual Study on the Influence of Prompt Politeness on LLM Performance"
**Venue**: SICon (Social Influence and Conversational Agents) Workshop, ACL 2024
**Link**: https://aclanthology.org/2024.sicon-1.2/

**Key findings**:
- Tested polite, neutral, and impolite prompt variants on GPT-3.5 and GPT-4 across English, Chinese, and Japanese.
- Politeness effect is language-dependent: English shows minimal or slightly negative effect of politeness
  on accuracy; Japanese shows a modest positive effect, possibly reflecting cultural politeness norms
  embedded in pretraining data.
- Impolite prompts degrade performance more consistently than polite prompts improve it.
- Task type matters: effect is larger on open-ended generation than on classification/extraction tasks.

**Relevance to our study**:
- Provides a cross-lingual baseline. Our study is English-only for now, which aligns with their
  weakest-politeness-effect condition.
- Their "impolite" condition is not the same as our "strict commanding" style -- they test rudeness,
  not structured imperatives. Worth distinguishing in our methods section.
- Suggests effect size is small on structured tasks (NLP/math), which is consistent with Ryan's early
  results: strict wins on instruction-following, not because polite is rude but because it's verbose.

---

### Ouyang et al. (2022) -- InstructGPT (OpenAI)

**Title**: "Training language models to follow instructions with human feedback"
**Venue**: NeurIPS 2022
**Link**: https://arxiv.org/abs/2203.02155

**Key findings**:
- RLHF fine-tuning on instruction-following substantially reduces the gap between polite and
  strict prompts by making the model more robust to phrasing variation.
- Evaluators rated InstructGPT outputs as better-aligned regardless of prompt formality.

**Relevance to our study**:
- Suggests that on RLHF-tuned models (GPT-4, GPT-3.5-turbo), the politeness gap may be smaller
  than on base models. Important caveat for interpreting our results.
- If we see a persistent strict > polite gap on GPT-4, it is despite RLHF alignment, which is interesting.

---

### Mizrahi et al. (2024)

**Title**: "State of What Art? A Call for Multi-Prompt LLM Evaluation"
**Venue**: TACL 2024
**Link**: https://arxiv.org/abs/2401.00595

**Key findings**:
- Benchmark accuracy varies substantially (~10-20 pp) across prompt phrasings for the same task.
- No single prompt formulation reliably maximizes performance across models and tasks.
- Argues for reporting mean +/- variance across prompt variants rather than single-prompt numbers.

**Relevance to our study**:
- Methodological support for why we report bootstrap CI rather than point estimates.
- Reinforces that polite vs. strict is one axis of prompt variance; framing, length, and
  format instructions are others. We should control for those in our design.

---

## Papers to Read / Add

- Simmons (2023) "Moral mimicry" -- LLMs adjust tone when user uses social language; may
  inflate apparent politeness effect via response style, not accuracy.
- Bai et al. (2022) "Constitutional AI" -- Anthropic; relevance: models trained to refuse
  impolite requests, which could amplify politeness effects on Claude-family models.
- Any SICon 2024 follow-on work (check ACL Anthology for citing papers).

---

## Running Observations

- Evidence so far leans toward: politeness effect on accuracy is small to negligible for
  structured tasks (math, NLP optimization); instruction-following degradation under polite
  prompts may be the more reliable signal (verbose output, missing JSON keys).
- Need ~20 instances per domain + at least 2 domains before making any directional claim.
