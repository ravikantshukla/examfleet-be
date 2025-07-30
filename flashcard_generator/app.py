"""
Lambda to generate flashcards (question‑answer pairs) from a summary.  This
function calls an LLM to produce a list of flashcards, each containing a
question and its answer.  The event body should contain a ``summary``
field.  If OpenAI is not configured, a dummy flashcard is returned.
"""

import json
import os
from typing import Any, Dict, List

try:
    import openai  # type: ignore
except ImportError:
    openai = None


def _dummy_flashcards(summary: str) -> List[Dict[str, str]]:
    return [
        {
            "question": "What is the purpose of flashcards?",
            "answer": "Flashcards are used as a study aid to improve memory through spaced repetition.",
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
            "Generate three flashcards from the following summary. "
            "Return a JSON list where each element has 'question' and 'answer' fields.\n\n"
            f"Summary:\n{summary}\n"
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            content = response["choices"][0]["message"]["content"].strip()
            flashcards = json.loads(content)
        except Exception:
            flashcards = _dummy_flashcards(summary)
    else:
        flashcards = _dummy_flashcards(summary)

    return {"statusCode": 200, "body": json.dumps({"flashcards": flashcards})}