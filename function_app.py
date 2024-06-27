import azure.functions as func
import os
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import TextCategory
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.contentsafety.models import AnalyzeTextOptions
import safety_checks.safety_checks as safety_checks
import logging
import asyncio
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

import azure.functions as func
import logging
import requests  # You might need to install this dependency

CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")

# Initialize your Azure Function
@app.route(route="SecurityHub")
async def security_hub(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing request.')
    # Extract question, answer, and sources from the request
    try:
        req_body = req.get_json()
        question = req_body.get('question')
        answer = req_body.get('answer')
        sources = req_body.get('sources')
    except ValueError:
        return func.HttpResponse("Invalid request", status_code=400)

    if not question or not answer or not sources:
        return func.HttpResponse("Missing question, answer, or sources in the request", status_code=400)

    # Create a Content Safety client
    client = ContentSafetyClient(CONTENT_SAFETY_ENDPOINT, AzureKeyCredential(CONTENT_SAFETY_KEY))
    #Call content safety functions
    checks = [
        safety_checks.groundedness_check(question, answer, sources, client),
        safety_checks.prompt_shield(question, sources, client),
        safety_checks.jailbreak_detection(question, client),
        safety_checks.protected_material_detection(question, client)
    ]
    check_results = {}

    for check in asyncio.as_completed(checks):
        check_name, status_code, check_result = await check
        # If the status code is not 200, record the error and continue to the next check
        if status_code != 200:
            check_results[check_name] = "Error: Failed request"
            continue
        # If the check_result indicates a failure, record the failure
        if check_result:
            check_results[check_name] = f"Content safety check {check_name}failed"

    # Determine if all checks were successful
    successful = len(check_results) == 0

    # Prepare the response object
    response_data = {
        "successful": successful,
        "details": check_results
    }

    # Return a JSON response
    return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")
