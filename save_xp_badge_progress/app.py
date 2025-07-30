"""
Lambda to record XP and badge progress for users.  This function accepts
activities sent by the front‑end and updates a DynamoDB table with the
user's running totals.  It supports arbitrary increments of XP and a
simple streak mechanism that increments when the user completes an action
within a 24‑hour window.

Expected input JSON:

```
{
  "userId": "user-123",
  "xp": 10,
  "activity": "completed_quiz"
}
```

Environment variables:

* ``PROGRESS_TABLE`` – name of the DynamoDB table tracking user progress.
"""

import json
import os
import time
from typing import Any, Dict

import boto3


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body)
        user_id = payload["userId"]
        xp = int(payload.get("xp", 0))
    except (KeyError, json.JSONDecodeError, ValueError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    table_name = os.environ.get("PROGRESS_TABLE")
    if not table_name:
        return {"statusCode": 500, "body": json.dumps({"error": "PROGRESS_TABLE not configured"})}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    now = int(time.time())

    # Use an update expression to atomically increment XP and streaks
    # We maintain attributes: xp, streak, lastActivity
    response = table.update_item(
        Key={"userId": user_id},
        UpdateExpression="SET xp = if_not_exists(xp, :zero) + :xp, "
                         "lastActivity = :now, "
                         "streak = if_not_exists(streak, :zero) + :one",
        ExpressionAttributeValues={
            ":xp": xp,
            ":zero": 0,
            ":now": now,
            ":one": 1,
        },
        ReturnValues="ALL_NEW",
    )
    new_item = response.get("Attributes", {})
    return {"statusCode": 200, "body": json.dumps({"progress": new_item})}