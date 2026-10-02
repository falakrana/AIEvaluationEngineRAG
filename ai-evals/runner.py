import json
import os
from collections import Counter
from dotenv import load_dotenv

from model import run_model
from evaluator import evaluate

load_dotenv()

# Load test cases
dataset_path = os.path.join(os.path.dirname(__file__), "dataset.json")
with open(dataset_path, "r", encoding="utf-8") as f:
    tests = json.load(f)

results = []
passed = 0
faithful_count = 0
total_score = 0
failure_categories = Counter()

print("=" * 70)
print("🚀 Starting RAGnition AI Evaluation Run (LLM-as-a-Judge with Faithfulness)")
print(f"📋 Loaded {len(tests)} test cases from dataset.json")
print("=" * 70 + "\n")

for test in tests:
    test_id = test.get("id", "?")
    question = test["question"]
    expected = test["expected"]
    test_type = test.get("type", "general")

    print(f"▶ Test #{test_id} [{test_type}]: {question}")

    # 1. Run RAG Pipeline (calls RAGnition backend API)
    model_output = run_model(question)
    actual_answer = model_output.get("answer", "")
    retrieved_context = model_output.get("context", "")
    sources = model_output.get("sources", [])

    print(f"💬 Model Answer: {actual_answer}")
    if sources:
        pages_cited = [s.get("page_number", "?") for s in sources]
        print(f"📄 Retrieved Chunks from Pages: {pages_cited}")

    # 2. Judge Model Answer
    eval_result = evaluate(
        question=question,
        expected=expected,
        actual=actual_answer,
        context=retrieved_context
    )

    is_pass = eval_result.get("passed", False)
    is_faithful = eval_result.get("faithful", False)
    score = eval_result.get("score", 0)
    category = eval_result.get("failure_category", "none")
    reason = eval_result.get("reason", "")
    unsupported_claims = eval_result.get("unsupported_claims", [])

    if is_pass:
        passed += 1
    else:
        failure_categories[category] += 1

    if is_faithful:
        faithful_count += 1

    total_score += score

    record = {
        "id": test_id,
        "type": test_type,
        "question": question,
        "expected": expected,
        "actual": actual_answer,
        "score": score,
        "passed": is_pass,
        "faithful": is_faithful,
        "failure_category": category,
        "unsupported_claims": unsupported_claims,
        "reason": reason,
        "sources": sources
    }
    results.append(record)

    status_str = "✅ PASS" if is_pass else f"❌ FAIL [{category}]"
    faithful_str = "🔒 Grounded" if is_faithful else "⚠️ Unfaithful/Hallucinated"
    print(f"🎯 Status: {status_str} | {faithful_str} | Score: {score}/5")
    if unsupported_claims and unsupported_claims != ["empty list if faithful"]:
        print(f"⚠️ Unsupported Claims: {unsupported_claims}")
    print(f"💡 Judge Reason: {reason}")
    print("-" * 70 + "\n")

# Calculate aggregate metrics
total = len(tests)
pass_rate = (passed / total) if total > 0 else 0
faithfulness_rate = (faithful_count / total) if total > 0 else 0
avg_score = (total_score / total) if total > 0 else 0

print("=" * 70)
print("📊 RAG EVALUATION SUMMARY REPORT")
print(f"Total Tests:        {total}")
print(f"Passed:             {passed} / {total} ({pass_rate:.1%})")
print(f"Failed:             {total - passed}")
print(f"Faithfulness Rate:  {faithfulness_rate:.1%}")
print(f"Average Score:      {avg_score:.2f} / 5.0")

if failure_categories:
    print("\nFailure Breakdown:")
    for cat, count in failure_categories.items():
        print(f"  • {cat}: {count}")
print("=" * 70)

# Persist output
results_dir = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(results_dir, exist_ok=True)
latest_path = os.path.join(results_dir, "latest.json")

with open(latest_path, "w", encoding="utf-8") as f:
    json.dump({
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
            "faithfulness_rate": faithfulness_rate,
            "avg_score": avg_score,
            "failures": dict(failure_categories)
        },
        "results": results
    }, f, indent=2)

print(f"\n💾 Full structured results saved to {latest_path}\n")
