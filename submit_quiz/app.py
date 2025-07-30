"""
Lambda function to handle quiz submission.  The front‑end sends a JSON
payload containing the user's answers and the corresponding correct
answers.  The function calculates a simple score (number of correct
responses) and stores the result in DynamoDB.

Expected input JSON:

```
{
  "userId": "user-123",
  "quizId": "quiz-456",
  "answers": ["A", "B", "C", "D"],
  "correctAnswers": ["A", "C", "C", "D"]
}
```

Environment variables:

* ``QUIZ_RESULTS_TABLE`` – name of the DynamoDB table where results should
  be stored.
"""

import json
import os
import time
from typing import Any, Dict, List

import boto3


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Parse input
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode()
        payload = json.loads(body)
        user_id = payload["userId"]
        quiz_id = payload.get("quizId", "unknown")
        answers: List[str] = payload["answers"]
        correct_answers: List[str] = payload["correctAnswers"]
    except (KeyError, json.JSONDecodeError) as exc:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid input: {exc}"})}

    # Calculate score
    score = sum(1 for a, c in zip(answers, correct_answers) if a == c)

    # Persist result to DynamoDB
    table_name = os.environ.get("QUIZ_RESULTS_TABLE")
    if table_name:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        item = {
            "userId": user_id,
            "quizId": quiz_id,
            "timestamp": int(time.time()),
            "score": score,
            "totalQuestions": len(correct_answers),
        }
        table.put_item(Item=item)

    return {"statusCode": 200, "body": json.dumps({"score": score})}