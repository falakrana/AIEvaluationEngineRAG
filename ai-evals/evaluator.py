import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY", "")
)


def evaluate(question: str, expected: str, actual: str, context=None) -> dict:
    """
    Evaluates the actual response against expected answer and retrieved context using an LLM Judge.
    Measures:
      1. Correctness (Strict numerical & factual precision)
      2. Relevance (Directly addresses the prompt)
      3. Faithfulness / Groundedness (Strictly derived from retrieved context without hallucination)
    """
    context_str = json.dumps(context, indent=2) if context and not isinstance(context, str) else (context or "N/A")

    prompt = f"""
You are a rigorous, highly meticulous AI Quality & RAG Evaluation Judge specialized in Document QA, Resumes, and Knowledge Extraction.

Your task is to judge the actual model response against the expected reference answer and retrieved knowledge context.

Question:
{question}

Expected Reference Answer:
{expected}

Retrieved Knowledge Context:
{context_str}

Actual Model Response:
{actual}

Evaluation Criteria:
1. **Answer Correctness**: Is the actual response factually and numerically accurate compared to the Expected Reference Answer? Dates, metrics, names, technologies, titles, IDs, and details must be exact.
2. **Relevance**: Does the response directly and clearly answer what was asked?
3. **Faithfulness / Groundedness**: Is EVERY claim in the actual response strictly supported by the Retrieved Knowledge Context? (Mark unfaithful if the model invents numbers, mentions outside facts, or hallucinates items not present in the context).
4. **Negative / Out-of-Scope Handling**: If the item/question is not in the document, the model should correctly refuse or state it is not present.

Failure Categories (choose one if passed is false, else "none"):
- "none" (Passed all checks)
- "hallucination" (Model fabricated numbers, products, or claims not found in the context)
- "incorrect_answer" (Wrong numbers, contradictory information, or wrong calculation)
- "missing_information" (Partially answered, but missed crucial details or amounts)
- "unsupported_claim" (Made assertions that cannot be proven from the retrieved snippets)
- "irrelevant_answer" (Ignored the question or answered something off-topic)

Return JSON ONLY matching this schema:
{{
  "correct": true/false,
  "relevant": true/false,
  "faithful": true/false,
  "score": 1-5,
  "passed": true/false,
  "failure_category": "none" | "hallucination" | "incorrect_answer" | "missing_information" | "unsupported_claim" | "irrelevant_answer",
  "unsupported_claims": ["List of unsupported or hallucinated statements, or empty list if faithful"],
  "reason": "Clear explanation detailing numerical correctness, context groundedness, and judgment rationale."
}}
"""

    try:
        response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a strict, objective RAG evaluation judge. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        eval_result = json.loads(response.choices[0].message.content)
    except Exception as exc:
        # Fallback or parsing error
        eval_result = {
            "correct": False,
            "relevant": False,
            "faithful": False,
            "score": 1,
            "passed": False,
            "failure_category": "judge_error",
            "unsupported_claims": [f"Judge API error: {str(exc)}"],
            "reason": f"Evaluation could not complete due to error: {str(exc)}"
        }

    return eval_result
