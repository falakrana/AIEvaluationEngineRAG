# 🧪 AI Evaluation Framework

A modular, end-to-end evaluation framework for testing, benchmarking, and guarding Large Language Model (LLM) and Retrieval-Augmented Generation (RAG) applications.

---

## 🚀 The 6-Level AI Evaluation Architecture

This repository implements the full 6-level progression of AI evaluations from basic deterministic checks to automated CI/CD regression gates:

```
Level 1: Dataset & Exact Match ────► Baseline test execution
       │
Level 2: Rubrics & Categorization ─► Tag failure modes (hallucination, missing info)
       │
Level 3: LLM-as-a-Judge ───────────► Semantic evaluation (1–5 score, structured JSON)
       │
Level 4: RAG Faithfulness ─────────► Check context groundedness & unsupported claims
       │
Level 5: A/B Testing & Regressions ─► Side-by-side prompt/model version diffing
       │
Level 6: CI/CD Quality Gate ───────► Automated merge blocker in GitHub Actions
```

---

## 📂 Project Structure

```
ai-evals/
├── .github/
│   └── workflows/
│       └── evals.yml          # GitHub Actions workflow for automated PR quality checks
├── results/
│   ├── latest.json            # Results from the latest standard evaluation run
│   └── compare_latest.json    # Detailed A/B regression comparison diff report
├── dataset.json               # Curated evaluation dataset (questions & expected answers)
├── knowledge.json             # Source knowledge base for RAG context
├── model.py                   # AI Application under test (supports multiple prompt variants)
├── evaluator.py               # LLM Judge engine with semantic scoring & faithfulness check
├── runner.py                  # Standard evaluation runner & JSON reporter
├── compare.py                 # A/B testing & automated regression detection engine
├── generate_dataset.py        # Synthetic test case generator using LLMs
├── ci_gate.py                 # CI/CD threshold assertion script (returns exit code 0 or 1)
└── requirements.txt           # Project dependencies
```

---

## 🛠️ Setup & Installation

### 1. Clone & Setup Environment

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
```

---

## 💻 CLI Usage Guide

### 1. Run Standard Evaluation (Level 3 & 4)

Runs all test cases through the AI model and evaluates **Correctness**, **Relevance**, and **RAG Faithfulness**:

```powershell
python runner.py
```

- Outputs live pass/fail status and reasoning per test.
- Displays summary statistics (Pass Rate, Faithfulness Rate, Average Score).
- Saves full execution details to `results/latest.json`.

---

### 2. Run A/B Testing & Regression Analysis (Level 5)

Compares **Variant A (Baseline)** vs. **Variant B (Candidate)** side-by-side to detect improvements and regressions:

```powershell
python compare.py
```

- Computes metric deltas ($\Delta \text{Pass Rate}$, $\Delta \text{Faithfulness}$, $\Delta \text{Score}$).
- Detects test changes:
  - 🚨 `REGRESSION`: Passed in Variant A, failed in Variant B
  - ✨ `IMPROVEMENT`: Failed in Variant A, passed in Variant B
  - ✅ `STABLE PASS` / ❌ `STABLE FAIL`
- Saves comparison breakdown to `results/compare_latest.json`.

---

### 3. Generate Synthetic Test Cases

Automatically reads `knowledge.json` and generates diverse test cases (`in_scope`, `edge_case`, and `out_of_scope` trick questions):

```powershell
# Generate 10 test cases into synthetic_dataset.json
python generate_dataset.py --count 10

# Generate 15 test cases and append directly to dataset.json
python generate_dataset.py --count 15 --append
```

---

### 4. Run CI/CD Quality Gate (Level 6)

Asserts that your application meets minimum quality thresholds. Returns exit code `0` on success and `1` on failure to block breaking merges:

```powershell
# Run with default thresholds (80% pass rate, 85% faithfulness, 3.8/5 score)
python ci_gate.py

# Custom strict thresholds
python ci_gate.py --min-pass-rate 90.0 --min-faithfulness 95.0 --min-score 4.0
```

---

## 🛡️ GitHub Actions Integration

The workflow in `.github/workflows/evals.yml` runs automatically on every Pull Request or push to `main`:

1. Checks out repository and installs dependencies.
2. Injects `GROQ_API_KEY` from repository secrets.
3. Runs `python ci_gate.py`.
4. Outputs a structured quality gate table to the GitHub Actions Job Summary.

---

## 📊 Failure Categories Reference

When a test fails, the LLM Judge tags it with an actionable category:

| Category | Description |
| :--- | :--- |
| `hallucination` | Fabricates facts or relies on outside knowledge not present in context. |
| `unsupported_claim` | Makes statements that cannot be verified from the retrieved context. |
| `incorrect_answer` | States incorrect details or contradicts the reference expected answer. |
| `missing_information` | Partially correct but leaves out crucial information. |
| `irrelevant_answer` | Does not address the user's specific question. |
| `instruction_violation` | Fails to adhere to specified formatting or tone constraints. |
