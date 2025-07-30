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
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body)
        summary = payload["summary"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    api_key = os.environ.get("OPENAI_API_KEY")
    if openai and api_key:
        openai.api_key = api_key
        prompt = (
            "You are a helpful assistant that creates multiple choice quizzes. "
            "Given the following summary of study material, generate five distinct MCQ questions. "
            "Provide four options labelled A, B, C, D and identify the correct answer. "
            "Return the result as JSON with the keys 'question', 'options' (list) and 'answer'.\n\n"
            f"Summary:\n{summary}\n"
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

    return {"statusCode": 200, "body": json.dumps({"quiz": quiz})}