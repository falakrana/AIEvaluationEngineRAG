import json
import os
import argparse
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.environ["GROQ_API_KEY"]
)


def generate_synthetic_tests(knowledge, count=10):
    """
    Uses an LLM to generate synthetic test cases from the knowledge base.
    Produces direct QA, edge cases, and out-of-scope questions.
    """
    knowledge_str = json.dumps(knowledge, indent=2)

    prompt = f"""
You are a QA test case generator for an AI customer support evaluation system.

Here is the knowledge base the AI system has access to:
{knowledge_str}

Generate exactly {count} diverse test cases as a JSON array. Each test case must have:
- "question": A realistic customer question.
- "expected": The correct ground-truth answer based ONLY on the knowledge base.
- "type": One of "in_scope", "edge_case", or "out_of_scope".

Distribution rules:
- ~50% "in_scope": Direct questions clearly answerable from the knowledge base.
- ~30% "edge_case": Paraphrased, informal, multi-part, or tricky variations of in-scope topics.
- ~20% "out_of_scope": Questions NOT answerable from the knowledge base. For these, the expected answer must be: "This information is not available in our knowledge base."

Requirements:
- Questions must be varied and realistic (not repetitive).
- Edge cases should test nuance (e.g., combining topics, informal language, negations).
- Do NOT repeat the exact wording from the knowledge base in questions.

Return ONLY a valid JSON array of objects with keys: "question", "expected", "type".
"""

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a precise test case generator. Always respond with valid JSON only."
            },
            {"role": "user", "content": prompt}
        ]
    )

    try:
        raw = json.loads(response.choices[0].message.content)
        # Handle both direct array and wrapped object responses
        if isinstance(raw, list):
            tests = raw
        elif isinstance(raw, dict):
            # Find the array value in the dict
            for v in raw.values():
                if isinstance(v, list):
                    tests = v
                    break
            else:
                tests = []
        else:
            tests = []
    except json.JSONDecodeError:
        print("❌ LLM returned invalid JSON. No tests generated.")
        return []

    return tests


def main():
    parser = argparse.ArgumentParser(description="Synthetic Test Dataset Generator")
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of synthetic test cases to generate (default: 10)"
    )
    parser.add_argument(
        "--output", type=str, default="synthetic_dataset.json",
        help="Output file name (default: synthetic_dataset.json)"
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append generated tests to existing dataset.json instead of creating a new file"
    )
    args = parser.parse_args()

    # Load knowledge base
    with open("knowledge.json", "r") as f:
        knowledge = json.load(f)

    print(f"📦 Loaded {len(knowledge)} knowledge entries.")
    print(f"🔄 Generating {args.count} synthetic test cases...\n")

    tests = generate_synthetic_tests(knowledge, count=args.count)

    if not tests:
        print("No test cases were generated.")
        return

    # Assign IDs
    if args.append:
        # Load existing dataset and continue IDs from there
        with open("dataset.json", "r") as f:
            existing = json.load(f)
        next_id = max(t["id"] for t in existing) + 1
    else:
        existing = []
        next_id = 1

    for i, test in enumerate(tests):
        test["id"] = next_id + i

    # Print generated tests
    in_scope = sum(1 for t in tests if t.get("type") == "in_scope")
    edge_case = sum(1 for t in tests if t.get("type") == "edge_case")
    out_of_scope = sum(1 for t in tests if t.get("type") == "out_of_scope")

    print(f"✅ Generated {len(tests)} test cases:")
    print(f"   • In-scope:     {in_scope}")
    print(f"   • Edge cases:   {edge_case}")
    print(f"   • Out-of-scope: {out_of_scope}\n")

    for t in tests:
        tag = {"in_scope": "📗", "edge_case": "📙", "out_of_scope": "📕"}.get(t.get("type", ""), "❓")
        print(f"  {tag} [{t['id']}] {t['question']}")
        print(f"     Expected: {t['expected']}\n")

    # Save
    if args.append:
        combined = existing + tests
        with open("dataset.json", "w") as f:
            json.dump(combined, f, indent=2)
        print(f"\n📁 Appended {len(tests)} tests to dataset.json (total: {len(combined)})")
    else:
        with open(args.output, "w") as f:
            json.dump(tests, f, indent=2)
        print(f"\n📁 Saved to {args.output}")


if __name__ == "__main__":
    main()
