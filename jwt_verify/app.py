"""
Lambda function to verify Firebase JWT tokens.  This serves as a custom
authorizer or a middleware that your API routes can call to authenticate
requests.  The function expects the incoming event to contain an
``authorization`` header bearing a Bearer token.  It uses the Firebase
Admin SDK to verify the token and returns the decoded user claims.

Environment variables:

* ``FIREBASE_PROJECT_ID`` – your Firebase project ID.
* ``GOOGLE_APPLICATION_CREDENTIALS`` – optional path to a service account
  JSON file packaged with the Lambda (if not using default credentials).
"""

import json
import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import auth, credentials

_initialized = False


def _init_firebase():
    global _initialized
    if _initialized:
        return
    # Initialize Firebase Admin using default credentials or service account
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    else:
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    })
    _initialized = True


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    _init_firebase()
    headers = event.get("headers") or {}
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if not auth_header:
        return {"statusCode": 401, "body": json.dumps({"error": "Missing Authorization header"})}
    # Expect format "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid authorization format"})}
    token = parts[1]
    try:
        decoded = auth.verify_id_token(token)
        return {"statusCode": 200, "body": json.dumps({"claims": decoded})}
    except Exception as exc:
        return {"statusCode": 401, "body": json.dumps({"error": f"Token verification failed: {exc}"})}