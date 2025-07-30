"""
Lambda function to generate multiple‑choice questions (MCQs) from a summary
of content.  Accepts a JSON body with a ``summary`` field, forwards the
summary to an LLM (OpenAI) to create quiz questions with options and a
correct answer, and returns them in a structured format.

If the ``OPENAI_API_KEY`` environment variable is not configured or the
``openai`` package is unavailable, returns a single dummy question as a
fallback.  The returned structure is a list of dictionaries with keys
``question``, ``options`` (a list of four strings), and ``answer`` (the
correct option text).
"""

import json
import os
from typing import Any, Dict, List

try:
    import openai  # type: ignore
except ImportError:
    openai = None


def _dummy_quiz(summary: str) -> List[Dict[str, Any]]:
    """Generate a placeholder quiz when OpenAI isn't configured."""
    return [
        {
            "question": "This is a placeholder question because the quiz generator is not configured.",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
        }
    ]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate multiple choice questions from a summary of study material.

    The incoming request must provide a ``summary`` field in the JSON
    payload.  The returned object includes a ``questions`` property
    containing a list of objects conforming to the ``QuizQuestion``
    interface expected by the Next.js front‑end (see ``src/types`` in
    examfleet‑fe).  On failure to call the OpenAI API a single dummy
    question is returned.
    """
    # Decode body
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()
    try:
        payload = json.loads(body)
        summary = payload["summary"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    api_key = os.environ.get("OPENAI_API_KEY")
    quiz: List[Dict[str, Any]]
    if openai and api_key:
        openai.api_key = api_key
        # Craft a prompt instructing the LLM to return valid JSON with
        # the desired structure.  We ask for 5 questions by default.
        prompt = (
            "You are a helpful assistant that creates multiple choice quizzes. "
            "Given the following summary of study material, generate five distinct MCQ questions. "
            "Each question should include four options and specify the correct answer. "
            "Return the result as JSON: a list where each element has 'question', 'options' (list of four strings), "
            "and 'answer' (one of the options).\n\nSummary:\n" + summary
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=800,
            )
            content = response["choices"][0]["message"]["content"].strip()
            quiz = json.loads(content)
        except Exception:
            quiz = _dummy_quiz(summary)
    else:
        quiz = _dummy_quiz(summary)

    # Normalise the key name for the front‑end: `questions` instead of `quiz`
    return {
        "statusCode": 200,
        "body": json.dumps({"questions": quiz}),
    }