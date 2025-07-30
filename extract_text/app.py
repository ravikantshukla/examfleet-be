"""
Lambda function triggered by S3 events to extract raw text from uploaded PDFs.

This handler listens for ``ObjectCreated`` events on the configured PDF
uploads bucket (see ``template.yaml`` for event source configuration).
When triggered, it downloads the new object from S3, extracts text using
``PyPDF2``, and writes the extracted plain text back to S3 under a
``extracted/`` prefix or stores it to DynamoDB (left as an exercise).

Environment variables used:

* ``UPLOADS_BUCKET_NAME`` – the source bucket containing uploaded PDFs.
* ``EXTRACTED_BUCKET_NAME`` – optional destination bucket for storing
  extracted text.  If not provided, extracted content is returned in the
  function response instead of being persisted.
"""

import json
import os
from typing import Any, Dict

import boto3
from PyPDF2 import PdfReader
import io


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    uploads_bucket = os.environ.get("UPLOADS_BUCKET_NAME")
    dest_bucket = os.environ.get("EXTRACTED_BUCKET_NAME")

    # Iterate over records (S3 events may include multiple objects)
    outputs = []
    for record in event.get("Records", []):
        s3_info = record.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name")
        key = s3_info.get("object", {}).get("key")
        if not bucket_name or not key:
            continue

        # Only process the expected uploads bucket
        if uploads_bucket and bucket_name != uploads_bucket:
            continue

        # Download the PDF from S3
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        pdf_bytes = obj["Body"].read()

        # Extract text using PyPDF2
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

        if dest_bucket:
            # Save extracted text to dest bucket under extracted/key.txt
            dest_key = f"extracted/{os.path.splitext(key)[0]}.txt"
            s3.put_object(Bucket=dest_bucket, Key=dest_key, Body=text.encode("utf-8"), ContentType="text/plain")
            outputs.append({"source": key, "destination": dest_key})
        else:
            outputs.append({"source": key, "text": text})

    return {"statusCode": 200, "body": json.dumps(outputs)}