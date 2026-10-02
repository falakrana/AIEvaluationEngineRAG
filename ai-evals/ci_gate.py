import json
import os
import sys
import argparse
from collections import Counter

from model import run_model
from evaluator import evaluate


def run_ci_gate(min_pass_rate, min_faithfulness, min_score, dataset_path, knowledge_path):
    print("=" * 60)
    print(" 🛡️  AI EVALUATION CI/CD QUALITY GATE")
    print("=" * 60)

    # 1. Load data
    if not os.path.exists(dataset_path):
        print(f"❌ Error: Dataset file '{dataset_path}' not found.")
        sys.exit(1)

    if not os.path.exists(knowledge_path):
        print(f"❌ Error: Knowledge file '{knowledge_path}' not found.")
        sys.exit(1)

    with open(dataset_path, "r") as f:
        tests = json.load(f)

    with open(knowledge_path, "r") as f:
        context = json.load(f)

    total = len(tests)
    print(f"Loaded {total} test cases from '{dataset_path}'.")
    print(f"Required Thresholds:")
    print(f"  • Min Pass Rate:       {min_pass_rate:.1f}%")
    print(f"  • Min Faithfulness:    {min_faithfulness:.1f}%")
    print(f"  • Min Average Score:   {min_score:.2f} / 5.0")
    print("-" * 60)

    # 2. Run evaluations
    passed = 0
    faithful_count = 0
    total_score = 0
    failures = Counter()
    results = []

    for test in tests:
        model_out = run_model(test["question"])
        actual = model_out.get("answer", "")
        retrieved_ctx = model_out.get("context", "")
        eval_res = evaluate(
            question=test["question"],
            expected=test["expected"],
            actual=actual,
            context=retrieved_ctx
        )

        is_pass = eval_res.get("passed", False)
        is_faithful = eval_res.get("faithful", False)
        score = eval_res.get("score", 0)
        category = eval_res.get("failure_category", "none")

        if is_pass:
            passed += 1
        else:
            failures[category] += 1

        if is_faithful:
            faithful_count += 1

        total_score += score

        results.append({
            "id": test["id"],
            "question": test["question"],
            "passed": is_pass,
            "faithful": is_faithful,
            "score": score,
            "category": category,
            "reason": eval_res.get("reason", "")
        })

    # 3. Calculate metrics
    pass_rate = (passed / total) * 100.0
    faithfulness_rate = (faithful_count / total) * 100.0
    avg_score = total_score / total

    print("\n" + "=" * 60)
    print(" 📊 CI EVALUATION METRICS SUMMARY")
    print("=" * 60)
    print(f"Total Tests:        {total}")
    print(f"Passed:             {passed} / {total}")
    print(f"Pass Rate:          {pass_rate:.2f}% (Threshold: {min_pass_rate:.1f}%)")
    print(f"Faithfulness Rate:  {faithfulness_rate:.2f}% (Threshold: {min_faithfulness:.1f}%)")
    print(f"Average Score:      {avg_score:.2f} / 5.0 (Threshold: {min_score:.2f})")

    if failures:
        print("\nFailure Breakdown:")
        for cat, cnt in failures.items():
            print(f"  • {cat}: {cnt}")

    # 4. Check thresholds
    checks = []
    if pass_rate >= min_pass_rate:
        checks.append(("Pass Rate", True, f"{pass_rate:.2f}% >= {min_pass_rate:.1f}%"))
    else:
        checks.append(("Pass Rate", False, f"{pass_rate:.2f}% < {min_pass_rate:.1f}%"))

    if faithfulness_rate >= min_faithfulness:
        checks.append(("Faithfulness", True, f"{faithfulness_rate:.2f}% >= {min_faithfulness:.1f}%"))
    else:
        checks.append(("Faithfulness", False, f"{faithfulness_rate:.2f}% < {min_faithfulness:.1f}%"))

    if avg_score >= min_score:
        checks.append(("Average Score", True, f"{avg_score:.2f} >= {min_score:.2f}"))
    else:
        checks.append(("Average Score", False, f"{avg_score:.2f} < {min_score:.2f}"))

    # 5. Write GitHub Step Summary (if running inside GitHub Actions)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as sf:
            sf.write("## 🛡️ AI Evaluation Quality Gate Results\n\n")
            sf.write(f"| Metric | Result | Threshold | Status |\n")
            sf.write(f"| --- | --- | --- | --- |\n")
            sf.write(f"| **Pass Rate** | `{pass_rate:.2f}%` | `{min_pass_rate:.1f}%` | {'✅ PASS' if pass_rate >= min_pass_rate else '❌ FAIL'} |\n")
            sf.write(f"| **Faithfulness Rate** | `{faithfulness_rate:.2f}%` | `{min_faithfulness:.1f}%` | {'✅ PASS' if faithfulness_rate >= min_faithfulness else '❌ FAIL'} |\n")
            sf.write(f"| **Average Score** | `{avg_score:.2f}/5` | `{min_score:.2f}/5` | {'✅ PASS' if avg_score >= min_score else '❌ FAIL'} |\n\n")

    # 6. Final Decision
    all_passed = all(status for _, status, _ in checks)

    print("\n" + "=" * 60)
    print(" 🚦 GATE DECISION")
    print("=" * 60)
    for name, status, detail in checks:
        icon = "✅ PASS" if status else "❌ FAIL"
        print(f"  [{icon}] {name}: {detail}")
    print("=" * 60)

    if all_passed:
        print("\n🎉 Quality gate PASSED! Build is green.\n")
        sys.exit(0)
    else:
        print("\n🚨 Quality gate FAILED! Build is blocked due to threshold violations.\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AI Evaluation CI/CD Quality Gate")
    parser.add_argument("--min-pass-rate", type=float, default=80.0, help="Minimum pass rate percentage (default: 80.0)")
    parser.add_argument("--min-faithfulness", type=float, default=85.0, help="Minimum faithfulness rate percentage (default: 85.0)")
    parser.add_argument("--min-score", type=float, default=3.8, help="Minimum average score out of 5.0 (default: 3.8)")
    parser.add_argument("--dataset", type=str, default="dataset.json", help="Path to dataset JSON")
    parser.add_argument("--knowledge", type=str, default="knowledge.json", help="Path to knowledge base JSON")

    args = parser.parse_args()

    run_ci_gate(
        min_pass_rate=args.min_pass_rate,
        min_faithfulness=args.min_faithfulness,
        min_score=args.min_score,
        dataset_path=args.dataset,
        knowledge_path=args.knowledge
    )


if __name__ == "__main__":
    main()
