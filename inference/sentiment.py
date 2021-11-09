"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import json
from transformers import pipeline

nlp = pipeline("sentiment-analysis")


def handler(event, context):
    print(event)
    input_body = json.loads(event["body"])
    print(input_body)
    input_text = input_body["text"]
    sentiment_output = nlp(input_text)[0]
    response = {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps(sentiment_output),
    }
    return response
