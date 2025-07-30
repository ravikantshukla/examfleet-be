"""
Lambda to summarize extracted text using an LLM (e.g. OpenAI GPT).  The
incoming event should include a JSON body with a ``text`` field containing
the raw content to summarize.  This function calls the OpenAI API using the
API key provided via the ``OPENAI_API_KEY`` environment variable and
returns a concise summary.

If ``OPENAI_API_KEY`` is not set, a fallback summarizer returns the first
1000 characters of the input text to allow local testing without external
dependencies.
"""

import json
import os
from typing import Any, Dict

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # fallback if openai isn't installed


def _fallback_summary(text: str) -> str:
    """Return a truncated version of the input as a fallback summary."""
    return text[:1000] + ("..." if len(text) > 1000 else "")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body)
        text = payload["text"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    api_key = os.environ.get("OPENAI_API_KEY")
    if openai and api_key:
        openai.api_key = api_key
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Summarize the following text."}, {"role": "user", "content": text}],
                temperature=0.5,
                max_tokens=300,
            )
            summary = response["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            summary = _fallback_summary(text)
    else:
        summary = _fallback_summary(text)

    return {"statusCode": 200, "body": json.dumps({"summary": summary})}