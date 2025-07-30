"""
Lambda to aggregate quiz performance statistics for a user.  This function
queries a DynamoDB table of quiz results (same table used by the
SubmitQuiz Lambda) and returns aggregate metrics such as the number of
quizzes taken, total score, and average score.

Expected input JSON:

```
{
  "userId": "user-123"
}
```

Environment variables:

* ``QUIZ_RESULTS_TABLE`` – name of the DynamoDB table containing quiz
  submissions.
"""

import json
import os
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body)
        user_id = payload["userId"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    table_name = os.environ.get("QUIZ_RESULTS_TABLE")
    if not table_name:
        return {"statusCode": 500, "body": json.dumps({"error": "QUIZ_RESULTS_TABLE not configured"})}

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    # Query by partition key (userId)
    response = table.query(KeyConditionExpression=Key("userId").eq(user_id))
    items = response.get("Items", [])
    total_quizzes = len(items)
    total_score = sum(item.get("score", 0) for item in items)
    avg_score = total_score / total_quizzes if total_quizzes else 0
    return {
        "statusCode": 200,
        "body": json.dumps({
            "userId": user_id,
            "totalQuizzes": total_quizzes,
            "totalScore": total_score,
            "averageScore": avg_score,
        })
    }