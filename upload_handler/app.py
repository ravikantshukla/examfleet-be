"""
Lambda function for handling file uploads via API Gateway.  This function
expects the incoming event to contain a JSON body with two fields:

* ``fileName`` – the desired name of the file (including extension) to store
  in S3.
* ``fileContent`` – a base64‑encoded string representing the binary content
  of the uploaded PDF.

When invoked, the function decodes the file content, writes it to the
configured S3 bucket, and returns a signed URL (or plain S3 URL) pointing to
the stored object.  The destination bucket name must be provided via the
``UPLOADS_BUCKET_NAME`` environment variable.

This simplified implementation avoids multipart parsing.  Front‑end code
should Base64‑encode the file and send it as JSON to this endpoint.
"""

import base64
import json
import os
from typing import Any, Dict

import boto3


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Retrieve bucket name from environment
    bucket_name = os.environ.get("UPLOADS_BUCKET_NAME")
    if not bucket_name:
        return {"statusCode": 500, "body": json.dumps({"error": "UPLOADS_BUCKET_NAME not configured"})}

    # Parse JSON body
    try:
        body = event.get("body")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode()
        payload = json.loads(body or "{}")
        file_name = payload["fileName"]
        file_content_b64 = payload["fileContent"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    # Decode the file content
    try:
        file_bytes = base64.b64decode(file_content_b64)
    except Exception as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Unable to decode fileContent: {exc}"})}

    # Upload to S3
    s3_client = boto3.client("s3")
    key = file_name
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=file_bytes, ContentType="application/pdf")

    # Construct the S3 URL (non‑signed) – adjust if you need signed URLs
    url = f"https://{bucket_name}.s3.amazonaws.com/{key}"
    return {
        "statusCode": 200,
        "body": json.dumps({"fileUrl": url}),
    }