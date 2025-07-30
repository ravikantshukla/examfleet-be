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
    """Generate flashcards from a summary of study material.

    Expects a JSON payload with a ``summary`` field and optionally a
    ``topicId``.  Returns a list of objects matching the ``Flashcard``
    interface used by the front‑end (id, front, back, topicId).  When the
    OpenAI API is unavailable a default set of flashcards is used.
    """
    # Decode body
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()
    try:
        payload = json.loads(body)
        summary: str = payload["summary"]
        topic_id: str = payload.get("topicId", "general")
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    api_key = os.environ.get("OPENAI_API_KEY")
    cards: List[Dict[str, str]]
    if openai and api_key:
        openai.api_key = api_key
        prompt = (
            "Generate three flashcards from the following summary. "
            "Return the result as JSON: a list where each element has 'front' and 'back' fields, representing the question and answer.\n\nSummary:\n"
            + summary
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=500,
            )
            content = response["choices"][0]["message"]["content"].strip()
            cards = json.loads(content)
        except Exception:
            cards = _dummy_flashcards(summary)
    else:
        cards = _dummy_flashcards(summary)

    # Convert to full Flashcard objects: add id and topicId, rename keys
    import uuid

    flashcards: List[Dict[str, str]] = []
    for card in cards:
        # card may have 'question'/'answer' (dummy) or 'front'/'back'
        front = card.get("front") or card.get("question") or ""
        back = card.get("back") or card.get("answer") or ""
        flashcards.append({
            "id": str(uuid.uuid4()),
            "front": front,
            "back": back,
            "topicId": topic_id,
        })

    return {
        "statusCode": 200,
        "body": json.dumps({"flashcards": flashcards}),
    }