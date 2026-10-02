## My Honest Take

**For your invoice/document RAG eval use case specifically:**

**Go Hybrid — it's the no-brainer choice.**

Here's why:

- **~70% of your test cases are extractive** (account numbers, amounts, dates, IDs). These are **exact/regex territory**. Using an LLM Judge on `"9304861812"` is wasteful — it's like using a sledgehammer on a thumbtack.

- **Local embeddings are solid, but tricky to threshold.** Cosine similarity of `0.85` sounds good on paper, but invoice data has edge cases — `"$1,809.96"` vs `"$1,809"` might score `0.91` and pass when it shouldn't. You'll spend time tuning thresholds.

- **ROUGE/BLEU are poor fits for your domain.** They reward word overlap, not semantic correctness. `"The balance is not $500"` scores high against `"The balance is $500"` — dangerous for financial data.

- **LLM Judge is still worth keeping** — but *only* for complex reasoning questions like `"Summarize the payment terms"` or `"What changed between invoices?"`. These genuinely need semantic understanding.

---

### My Recommended Priority Order:

```
1. Exact/Regex Match  → Numbers, IDs, dates       (0 tokens, instant)
2. LLM Judge          → Complex/reasoning only    (~400 tokens, targeted)
3. Skip local embeds  → Not worth the calibration overhead for financial data
```

**Bottom line:** Don't overcomplicate it. A well-written regex gate + targeted LLM Judge will outperform all other options in both cost and *reliability* for invoice RAG eval.