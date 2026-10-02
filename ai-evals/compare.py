import json
import os
from collections import Counter

from model import run_model, PROMPT_VARIANT_A, PROMPT_VARIANT_B
from evaluator import evaluate


def run_variant(variant_name, system_prompt, model_name, tests, context):
    print(f"\n⚡ Evaluating Variant '{variant_name}'...")
    results = []
    passed = 0
    faithful_count = 0
    total_score = 0
    failures = Counter()

    for test in tests:
        # 1. Run AI system
        actual = run_model(
            question=test["question"],
            context=context,
            system_prompt=system_prompt,
            model_name=model_name
        )

        # 2. Judge output
        eval_res = evaluate(
            question=test["question"],
            expected=test["expected"],
            actual=actual,
            context=context
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
            "expected": test["expected"],
            "actual": actual,
            "passed": is_pass,
            "faithful": is_faithful,
            "score": score,
            "failure_category": category,
            "reason": eval_res.get("reason", ""),
            "unsupported_claims": eval_res.get("unsupported_claims", [])
        })

    total = len(tests)
    return {
        "variant_name": variant_name,
        "prompt": system_prompt,
        "model": model_name,
        "metrics": {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total,
            "faithful_count": faithful_count,
            "faithfulness_rate": faithful_count / total,
            "avg_score": total_score / total,
            "failures": dict(failures)
        },
        "records": {r["id"]: r for r in results}
    }


def compare_variants():
    # Load dataset & context
    with open("dataset.json", "r") as f:
        tests = json.load(f)

    with open("knowledge.json", "r") as f:
        context = json.load(f)

    print("═══════════════════════════════════════════════════════════")
    print("      🔍 AI EVALUATION: A/B TESTING & REGRESSION ENGINE   ")
    print("═══════════════════════════════════════════════════════════")

    # Run Variant A (Baseline)
    var_a = run_variant(
        variant_name="Variant A (Baseline)",
        system_prompt=PROMPT_VARIANT_A,
        model_name="qwen/qwen3.8-27b",
        tests=tests,
        context=context
    )

    # Run Variant B (Candidate)
    var_b = run_variant(
        variant_name="Variant B (Candidate)",
        system_prompt=PROMPT_VARIANT_B,
        model_name="qwen/qwen3.8-27b",
        tests=tests,
        context=context
    )

    # Analyze Diff & Regressions
    regressions = []
    improvements = []
    stable_passes = []
    stable_fails = []
    diff_table = []

    for test in tests:
        tid = test["id"]
        rec_a = var_a["records"][tid]
        rec_b = var_b["records"][tid]

        pass_a = rec_a["passed"]
        pass_b = rec_b["passed"]

        status_change = ""
        if pass_a and not pass_b:
            status_change = "🚨 REGRESSION"
            regressions.append(tid)
        elif not pass_a and pass_b:
            status_change = "✨ IMPROVEMENT"
            improvements.append(tid)
        elif pass_a and pass_b:
            status_change = "✅ STABLE PASS"
            stable_passes.append(tid)
        else:
            status_change = "❌ STABLE FAIL"
            stable_fails.append(tid)

        diff_table.append({
            "id": tid,
            "question": test["question"],
            "status_change": status_change,
            "score_a": rec_a["score"],
            "score_b": rec_b["score"],
            "category_a": rec_a["failure_category"],
            "category_b": rec_b["failure_category"]
        })

    # Summary calculations
    mA = var_a["metrics"]
    mB = var_b["metrics"]

    pass_delta = mB["pass_rate"] - mA["pass_rate"]
    faith_delta = mB["faithfulness_rate"] - mA["faithfulness_rate"]
    score_delta = mB["avg_score"] - mA["avg_score"]

    print("\n" + "═" * 65)
    print("                  📊 COMPARATIVE SUMMARY REPORT             ")
    print("═" * 65)
    print(f"{'Metric':<22} | {'Variant A (Baseline)':<20} | {'Variant B (Candidate)':<20} | {'Delta':<10}")
    print("-" * 78)
    print(f"{'Pass Rate':<22} | {mA['pass_rate']:<20.2%} | {mB['pass_rate']:<20.2%} | {pass_delta:+6.2%}")
    print(f"{'Faithfulness Rate':<22} | {mA['faithfulness_rate']:<20.2%} | {mB['faithfulness_rate']:<20.2%} | {faith_delta:+6.2%}")
    print(f"{'Average Score':<22} | {mA['avg_score']:<20.2f} | {mB['avg_score']:<20.2f} | {score_delta:+6.2f}")
    print("-" * 78)

    print("\n🔍 Test Case Regressions & Improvements:")
    for row in diff_table:
        print(f"  Test #{row['id']} [{row['status_change']}]: Score A={row['score_a']} -> B={row['score_b']} | '{row['question']}'")

    print("\n🚨 Total Regressions: ", len(regressions))
    print("✨ Total Improvements:", len(improvements))
    print("═" * 65)

    # Save to file
    os.makedirs("results", exist_ok=True)
    comparison_report = {
        "summary": {
            "variant_a": mA,
            "variant_b": mB,
            "deltas": {
                "pass_rate_delta": pass_delta,
                "faithfulness_delta": faith_delta,
                "score_delta": score_delta
            },
            "counts": {
                "regressions": len(regressions),
                "improvements": len(improvements),
                "stable_passes": len(stable_passes),
                "stable_fails": len(stable_fails)
            }
        },
        "regressions_test_ids": regressions,
        "improvements_test_ids": improvements,
        "diff_table": diff_table,
        "details_a": var_a,
        "details_b": var_b
    }

    with open("results/compare_latest.json", "w") as f:
        json.dump(comparison_report, f, indent=2)

    print("\nComparison report saved to results/compare_latest.json")


if __name__ == "__main__":
    compare_variants()
