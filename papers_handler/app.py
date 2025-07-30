"""
AWS Lambda function handlers to manage question paper downloads and listings for the
ExamFleet MVP.  These functions support downloading publicly available question
pairs from official government sources into an S3 bucket and listing stored
papers.  The event payload must specify an `action` key with one of the
following values:

* ``download_papers`` – Download a fixed set of exam PDFs from their
  authoritative sources and upload them into an S3 bucket.  The bucket name
  must be provided via the ``BUCKET_NAME`` environment variable.  When
  triggered, this action fetches the UPSC Civil Services Preliminary 2024
  General Studies papers and the SSC model question paper (English) from
  official UPSC and SSC websites and stores them in the bucket.  You can add
  additional URLs to the ``exam_urls`` mapping as more resources become
  available.

* ``list_papers`` – Return a list of keys for all objects currently stored
  under the configured S3 bucket.  This action makes it easy for the frontend
  to enumerate available downloads without hard‑coding filenames.

If the event does not include a supported ``action``, the function returns
HTTP 400 with a brief error message.

This module uses the ``requests`` package to fetch remote files and the
``boto3`` SDK to interact with Amazon S3.  Make sure to add ``requests`` to
your project dependencies (see ``papers_handler/requirements.txt``) and
configure a bucket via the ``BUCKET_NAME`` environment variable in
``template.yaml``.
"""

import json
import os
from typing import Dict, Any, List

import boto3
import requests


def _download_and_store(url: str, key: str, bucket: str, s3_client: boto3.client) -> None:
    """Fetch a PDF from a URL and upload it to the given S3 bucket.

    Args:
        url: HTTP URL of the PDF to download.
        key: Object key to use when storing the PDF in S3.
        bucket: Name of the destination S3 bucket.
        s3_client: boto3 S3 client instance.
    """
    response = requests.get(url)
    response.raise_for_status()
    # Upload the binary content directly to S3
    s3_client.put_object(Bucket=bucket, Key=key, Body=response.content, ContentType="application/pdf")


def _handle_download_papers(event: Dict[str, Any]) -> Dict[str, Any]:
    """Download known question papers and upload them to S3.

    Returns a JSON object listing the S3 keys that were saved.
    """
    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "BUCKET_NAME environment variable not set"}),
        }

    # Map exam identifiers to their official PDF URLs.
    # These URLs were curated from official UPSC and SSC websites during initial development.
    exam_urls: Dict[str, str] = {
        "UPSC_Civil_Services_Prelims_2024_GS_Paper_I": "https://upsc.gov.in/sites/default/files/QP-CSP-24-GENERAL-STUDIES-PAPER-I-180624.pdf",
        "UPSC_Civil_Services_Prelims_2024_GS_Paper_II": "https://upsc.gov.in/sites/default/files/QP-CSP-24-GENERAL-STUDIES-PAPER-II-180624.pdf",
        "SSC_Model_Question_Paper_English": "https://ssc.nic.in/Downloads/portal/english/modal-question-paper-english.pdf",
    }

    s3_client = boto3.client("s3")
    saved_keys: List[str] = []
    for name, url in exam_urls.items():
        key = f"{name}.pdf"
        try:
            _download_and_store(url, key, bucket_name, s3_client)
            saved_keys.append(key)
        except Exception as exc:  # broad catch to ensure all papers attempt
            # Log the error into the saved list with the error message
            saved_keys.append(f"{key}: error {exc}")

    return {
        "statusCode": 200,
        "body": json.dumps({"saved": saved_keys}),
    }


def _handle_list_papers(event: Dict[str, Any]) -> Dict[str, Any]:
    """List objects stored in the configured S3 bucket.

    Returns a JSON object with the key names.
    """
    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "BUCKET_NAME environment variable not set"}),
        }
    s3_client = boto3.client("s3")
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    keys = [item["Key"] for item in response.get("Contents", [])]
    return {
        "statusCode": 200,
        "body": json.dumps({"files": keys}),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Primary Lambda entry point for paper management.

    The event must include an 'action' key specifying what to do.  Supported
    actions are 'download_papers' and 'list_papers'.  Any other value results
    in an HTTP 400 response.
    """
    action = (event or {}).get("action")
    if action == "download_papers":
        return _handle_download_papers(event)
    elif action == "list_papers":
        return _handle_list_papers(event)
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unsupported action: {action}"}),
        }