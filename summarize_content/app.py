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
    """Entry point for the summarisation Lambda.

    This handler accepts either raw text or a base64‑encoded PDF and
    returns a concise summary.  It is intended to power the `/summarize`
    endpoint consumed by the Next.js front‑end and therefore always
    returns an object with a ``summary`` field.  When a ``fileContent``
    property is provided the PDF is parsed using ``PyPDF2`` to extract
    plain text prior to summarisation.  If a ``text`` field is supplied
    directly it is used verbatim.

    If the OpenAI client is configured via the ``OPENAI_API_KEY``
    environment variable then the summary is generated with GPT‑3.5,
    otherwise a fallback summariser simply truncates the input.
    """
    # Decode the body.  API Gateway may send Base64‑encoded payloads
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid JSON: {exc}"})}

    # Determine which field to use for source text
    text: str | None = None
    # Direct text provided
    if isinstance(payload.get("text"), str) and payload["text"]:
        text = payload["text"]
    # Base64 encoded PDF provided
    elif isinstance(payload.get("fileContent"), str) and payload["fileContent"]:
        b64_str = payload["fileContent"]
        try:
            import base64
            import io
            from PyPDF2 import PdfReader  # type: ignore

            pdf_bytes = base64.b64decode(b64_str)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            return {"statusCode": 400, "body": json.dumps({"error": f"Failed to decode PDF: {exc}"})}
    else:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing 'text' or 'fileContent' in request"})}

    # Validate text
    if not text:
        return {"statusCode": 400, "body": json.dumps({"error": "No content provided to summarise"})}

    # Generate summary using LLM or fallback
    api_key = os.environ.get("OPENAI_API_KEY")
    if openai and api_key:
        openai.api_key = api_key
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarises study material."},
                    {"role": "user", "content": text},
                ],
                temperature=0.5,
                max_tokens=300,
            )
            summary = response["choices"][0]["message"]["content"].strip()
        except Exception:
            summary = _fallback_summary(text)
    else:
        summary = _fallback_summary(text)

    return {
        "statusCode": 200,
        "body": json.dumps({"summary": summary}),
    }